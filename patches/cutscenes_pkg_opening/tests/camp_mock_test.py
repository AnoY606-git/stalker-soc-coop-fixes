"""Offline check (no game) of the two server ticks of coop_soc_opening.script: the campfire move of non-story players and the task chain.
usage: python camp_mock_test.py     (needs `pip install lupa`, like voice_lang_mock_test.py)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with position / section, vector, level tick) and proves:
  * the story character (section actor_the_main_character) is never moved; a non-story player is moved ONCE to a free campfire spot (spots differ,
    4 m apart, 3.5 to 5 m from the fire), and not again after a respawn, a load (the flag is kept), or a second tick
  * a player still in the lobby is not touched; a player far from the bunker (an old save) is only marked; nothing happens after the flash drive
  * the test flag COOP_OPEN_TEST_NONSTORY makes the story section count as non-story
  * the start chain: the three SoC tasks appear for EVERY player at the right stage, once, and the old Akasi tasks are never offered"""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local script_path = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}                 -- "task|player" -> count
E.__calls = {}
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return true end
function E.OnClient() return false end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
-- vector
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function V:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
-- story flags (like the engine: any name, upper case)
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__setpos(o, x, y, z) o.__pos = E.vector():set(x, y, z) end
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
-- level / scenes / db
E.__level = "coop_l01_escape"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.coop_scenes = { cfg = { lobby = { x = 105.0, y = -15.8, z = -9.8, r = 25.0 } } }
E.db = { mp_actors = {} }
function E.__player(id, name, section, x, y, z)
	local o = { __id = id, __name = name, __section = section, __alive = true, __pos = E.vector():set(x, y, z), __dir = nil, __moves = 0 }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:section() return self.__section end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:set_actor_position(v) self.__pos = E.vector():set(v.x, v.y, v.z); self.__moves = self.__moves + 1 end
	function o:set_actor_direction(a) self.__dir = a end
	E.db.mp_actors[id] = o
	return o
end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_soc_opening"))
setfenv(fn, env)
fn()
E.coop_soc_opening = env
E.__env = env
return E
'''


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    E = lua.execute(PRELUDE, os.path.join(PATCH, "gamedata", "scripts", "coop_soc_opening.script"))
    env = E["__env"]

    def tick(ms=3000):
        """run the registered level call once after ms game milliseconds"""
        E["__time"] = E["__time"] + ms
        for f in list(E["__calls"].values()):
            f()

    def reset():
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__time"] = E["__time"] + 100000

    def player(pid, name, section, x, y, z):
        return E["__player"](pid, name, section, x, y, z)

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(n):
        E["story_flags"]["give_flag"](n)

    def fire_dist(p):
        pos = p.position(p)
        return ((pos.x + 206.9) ** 2 + (pos.z + 140.1) ** 2) ** 0.5

    def spot_of(p):
        pos = p.position(p)
        return (round(pos.x, 2), round(pos.y, 2), round(pos.z, 2))

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v is not None else 0

    env.install()
    BUNK = (-246.4, -24.8, -134.4)

    # ---- campfire move
    reset()
    s = player(1, "qaa", "actor_the_main_character", -246.4, -24.8, -133.7)       # story
    a = player(2, "qab", "actor_partner_regular", -246.4, -24.8, -135.1)
    b = player(3, "qac", "actor_partner_regular", -247.8, -24.8, -134.4)
    tick(1000)
    check("before the settle time nobody is moved", a.__moves == 0 and b.__moves == 0 and s.__moves == 0)
    tick(3000)
    check("story character stays in the bunker", s.__moves == 0 and abs(s.position(s).x + 246.4) < 0.1)
    check("non-story player A moved once to the campfire", a.__moves == 1 and 3.5 <= fire_dist(a) <= 5.0, fire_dist(a))
    check("non-story player B moved once to the campfire", b.__moves == 1 and 3.5 <= fire_dist(b) <= 5.0, fire_dist(b))
    check("A and B stand on different spots at least 4 m apart", spot_of(a) != spot_of(b) and
          ((a.position(a).x - b.position(b).x) ** 2 + (a.position(a).z - b.position(b).z) ** 2) ** 0.5 >= 4.0)
    check("per player flags are set for the non-story players only", flag("COOP_OPEN_CAMP_QAB") and flag("COOP_OPEN_CAMP_QAC") and not flag("COOP_OPEN_CAMP_QAA"))
    check("direction was turned to the fire", a.__dir is not None)
    tick(3000)
    tick(3000)
    check("later ticks do not move anybody again", a.__moves == 1 and b.__moves == 1)
    # a respawn: the engine puts A back on a bunker point
    E["__setpos"](a, *BUNK)
    tick(3000)
    tick(3000)
    check("after a respawn (flag kept) A is NOT moved again", a.__moves == 1 and abs(a.position(a).x + 246.4) < 0.1)
    # a "load": flags come back from the save, players are where the save put them (at the fire): nothing moves
    E["__setpos"](b, -209.3, -20.15, -143.5)
    tick(3000)
    check("after a load nobody is moved", b.__moves == 1)

    # ---- lobby, old save, flash drive handed in
    reset()
    lob = player(5, "qad", "actor_partner_regular", 105.0, -15.8, -9.8)
    tick(3000)
    tick(3000)
    check("a player in the lobby is not touched, no flag", lob.__moves == 0 and not flag("COOP_OPEN_CAMP_QAD"))
    E["__setpos"](lob, -246.4, -24.8, -134.4)       # READY: spawns at the bunker
    tick(1000)
    check("just out of the lobby: not yet (settle)", lob.__moves == 0)
    tick(3000)
    check("out of the lobby and settled: moved", lob.__moves == 1 and 3.5 <= fire_dist(lob) <= 5.0)

    reset()
    old = player(6, "qae", "actor_partner_regular", -100.0, -20.0, -50.0)       # an old save: somewhere else on Cordon
    tick(3000)
    tick(3000)
    check("far from the bunker (old save): marked, never moved", old.__moves == 0 and flag("COOP_OPEN_CAMP_QAE"))

    reset()
    give("ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO")
    late = player(7, "qaf", "actor_partner_regular", -246.4, -24.8, -134.4)
    tick(3000)
    tick(3000)
    check("after the flash drive hand-in nobody is moved", late.__moves == 0 and not flag("COOP_OPEN_CAMP_QAF"))

    # ---- test override
    reset()
    give("COOP_OPEN_TEST_NONSTORY")
    h = player(8, "qag", "actor_the_main_character", -246.4, -24.8, -134.4)
    check("is_story false with the test flag", env.is_story(h) is False)
    tick(3000)
    tick(3000)
    check("test flag: the story section is moved like a non-story player", h.__moves == 1 and 3.5 <= fire_dist(h) <= 5.0)
    reset()
    h = player(9, "qah", "actor_the_main_character", -246.4, -24.8, -134.4)
    check("is_story true without the flag", env.is_story(h) is True)

    # ---- task chain: every player, right stage, once
    reset()
    p1 = player(11, "qaa", "actor_the_main_character", -246.4, -24.8, -134.4)
    p2 = player(12, "qab", "actor_partner_regular", -247.8, -24.8, -134.4)
    SOC = ("esc_soc_trader_job_task", "esc_soc_railroad_passage_task", "esc_soc_military_documents_task")
    tick(3000)
    check("start: no SoC next task yet", all(given(t, 11) == 0 and given(t, 12) == 0 for t in SOC))
    check("start: both players got the opening tasks", given("esc_start_talk_to_the_sidorovich_quest_task", 11) == 1 and given("esc_start_talk_to_the_sidorovich_quest_task", 12) == 1)
    give("ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO")
    tick(3000)
    give("ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO")       # flash drive handed in (this phrase also gives the helicopter flag silently)
    give("ESC_HELICOPTER_GO_TO_AGROPROM_INFO")
    tick(3000)
    check("after the hand-in EVERY player gets 'Work for the trader'", given(SOC[0], 11) == 1 and given(SOC[0], 12) == 1)
    check("after the hand-in the job tasks are not given yet", given(SOC[1], 11) == 0 and given(SOC[2], 12) == 0)
    check("the flash drive task is closed (not given again)", given("esc_start_find_stalker_shustry_quest_task", 11) <= 1)
    tick(3000)
    check("'Work for the trader' is given once per player", given(SOC[0], 11) == 1 and given(SOC[0], 12) == 1)
    give("ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO")   # Sidorovich's military case talk
    tick(3000)
    check("after the job talk EVERY player gets both job tasks", all(given(t, pid) == 1 for t in SOC[1:] for pid in (11, 12)))
    check("'Work for the trader' is not given again", given(SOC[0], 11) == 1)
    for old in ("esc_start_talk_to_the_sidorovich_quest_1_task", "esc_start_talk_to_the_fox_quest_1_task", "esc_start_talk_to_the_fox_quest_2_task",
                "esc_start_5_bottles_of_vodka_for_kuznetsov_quest_task"):
        check("old level maker task never offered: " + old, given(old, 11) == 0 and given(old, 12) == 0)
    # a player who joins later gets the open tasks too
    p3 = player(13, "qac", "actor_partner_regular", -247.8, -24.8, -134.4)
    tick(3000)
    check("a late joiner gets the open SoC tasks", given(SOC[1], 13) == 1 and given(SOC[2], 13) == 1 and given(SOC[0], 13) == 0)
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    give("BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO")
    p4 = player(14, "qad2", "actor_partner_regular", -247.8, -24.8, -134.4)
    tick(3000)
    check("stages closed: nothing new for a player who joins after the Garbage / the Barkeep", given(SOC[1], 14) == 0 and given(SOC[2], 14) == 0)

    print("\n" + ("ALL PASS" if fails == 0 else "FAILED (%d)" % fails))
    sys.exit(1 if fails else 0)


main()
