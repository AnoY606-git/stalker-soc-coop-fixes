"""Offline check of the Full HD movie selection of the Scene Director (cutscenes_core), no game.
usage: python hd_mock_test.py     (needs `pip install lupa`, same package as the other mock tests)
Runs the REAL coop_scenes.script in a Lua 5.1 VM with an engine mock and proves:
  - hd_tutorial(name) answers "<name>_hd" only when textures\\intro_hd\\<movie>.ogm exists, else the name unchanged (also with cfg.hd = false,
    for names that are not movie blocks, and when getFS() raises);
  - a scene `need` whose normal movie is absent passes when the HD copy exists (and still fails when neither exists);
  - the tutorial step starts the HD block, falls back to the normal block when the HD block fails to start, and the normal block when no HD file;
  - every block in the HD table has a matching "<name>_hd" block in the ui xml files: same sound and window as the normal block, the video
    texture is intro_hd\\<movie> with the 1919x1076 source rectangle, the normal block still points at its old file and rectangle;
  - the movie names of the HD table are the 11 movies of the Enhanced Edition pack."""
import os
import re
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(PATCHES, "cutscenes_core", "gamedata", "scripts", "coop_scenes.script")
XMLS = [os.path.join(PATCHES, "cutscenes_core", "gamedata", "configs", "ui", "ui_soc_scenes.xml"),
        os.path.join(PATCHES, "cutscenes_pkg_yantar", "gamedata", "configs", "ui", "coop_scn_yantar.xml"),
        os.path.join(PATCHES, "cutscenes_pkg_monolith", "gamedata", "configs", "ui", "coop_scn_monolith.xml")]
BS = chr(92)

fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local src = ...
local E = { string = string, table = table, math = math, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber, tostring = tostring,
	type = type, setmetatable = setmetatable, rawget = rawget, error = error, select = select, unpack = unpack, next = next, print = print }
E._G = E
E.__exist = {}             -- "alias|path" -> true for files that exist
E.__fs_error = false
E.__started = {}           -- tutorial names handed to game.start_tutorial
E.__fail_start = {}        -- tutorial names that fail to start
E.__log = {}
local noop = function() end
E.printf_msg = function(fmt, s) E.__log[#E.__log + 1] = s end
E.getFS = function()
	if E.__fs_error then error("fs gone") end
	return { exist = function(self, alias, p) return E.__exist[alias .. "|" .. p] == true end }
end
E.game = { start_tutorial = function(n) if E.__fail_start[n] then error("no such tutorial " .. n) end E.__started[#E.__started + 1] = n end,
	has_active_tutorial = function() return false end, stop_tutorial = noop }
setmetatable(E, { __index = function(t, k) return setmetatable({}, { __index = function() return noop end, __call = noop }) end })
local f = assert(loadstring(src .. "\n__run_tutorial_step = nil\nfunction __missing_need(def) return missing_need(def) end\nfunction __exec(R, st, now) return exec_step(R, st, now) end\n", "coop_scenes"))
setfenv(f, E)
f()
return E
'''


def boot():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    src = open(SCRIPT, encoding="cp1251", errors="replace").read()
    return lua, lua.execute(PRELUDE, src)


def hd(E, movie, on=True):
    E["__exist"]["$game_textures$|intro_hd" + BS + movie + ".ogm"] = on or None


MOVIES = ["intro_stalker", "dream_rats", "dream_sarcofag", "dream_doctor", "dream_doctor_2",
          "final_blind", "final_gold", "final_to_monolith", "final_apocal", "final_immortal", "final_peace"]
TUT = {"soc_intro": "intro_stalker", "soc_dream_rats": "dream_rats", "soc_dream_sarcofag": "dream_sarcofag",
       "soc_dream_doctor": "dream_doctor", "soc_dream_doctor_2": "dream_doctor_2",
       "scn_yantar_dream": "dream_doctor", "scn_monolith_join": "dream_doctor_2",
       "soc_end_blind": "final_blind", "soc_end_gold": "final_gold", "soc_end_to_monolith": "final_to_monolith",
       "soc_end_apocal": "final_apocal", "soc_end_immortal": "final_immortal", "soc_end_peace": "final_peace"}

# ---- hd_tutorial / hd_exists ----
lua, E = boot()
r = [E.hd_tutorial(n) for n in TUT]
check("no HD file installed: every name unchanged", r == list(TUT), r)
for m in MOVIES:
    hd(E, m)
r = [E.hd_tutorial(n) for n in TUT]
check("all HD files installed: every block becomes <name>_hd", r == [n + "_hd" for n in TUT], r)
check("names that are not movie blocks stay as they are", E.hd_tutorial("credits_seq") == "credits_seq" and E.hd_tutorial("soc_black") == "soc_black"
      and E.hd_tutorial("scn_x18_card") == "scn_x18_card")
lua, E = boot()
hd(E, "dream_rats")
check("only dream_rats installed: only that block switches",
      E.hd_tutorial("soc_dream_rats") == "soc_dream_rats_hd" and E.hd_tutorial("soc_dream_sarcofag") == "soc_dream_sarcofag"
      and E.hd_tutorial("soc_intro") == "soc_intro")
E["__exist"]["$game_textures$|intro" + BS + "dream_rats.ogm"] = True      # the normal movie too: HD still wins
check("normal movie present as well: HD wins", E.hd_tutorial("soc_dream_rats") == "soc_dream_rats_hd")
E["cfg"]["hd"] = False
check("cfg.hd = false: normal block", E.hd_tutorial("soc_dream_rats") == "soc_dream_rats")
E["cfg"]["hd"] = True
E["__fs_error"] = True
check("getFS() raises: normal block, no error", E.hd_tutorial("soc_dream_rats") == "soc_dream_rats")
E["__fs_error"] = False
E["__exist"]["$game_textures$|intro_hd" + BS + "dream_rats.ogm"] = None
check("file removed again: normal block", E.hd_tutorial("soc_dream_rats") == "soc_dream_rats")

# ---- scene need ----
lua, E = boot()
need = lua.eval('{ need = { tex = { "intro' + BS * 2 + 'dream_rats.ogm" }, snd = { "x' + BS * 2 + 'a.ogg" } } }')
E["__exist"]["$game_sounds$|x" + BS + "a.ogg"] = True
check("need: neither the normal nor the HD movie: missing", E.__missing_need(need) == "intro" + BS + "dream_rats.ogm", E.__missing_need(need))
hd(E, "dream_rats")
check("need: only the HD movie: passes", E.__missing_need(need) is None, E.__missing_need(need))
E["cfg"]["hd"] = False
check("need: only the HD movie but cfg.hd = false: missing", E.__missing_need(need) == "intro" + BS + "dream_rats.ogm")
E["cfg"]["hd"] = True
hd(E, "dream_rats", False)
E["__exist"]["$game_textures$|intro" + BS + "dream_rats.ogm"] = True
check("need: only the normal movie: passes (old behaviour)", E.__missing_need(need) is None)
need2 = lua.eval('{ need = { tex = { "ui' + BS * 2 + 'final_peace.ogm" }, snd = {} } }')
hd(E, "final_peace")
check("need: ending path ui\\final_peace.ogm satisfied by intro_hd", E.__missing_need(need2) is None)
need3 = lua.eval('{ need = { tex = { "intro' + BS * 2 + 'something_else.ogm" }, snd = {} } }')
hd(E, "dream_rats")
check("need: a movie without an HD copy is not fooled by other HD files", E.__missing_need(need3) == "intro" + BS + "something_else.ogm")
need4 = lua.eval('{ need = { tex = { "ui' + BS * 2 + 'final_blind.ogm" }, snd = { "x' + BS * 2 + 'missing.ogg" } } }')
hd(E, "final_blind")
check("need: HD movie present, sound missing: the sound is reported", E.__missing_need(need4) == "x" + BS + "missing.ogg")

# ---- tutorial step ----
def step(E, lua, name):
    R = lua.eval("{ def = { length_ms = 1000, grace_ms = 1000 }, cams = {}, pps = {}, cpps = {}, snds = {} }")
    st = lua.eval('{ ["do"] = "tutorial", name = "%s", wait = true }' % name)
    E.__exec(R, st, 0)
    return R


lua, E = boot()
step(E, lua, "soc_dream_rats")
check("step: no HD file: the normal block starts", list(E["__started"].values()) == ["soc_dream_rats"], list(E["__started"].values()))
lua, E = boot()
hd(E, "dream_rats")
R = step(E, lua, "soc_dream_rats")
check("step: HD file: the _hd block starts, run marked as tutorial", list(E["__started"].values()) == ["soc_dream_rats_hd"] and R["tut"] is True,
      list(E["__started"].values()))
lua, E = boot()
hd(E, "dream_rats")
E["__fail_start"]["soc_dream_rats_hd"] = True
R = step(E, lua, "soc_dream_rats")
check("step: the _hd block fails to start: the normal block starts instead", list(E["__started"].values()) == ["soc_dream_rats"] and R["tut"] is True,
      list(E["__started"].values()))
lua, E = boot()
hd(E, "dream_rats")
E["__fail_start"]["soc_dream_rats_hd"] = True
E["__fail_start"]["soc_dream_rats"] = True
R = step(E, lua, "soc_dream_rats")
check("step: both fail: nothing starts, run not marked", list(E["__started"].values()) == [] and not R["tut"])
lua, E = boot()
hd(E, "dream_rats")
step(E, lua, "scn_x18_card")
check("step: a card block is never swapped", list(E["__started"].values()) == ["scn_x18_card"])

# ---- xml blocks ----
tab = {}
for p in XMLS:
    tab[p] = open(p, encoding="utf-8").read()
allx = "\n".join(tab.values())


def block(nm):
    m = re.search(r"<%s>(.*?)</%s>" % (nm, nm), allx, re.S)
    return m.group(1) if m else None


def strip_tex(b):
    return re.sub(r"<texture x=\"0\" y=\"1\" width=\"\d+\" height=\"\d+\">[^<]*</texture>", "<texture/>", b)


for name, movie in TUT.items():
    n, h = block(name), block(name + "_hd")
    check("xml: " + name + " and " + name + "_hd exist", n is not None and h is not None)
    if n is None or h is None:
        continue
    check("xml: " + name + "_hd differs from the normal block only in the video texture", strip_tex(n) == strip_tex(h))
    tn = re.search(r"<texture x=\"0\" y=\"1\" width=\"(\d+)\" height=\"(\d+)\">([^<]*)</texture>", n)
    th = re.search(r"<texture x=\"0\" y=\"1\" width=\"(\d+)\" height=\"(\d+)\">([^<]*)</texture>", h)
    check("xml: " + name + ": normal block keeps its old 512x28x rectangle and file",
          tn is not None and tn.group(1) == "512" and tn.group(3).split(BS)[-1] == movie and "intro_hd" not in tn.group(3), tn.groups() if tn else None)
    check("xml: " + name + "_hd: 1919x1076 of intro_hd\\" + movie,
          th is not None and (th.group(1), th.group(2), th.group(3)) == ("1919", "1076", "intro_hd" + BS + movie), th.groups() if th else None)
    check("xml: " + name + "_hd keeps window 1024x768 stretch", re.search(r'<video_wnd x="0" y="0" width="1024" height="768" stretch="1">', h) is not None)

# the table of the script matches the test table
src = open(SCRIPT, encoding="cp1251", errors="replace").read()
tbl = dict(re.findall(r"(\w+) = \"(\w+)\"", src[src.index("local HD_TUTORIALS"):src.index("-- true when the HD file")]))
check("script table HD_TUTORIALS equals the expected 13 blocks", tbl == TUT, set(tbl.items()) ^ set(TUT.items()))
mv = re.search(r"local HD_MOVIES = \{(.*?)\n\}", src, re.S).group(1)
check("script table HD_MOVIES equals the 11 movies", sorted(re.findall(r"(\w+) = true", mv)) == sorted(MOVIES))

print("hd_mock_test: %s" % ("ALL PASS" if fails == 0 else "%d FAIL" % fails))
sys.exit(1 if fails else 0)
