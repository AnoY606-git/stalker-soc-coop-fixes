"""Offline check of the per-player voice language choice (coop_soc_opening.voice_lang) and the opening voice tables, no game.
usage: python voice_lang_mock_test.py     (needs `pip install lupa`, the same package the other mock tests use)
Runs the REAL scripts coop_soc_opening and coop_host_cfg in a Lua 5.1 VM with a small engine mock: the file is written into a temp folder,
game.translate_string answers Cyrillic or Latin like the two game languages do. Proves: auto follows the game language, rus / eng override it,
a bad value falls back to auto, a client (OnServer false) reads its own file, every shipped sound file exists and the ms values of
coop_scn_opening.script match the ogg length + 300 ms."""
import os
import re
import sys
import tempfile

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
HOST = os.path.abspath(os.path.join(HERE, "..", "..", "host_settings"))
sys.path.insert(0, os.path.join(PATCH, "tools"))
import ogg_ms  # noqa: E402

fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local scripts, tmp = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__server = true
E.__cyr = false
E.__log = {}
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return 1000 end
function E.OnServer() return E.__server end
function E.OnClient() return true end
function E.getFS() return { update_path = function(self, a, n) return tmp .. "/" .. a:gsub("%$", "") .. "_" .. n end, exist = function() return true end } end
E.game = { translate_string = function(id) if E.__cyr then return "\206\202\206\205\205\219\201" end return "Windowed" end }
E.level = { add_call = function() end }
local mods = {}
local function load(name)
	local f = io.open(scripts[name], "r")
	local src = f:read("*a")
	f:close()
	local env = setmetatable({}, { __index = E })
	local fn = assert(loadstring(src, name))
	setfenv(fn, env)
	fn()
	E[name] = env
	return env
end
E.__load = load
return E
'''


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    tmp = tempfile.mkdtemp(prefix="voicelang_")
    scripts = lua.table_from({
        "coop_soc_opening": os.path.join(PATCH, "gamedata", "scripts", "coop_soc_opening.script"),
        "coop_host_cfg": os.path.join(HOST, "gamedata", "scripts", "coop_host_cfg.script"),
    })
    E = lua.execute(PRELUDE, scripts, tmp)
    # the host cfg reads ltx files for its defaults: no db here, the [client] key has a built-in default
    E["ini_file"] = lambda name: (_ for _ in ()).throw(Exception("no ini in the mock"))
    cfg = E["__load"]("coop_host_cfg")
    so = E["__load"]("coop_soc_opening")
    cfg_path = os.path.join(tmp, "app_data_root_coop_settings.ltx")

    def setting(text):
        if text is None:
            if os.path.exists(cfg_path):
                os.remove(cfg_path)
        else:
            open(cfg_path, "wb").write(text.encode("utf-8"))
        so.voice_reset()

    def lang(cyr, server=True):
        E["__cyr"] = cyr
        E["__server"] = server
        so.voice_reset()
        return so.voice_lang()

    # no file: created with the default auto
    setting(None)
    check("no file, English game -> eng", lang(False) == "eng")
    check("the file was created with [client] voice_language = auto", "voice_language = auto" in open(cfg_path, encoding="utf-8").read())
    check("no file, Russian game -> rus", lang(True) == "rus")
    for text, cyr, want, name in [
        ("[client]\nvoice_language = auto\n", False, "eng", "auto + English game"),
        ("[client]\nvoice_language = auto\n", True, "rus", "auto + Russian game"),
        ("[client]\nvoice_language = rus\n", False, "rus", "rus overrides an English game"),
        ("[client]\nvoice_language = eng\n", True, "eng", "eng overrides a Russian game"),
        ("[client]\nvoice_language = ENG ; comment\n", True, "eng", "case and comment"),
        ("[client]\nvoice_language = banana\n", True, "rus", "bad value -> auto (Russian game)"),
        ("[client]\nvoice_language = banana\n", False, "eng", "bad value -> auto (English game)"),
        ("[damage]\nplayer_damage_mult = 2\n", True, "rus", "old file without [client] -> auto, section appended"),
    ]:
        setting(text)
        check("setting: " + name, lang(cyr) == want, lang(cyr))
    check("old file kept its line and got the section", "player_damage_mult = 2" in open(cfg_path, encoding="utf-8").read()
          and "voice_language = auto" in open(cfg_path, encoding="utf-8").read())
    # a client machine (OnServer false) reads its own file
    setting("[client]\nvoice_language = eng\n")
    check("client machine: eng from its own file (Russian game)", lang(True, server=False) == "eng")
    setting(None)
    check("client machine: no file -> auto, file created", lang(True, server=False) == "rus" and "voice_language = auto" in open(cfg_path, encoding="utf-8").read())
    E["__server"] = True

    # shipped files and the ms table of coop_scn_opening.script
    src = open(os.path.join(PATCH, "gamedata", "scripts", "coop_scn_opening.script"), encoding="utf-8").read()
    snd = os.path.join(PATCH, "gamedata", "sounds")
    rows = re.findall(r'line\("([a-z_0-9]+)", (\d+), (\d+)\)', src)
    check("11 voice lines in the table", len(rows) == 11, len(rows))
    for name, rms, ems in rows:
        for lg, ms, sub in (("rus", rms, ""), ("eng", ems, "eng")):
            f = os.path.join(snd, "script_replics", "trader", sub, name + ".ogg")
            ok = os.path.exists(f)
            check("file %s %s" % (lg, name), ok, f if not ok else "")
            if ok:
                want = int(round(ogg_ms.ogg_seconds(f) * 1000)) + 300
                check("ms %s %s" % (lg, name), abs(want - int(ms)) <= 1, "table %s measured %s" % (ms, want))
    for n in ("escape_trader_start_dialog_3", "escape_trader_start_dialog_321"):
        check("dialog voice eng " + n, os.path.exists(os.path.join(snd, "characters_voice", "dialogs", "eng", n + ".ogg")))
        check("Russian dialog voice ships in soc_ru_voices " + n, os.path.exists(os.path.join(os.path.dirname(PATCH), "soc_ru_voices", "gamedata", "sounds", "characters_voice", "dialogs", n + ".ogg")))
    print("\n" + ("ALL PASS" if fails == 0 else "FAILED (%d)" % fails))
    sys.exit(1 if fails else 0)


main()
