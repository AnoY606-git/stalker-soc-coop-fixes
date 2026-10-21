"""Offline check (no game) of coop_soc_doctor.script: the Guide / Doctor chain tick, the dialog preconditions, the Doctor's creation, the voice lines.
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with position, alife().create / object, task hand-out)."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
fails = 0
total = 0


def check(name, ok, info=""):
    global fails, total
    total += 1
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local path, patch_root = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}                 -- "task|player" -> count
E.__calls = {}
E.__client = false
E.__played = {}
E.__voice_lang = "eng"
E.__created = {}               -- list of {section, x, y, z, lv, gv, id}
E.__fail_create = false
E.__story = {}                 -- story id -> server entity id
E.__objects = {}               -- entity id -> { section, alive }
E.__unregistered = 0
E.__added = {}
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return not E.__client end
function E.OnClient() return E.__client end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
E.__level = "coop_l01_escape"
local nextid = 100
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.get_story_object_id = function(s) return E.__story[s] end
E.unregister_story_id = function(s) E.__story[s] = nil; E.__unregistered = E.__unregistered + 1 end
E.add_story_object = function(id, s) E.__story[s] = id; E.__added[#E.__added + 1] = s end
E.alife = function() return {
	create = function(self, section, pos, lv, gv, parent)
		if E.__fail_create then error("create failed") end
		nextid = nextid + 1
		local se = { id = nextid, section = section }
		E.__objects[se.id] = { section = section, alive = true }
		E.__created[#E.__created + 1] = { section = section, x = pos.x, y = pos.y, z = pos.z, lv = lv, gv = gv, id = se.id }
		if section == "soc_cit_doctor" then E.__story["soc_cit_doctor"] = se.id end
		return se
	end,
	object = function(self, id)
		local o = E.__objects[id]
		if o == nil then return nil end
		return { id = id, section_name = function() return o.section end, alive = function() return o.alive end }
	end } end
E.db = { mp_actors = {}, storage = {}, spawned_vertex_by_id = {} }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z), __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec) if self.__items[sec] then return true end return nil end
	function o:level_vertex_id() return 1 end
	function o:game_vertex_id() return 2 end
	E.db.mp_actors[id] = o
	return o
end
E.coop_soc_opening = { voice_lang = function() return E.__voice_lang end }
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
local function mk_sound(p)
	local s = { path = p }
	function s:playing() return false end
	function s:stop() end
	function s:play(o, d, f) E.__played[#E.__played + 1] = p end
	return s
end
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(t, p) return mk_sound(p) end })
E.__me = nil
function E.getLocalActor() return E.__me end
E.getFS = function() return { exist = function(self, root, name)
	local f = io.open(patch_root .. "/gamedata/sounds/" .. string.gsub(name, "\\", "/"), "rb")
	if f then f:close() return true end
	return false end } end
E.game = { translate_string = function(s) return "Windowed" end }

local f = io.open(path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_soc_doctor"))
setfenv(fn, env)
fn()
E.coop_soc_doctor = env
return E
'''

DOCS = "X16_GHOST_DOCS_TAKEN"
GUIDE = "ESC_FIND_DOCTOR_START"
MET = "ESC_FIND_DOCTOR_DONE"
TASK = "CIT_JAIL_DOCTOR_PRYP_TASK"
CONCL = "CIT_DOCTOR_MEET_CONCLUSION_INFO"
GOT = "PRI_MONOLITH_DECODER_GOT"
CLOSED = "SOC_DOC_CLOSED"
YAN_G = "YAN_SOC_GUIDE_MET"
CORDON, UG, PRI = "coop_l01_escape", "coop_l03_agroprom_underground", "coop_l10_pripyat"
DOC_POS = (-69.7555, -6.8732, -70.4957)
KNOCK = (-75.4297, -6.8732, -74.6515)


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    E = lua.execute(PRELUDE, os.path.join(PATCH, "gamedata", "scripts", "coop_soc_doctor.script"), PATCH.replace("\\", "/"))
    D = E["coop_soc_doctor"]

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(n):
        E["story_flags"]["give_flag"](n)

    def reset(level=CORDON):
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["db"]["storage"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__created"] = lua.table_from({})
        E["__story"] = lua.table_from({})
        E["__objects"] = lua.table_from({})
        E["__added"] = lua.table_from({})
        E["__fail_create"] = False
        E["__client"] = False
        E["__level"] = level
        E["__time"] = 0
        E["__played"] = lua.table_from({})
        D["reset_given"]()

    def player(pid, x=0.0, y=0.0, z=0.0):
        return E["__player"](pid, "p%d" % pid, x, y, z)

    def move(p, x, y, z):
        p["__pos"] = E["vector"]()
        p["__pos"]["x"], p["__pos"]["y"], p["__pos"]["z"] = x, y, z

    def step(dt=1000):
        E["__time"] = E["__time"] + dt
        return D["step"](E["__time"])

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def all_tasks():
        return sorted(k for k in E["__given"].keys())

    def created():
        return [E["__created"][i] for i in range(1, len(E["__created"]) + 1)]

    # ------------------------------------------------------------------ nothing happens without the chain
    reset()
    p1, p2 = player(1, 0, 0, 0), player(2, 3, 0, 0)
    step(); step()
    check("no flag: no task, no Doctor, no flag set", all_tasks() == [] and created() == [] and not flag(GUIDE) and not flag(CLOSED) and not flag(YAN_G), all_tasks())
    check("Guide topic is closed before Ghost's documents", not D["st_g_open"](None, None))
    give(DOCS)
    check("Guide topic opens with Ghost's documents", D["st_g_open"](None, None))
    step()
    check("... and still no task (the dialog was not used)", all_tasks() == [])

    # ------------------------------------------------------------------ the Guide spoke (Cordon)
    give(GUIDE)
    check("after the Guide spoke the topic is gone", not D["st_g_open"](None, None))
    step()
    check("'Meet with Doctor' to BOTH players", given("soc_doc_meet_task", 1) == 1 and given("soc_doc_meet_task", 2) == 1, all_tasks())
    check("'Meet the Guide' of the Yantar chain is done by the dialog flag", flag(YAN_G))
    check("on Cordon the Doctor is not created", created() == [])
    step(); step()
    check("tasks are given once per player", given("soc_doc_meet_task", 1) == 1 and len(all_tasks()) == 2, all_tasks())
    p3 = player(3, 1, 0, 0)
    step()
    check("a late joiner gets the open task", given("soc_doc_meet_task", 3) == 1, all_tasks())
    check("the stash task is not given yet", given("soc_doc_stash_task", 1) == 0)

    # ------------------------------------------------------------------ the underground: the Doctor is created once
    E["__level"] = UG
    D["reset_given"]()
    move(p1, -20, -6, -10); move(p2, -21, -6, -10); move(p3, -19, -6, -10)
    step()
    c = created()
    check("the Doctor is created once on the underground", len(c) == 1 and c[0]["section"] == "soc_cit_doctor", [x["section"] for x in c])
    if c:
        check("at the SoC position", abs(c[0]["x"] - DOC_POS[0]) < 0.01 and abs(c[0]["y"] - DOC_POS[1]) < 0.01 and abs(c[0]["z"] - DOC_POS[2]) < 0.01)
        check("with the AI node 3563 and game vertex 689 of the room", c[0]["lv"] == 3563 and c[0]["gv"] == 689, (c[0]["lv"], c[0]["gv"]))
        check("the spawned vertex is registered like the technician's", E["db"]["spawned_vertex_by_id"][c[0]["id"]] == 3563)
    step(); step(); step()
    check("... and not again on later ticks", len(created()) == 1)
    check("the task is given again once on the new level load", given("soc_doc_meet_task", 1) == 2 or given("soc_doc_meet_task", 1) == 1)
    check("far from the hiding place: not met yet", not flag(MET))

    # ------------------------------------------------------------------ a player comes to the hiding place
    move(p2, KNOCK[0] + 3, KNOCK[1], KNOCK[2])
    step()
    check("a player within 8 m of the SoC knock-out zone: ESC_FIND_DOCTOR_DONE", flag(MET))
    p4 = player(4, 0, -6, 0)
    step()
    check("'Meet with Doctor' is not offered any more (late joiner)", given("soc_doc_meet_task", 4) == 0)
    check("the Doctor's greeting is the first-meeting line", D["st_h_first"](None, None) and not D["st_h_after"](None, None))
    check("his talk is open", D["st_d_open"](None, None))
    check("no stash task before the talk", given("soc_doc_stash_task", 1) == 0)

    # ------------------------------------------------------------------ the talk (dialog flags)
    give(TASK); give(CONCL)
    step()
    check("after the talk: the greeting is the second one, the talk is closed", D["st_h_after"](None, None) and not D["st_h_first"](None, None) and not D["st_d_open"](None, None))
    check("'Secret stash at Pripyat' to every living player", all(given("soc_doc_stash_task", i) == 1 for i in (1, 2, 3, 4)), all_tasks())
    step(); step()
    check("... once", all(given("soc_doc_stash_task", i) == 1 for i in (1, 2, 3, 4)))
    p5 = player(5, 0, -6, 0)
    step()
    check("a respawned / late player gets the stash task", given("soc_doc_stash_task", 5) == 1)
    p5["__alive"] = False
    p6 = player(6, 0, -6, 0)
    p6["__alive"] = False
    step()
    check("a dead player is skipped", given("soc_doc_stash_task", 6) == 0)
    check("the Doctor chain flags are monotonic (talk implies met)", flag(MET))

    # ------------------------------------------------------------------ on the way: another level, then the decoder
    E["__level"] = CORDON
    D["reset_given"]()
    E["__given"] = lua.table_from({})
    step()
    check("on Cordon (new level load) the stash task is given again", given("soc_doc_stash_task", 1) == 1 and given("soc_doc_meet_task", 1) == 0, all_tasks())
    check("the Doctor is not touched on Cordon", len(created()) == 1)
    give(GOT)
    step()
    check("decoder taken: the chain is closed", flag(CLOSED))
    D["reset_given"](); E["__given"] = lua.table_from({})
    step()
    check("... no task is given any more", all_tasks() == [], all_tasks())

    # ------------------------------------------------------------------ a party that skips the Doctor
    reset(UG)
    player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    E["__level"] = PRI
    step()
    check("Pripyat reached without the Doctor: the chain closes", flag(CLOSED) and flag(MET) and flag(TASK))
    check("... no tasks, no Doctor, the Guide topic is gone", all_tasks() == [] and created() == [] and not D["st_g_open"](None, None), all_tasks())
    E["__level"] = UG
    step(); step()
    check("... and he is not created later on the underground", created() == [])

    # ------------------------------------------------------------------ Pripyat reached with Ghost's documents but without ever meeting the Guide
    reset(PRI)
    player(1, 0, 0, 0)
    give(DOCS)
    step()
    check("Pripyat reached without the Guide: \"Meet the Guide\" of the Yantar chain is closed", flag(CLOSED) and flag(YAN_G) and all_tasks() == [], all_tasks())


    # ------------------------------------------------------------------ freeplay: every flag stays set after the ending, nothing replays
    reset(CORDON)
    p = player(1, 0, 0, 0)
    for f in (DOCS, GUIDE, MET, TASK, CONCL, GOT, CLOSED, YAN_G):
        give(f)
    step(); step()
    check("freeplay on Cordon: nothing is given", all_tasks() == [] and created() == [], all_tasks())
    E["__level"] = UG
    step(); step()
    check("freeplay on the underground: no Doctor, no task", all_tasks() == [] and created() == [])
    check("freeplay: the Guide topic stays closed", not D["st_g_open"](None, None))

    # ------------------------------------------------------------------ the Doctor died / cannot be created
    reset(UG)
    p = player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    step()
    id1 = created()[0]["id"]
    E["__objects"][id1]["alive"] = False
    step()
    check("a dead Doctor does not block: the talk flags are given", flag(TASK) and flag(CONCL))
    step()
    check("... and the stash task follows", given("soc_doc_stash_task", 1) == 1)

    reset(UG)
    p = player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    E["__fail_create"] = True
    for _ in range(6):
        step()
    check("a create that fails is tried 3 times, then left alone, the meet task still works", len(created()) == 0 and given("soc_doc_meet_task", 1) == 1)
    E["__fail_create"] = False
    for _ in range(3):
        step()
    check("... (no endless retries)", len(created()) == 0)
    check("... and the chain is not blocked", not flag(CLOSED))

    # registry lost, entity still exists: re-registered, not duplicated
    reset(UG)
    p = player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    step()
    id1 = created()[0]["id"]
    E["__story"] = lua.table_from({})
    step()
    check("registry lost: the existing Doctor is re-registered, not created again", len(created()) == 1 and len(E["__added"]) == 1)
    # registry points to a gone entity: dropped, a new one is created
    reset(UG)
    p = player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    E["__story"]["soc_cit_doctor"] = 9999
    step()
    check("a stale registry entry is dropped and the Doctor is created", E["__unregistered"] >= 1 and len(created()) == 1)

    # no player online: nothing is created
    reset(UG)
    give(DOCS); give(GUIDE)
    step(); step()
    check("no player online: no Doctor", created() == [])

    # ------------------------------------------------------------------ the client side does nothing to the world
    reset(UG)
    p = player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    E["__client"] = True
    check("a client does not create the Doctor", D["ensure_doctor"]() is None and created() == [])
    E["__client"] = False

    # ------------------------------------------------------------------ install: the tick only works on the server
    reset(UG)
    p = player(1, -20, -6, -10)
    give(DOCS); give(GUIDE)
    n0 = len(E["__calls"])
    D["install"]()
    check("install registers one tick", len(E["__calls"]) == n0 + 1)
    tick = E["__calls"][len(E["__calls"])]
    E["__time"] = 5000
    tick()
    check("the tick creates the Doctor and gives the task (server)", len(created()) == 1 and given("soc_doc_meet_task", 1) == 1)
    D["install"]()
    check("an older tick stops after a reinstall", tick() is True)

    # ------------------------------------------------------------------ voice and PDA archive
    reset(UG)
    me = player(1, 0, 0, 0)
    other = player(2, 0, 0, 0)
    E["__me"] = me
    E["__client"] = True
    E["__voice_lang"] = "eng"
    D["say_d1"](me, other)
    played = [str(E["__played"][i]) for i in range(1, len(E["__played"]) + 1)]
    check("English: the Doctor's line has the original voice", played == ["characters_voice\\dialogs\\eng\\cit_doctor_main_dialog_1"], played)
    E["__time"] = E["__time"] + 5000
    D["say_dh11"](me, other)
    played = [str(E["__played"][i]) for i in range(1, len(E["__played"]) + 1)]
    check("English: the greeting has its voice", played[-1] == "characters_voice\\dialogs\\eng\\cit_doctor_hello_dialog_11", played)
    n = len(played)
    D["say_d11"](me, other)
    D["say_g3"](me, other)
    D["say_g0"](me, other)
    check("the player's own lines and the Guide have no recording: silent", len(E["__played"]) == n)
    E["__voice_lang"] = "rus"
    E["__time"] = E["__time"] + 5000
    D["say_d2"](me, other)
    check("Russian: silent (the Russian SoC has no recording)", len(E["__played"]) == n)
    check("the archive line is emitted and the speaker is registered",
          E["coop_pda_phrases"]["phrase_speaker"]["coop_soc_doc_d_1"] == "npc" and E["coop_pda_phrases"]["phrase_speaker"]["coop_soc_doc_d_11"] == "actor"
          and E["coop_pda_phrases"]["phrase_speaker"]["coop_soc_doc_g_3"] == "npc" and E["coop_pda_phrases"]["phrase_speaker"]["coop_soc_doc_g_0"] == "actor")
    E["__voice_lang"] = "eng"
    E["__time"] = E["__time"] + 5000
    n = len(E["__played"])
    stranger = player(3, 0, 0, 0)
    D["say_d3"](stranger, stranger)
    check("a talk of two other players is not played to this machine", len(E["__played"]) == n)
    E["__client"] = False

    print("\n%d checks, %d failed" % (total, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
