"""Offline check of the Yantar dream voices (yantar_ghost_sleep, dream_talk_l / _r), no game.
usage: python dream_voice_mock_test.py     (needs `pip install lupa`, same package as the other mock tests)
Runs the REAL coop_scn_yantar.script in a Lua 5.1 VM with an engine mock and builds the steps of the sleep scene for each voice language:
  rus -> snd2d steps for characters_voice\\scenario\\yantar\\dream_talk_l / _r (stock path, Russian files of patch soc_ru_voices)
  eng -> the same names under ...\\yantar\\eng\\ (Steam SoC files of patch soc_ru_voices)
  a language whose files do not exist plays nothing; without coop_soc_opening the game language decides.
Also proves the four files exist in patches\\soc_ru_voices and are Ogg Vorbis files, and that the Russian pair differs from the English one."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
VOICES = os.path.abspath(os.path.join(HERE, "..", "..", "soc_ru_voices", "gamedata", "sounds", "characters_voice", "scenario", "yantar"))
SCRIPT = os.path.join(PATCH, "gamedata", "scripts", "coop_scn_yantar.script")

fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local src = ...
local E = { string = string, table = table, math = math, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber, tostring = tostring,
	type = type, setmetatable = setmetatable, error = error, select = select, unpack = unpack, next = next, print = print }
E._G = E
E.__voice = "rus"          -- what voice_lang() answers; nil = coop_soc_opening missing
E.__cyr = false
E.__missing = {}           -- sound paths (without .ogg) that "do not exist"
E.__defs = {}
local noop = function() end
E.coop_scenes = { register = function(d) E.__defs[d.id] = d end }
E.getFS = function() return { exist = function(self, alias, p)
	if alias == "$game_sounds$" then return not E.__missing[(p:gsub("%.ogg$", ""))] end
	return true
end } end
E.game = { translate_string = function(id) if E.__cyr then return "\206\202\206\205\205\219\201" end return "Windowed" end }
E.level = setmetatable({}, { __index = function() return noop end })
E.printf = noop
E.coop_soc_opening = { voice_lang = function() return E.__voice end }
setmetatable(E, { __index = function(t, k) return setmetatable({}, { __index = function() return noop end, __call = noop }) end })
local f = assert(loadstring(src, "coop_scn_yantar"))
setfenv(f, E)
f()
return E
'''


def run(voice, cyr=False, missing=(), have_opening=True):
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    src = open(SCRIPT, encoding="cp1251", errors="replace").read()
    E = lua.execute(PRELUDE, src)
    E["__voice"] = voice
    E["__cyr"] = cyr
    if not have_opening:
        lua.execute("local E = ...; E.coop_soc_opening = nil", E)
    for m in missing:
        E["__missing"][m] = True
    steps = lua.execute("local E = ...; return E.__defs.yantar_ghost_sleep.steps({}, {})", E)
    out = []
    for i in range(1, len(steps) + 1):
        st = steps[i]
        if st["do"] == "snd2d" and "dream_talk" in st["path"]:
            out.append(st["path"])
    return out


YA = "characters_voice\\scenario\\yantar\\"

r = run("rus")
check("rus: dream_talk_l and _r at the stock path", r == [YA + "dream_talk_l", YA + "dream_talk_r"], r)
r = run("eng")
check("eng: dream_talk_l and _r under eng\\", r == [YA + "eng\\dream_talk_l", YA + "eng\\dream_talk_r"], r)
r = run("eng", missing=[YA + "eng\\dream_talk_l", YA + "eng\\dream_talk_r"])
check("eng files missing: silent, no step", r == [], r)
r = run("rus", missing=[YA + "dream_talk_r"])
check("rus, only _r missing: only _l is played", r == [YA + "dream_talk_l"], r)
r = run(None, cyr=True, have_opening=False)
check("no coop_soc_opening, Russian game: Russian files", r == [YA + "dream_talk_l", YA + "dream_talk_r"], r)
r = run(None, cyr=False, have_opening=False)
check("no coop_soc_opening, English game: English files", r == [YA + "eng\\dream_talk_l", YA + "eng\\dream_talk_r"], r)
r = run("auto-bad")
check("bad voice_lang answer: game language decides (English game)", r == [YA + "eng\\dream_talk_l", YA + "eng\\dream_talk_r"], r)

# ---- trigger of the ghost sleep (v1.4.3): the end of the last measurement at the bus, not a position alone ----
M = ["YAN_START_TAKE_MEASUREMENTS_%d_QUEST_TASK_INFO" % i for i in (1, 2, 3)]
REPORTED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO"
HELMET = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO"
LAB = "YAN_YAN_START_INFILTRATE_THE_X16_LAB_QUEST_TASK_INFO"

TRIG = r'''
local E, flags, near, now = ...
local ctx = { now = now, flag = function(f) return flags[f] == true end, near = function() return near end }
return E.__defs.yantar_ghost_sleep.trigger(ctx) and true or false
'''


def trig_env():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    src = open(SCRIPT, encoding="cp1251", errors="replace").read()
    E = lua.execute(PRELUDE, src)

    def t(flags, near, now):
        tbl = lua.table()
        for f in flags:
            tbl[f] = True
        return lua.execute(TRIG, E, tbl, near, now)

    return t


t = trig_env()
check("trigger: no measurement, nobody near: no", t([], False, 0) is False)
t = trig_env()
check("trigger: no measurement, player AT the research stop: no (old position rule is gone)", t([], True, 0) is False and t([], True, 20000) is False)
t = trig_env()
check("trigger: sites 1 and 2 only, nobody near: no", t(M[:2], False, 0) is False and t(M[:2], False, 20000) is False)
t = trig_env()
r = [t(M, False, 1000), t(M, False, 3500), t(M, False, 4100)]
check("trigger: all 3 measured: waits 3 s, then yes", r == [False, False, True], r)
t = trig_env()
r = [t(M[:2], True, 1000), t(M[:2], True, 4500)]
check("trigger: fallback, 2 measured and a player at the research stop: after 3 s", r == [False, True], r)
t = trig_env()
r = [t(M, False, 1000), t(M + [REPORTED], False, 5000), t(M, False, 6000), t(M, False, 8000), t(M, False, 9500)]
check("trigger: results handed in cancels the wait, a later condition restarts it", r == [False, False, False, False, True], r)
for nm, fl in (("helmet (lab job started)", HELMET), ("lab level entered", LAB), ("brain scene played", "SCN_YANTAR_BRAIN_PLAYED")):
    t = trig_env()
    check("trigger: no ghost sleep after " + nm, t(M + [fl], True, 0) is False and t(M + [fl], True, 9000) is False)
lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
E = lua.execute(PRELUDE, open(SCRIPT, encoding="cp1251", errors="replace").read())
d = E["__defs"]["yantar_ghost_sleep"]
check("scene: level coop_l08_yantar, once, skip any, no movie need", d["level"] == "coop_l08_yantar" and d["once"] is True and d["skip"] == "any" and d["need"] is None)

files = {}
for sub in ("", "eng"):
    for n in ("dream_talk_l", "dream_talk_r"):
        p = os.path.join(VOICES, sub, n + ".ogg")
        ok = os.path.isfile(p)
        data = open(p, "rb").read() if ok else b""
        check("file %s exists, Ogg Vorbis, not empty" % os.path.join(sub, n + ".ogg"), ok and data[:4] == b"OggS" and b"vorbis" in data[:200] and len(data) > 10000,
              len(data))
        files[(sub, n)] = data
check("Russian and English recordings are different files", files[("", "dream_talk_l")] != files[("eng", "dream_talk_l")])

print("ALL PASS" if fails == 0 else "%d FAILED" % fails)
sys.exit(1 if fails else 0)
