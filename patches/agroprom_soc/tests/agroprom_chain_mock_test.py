"""Offline check (no game) of the server tick of coop_scn_agroprom_soc.script.
usage: python agroprom_chain_mock_test.py     (needs `pip install lupa`, like patches\\cutscenes_pkg_opening\\tests\\camp_mock_test.py)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with position and inventory, level tick) and proves:
  * every task of the chain is handed to EVERY player, once, at the right stage; a late joiner gets the tasks of the open stage only
  * a stage closes when its task is complete (no completed task comes back after a reload / a new Lua VM)
  * Mole dead before the talk: the route flag is given and the chain goes on (go down to the underground)
  * the case with the documents in an inventory sets the flag the Cordon documents task follows
  * underground: stash box proximity, the flash drive in an inventory, the Ghost task on any level, dead players get nothing
"""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
fails = 0
n_checks = 0


def check(name, ok, info=""):
    global fails, n_checks
    n_checks += 1
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
E.__given = {}
E.__calls = {}
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return true end
function E.OnClient() return false end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function V:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__setpos(o, x, y, z) o.__pos = E.vector():set(x, y, z) end
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
E.__level = "coop_l03_agroprom"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.db = { mp_actors = {} }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z), __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec) return self.__items[sec] end
	E.db.mp_actors[id] = o
	return o
end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_scn_agroprom_soc"))
setfenv(fn, env)
fn()
E.__env = env
return E
'''


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    path = os.path.join(PATCH, "gamedata", "scripts", "coop_scn_agroprom_soc.script")
    st = {}

    def tick(ms=1500):
        E = st["E"]
        E["__time"] = E["__time"] + ms
        for f in list(E["__calls"].values()):
            f()

    def reset(level="coop_l03_agroprom"):
        """a new Lua VM (a level load): fresh script state, empty flags"""
        E = lua.execute(PRELUDE, path)
        E["__level"] = level
        st["E"] = E
        st["env"] = E["__env"]
        st["env"].install()

    def player(pid, name, x=0.0, y=0.0, z=0.0):
        return st["E"]["__player"](pid, name, x, y, z)

    def flag(n):
        return st["E"]["story_flags"]["has_flag"](n)

    def give(n):
        st["E"]["story_flags"]["give_flag"](n)

    def given(task, pid):
        v = st["E"]["__given"][task + "|" + str(pid)]
        return int(v) if v is not None else 0

    def all_once(task, pids):
        return all(given(task, p) == 1 for p in pids)

    def none(task, pids):
        return all(given(task, p) == 0 for p in pids)

    MAIN = "agr_start_follow_the_stalker_mole_quest_task"
    HSTK = "agr_soc_help_stalkers_task"
    HKROT = "agr_start_save_the_stalker_mole_quest_task"
    DOWN = "agr_start_go_to_the_agroprom_underground_quest_task"
    STASH = "agru_start_find_the_shooter_hiding_place_task"
    GHOST = "agr_soc_find_ghost_task"
    MOLE_TALK = "AGR_SMART_TERRAIN_7_STALKER_MOLE_TALK_TO_THE_STALKER_MOLE_STOP_DIALOG_INFO"

    # ---- Agroprom: arrival, the call, the fight, Mole's talk
    reset()
    a = player(1, "qaa")
    b = player(2, "qab")
    tick()
    check("before the arrival nothing is given", all(none(t, (1, 2)) for t in (MAIN, HSTK, HKROT, DOWN, STASH, GHOST)))
    give("AGR_STALKER_HELP_1_INFO")
    tick()
    check("arrival (gate flag): 'Get information about Strelok' for EVERY player, once", all_once(MAIN, (1, 2)))
    check("arrival: 'Help the stalkers' for EVERY player, once", all_once(HSTK, (1, 2)))
    check("arrival: 'Save Mole' not yet", none(HKROT, (1, 2)))
    tick()
    tick()
    check("later ticks do not give again", all_once(MAIN, (1, 2)) and all_once(HSTK, (1, 2)))
    give("AGR_THE_ORDER_TO_KILL_STALKER_SPACE_RESTRICTOR_INFO")
    tick()
    check("Mole's call (camera flight flag): 'Save Mole' for EVERY player, once", all_once(HKROT, (1, 2)))
    c = player(3, "qac")
    tick()
    check("late joiner: gets the open stage (main, help stalkers, save Mole) once", all_once(MAIN, (3,)) and all_once(HSTK, (3,)) and all_once(HKROT, (3,)))
    check("late joiner: not the stash tasks", none(DOWN, (3,)) and none(STASH, (3,)) and none(GHOST, (3,)))
    give("AGR_SMART_TERRAIN_5_MILITARY_1_SQUAD_DEAD")
    d = player(4, "qad")
    tick()
    check("first soldiers dead: 'Help the stalkers' is over, a joiner now does not get it", none(HSTK, (4,)))
    check("first soldiers dead: the joiner still gets 'Save Mole' (second squad alive) and the main task", all_once(HKROT, (4,)) and all_once(MAIN, (4,)))
    give("AGR_SMART_TERRAIN_5_MILITARY_2_SQUAD_DEAD")
    e = player(5, "qae")
    tick()
    check("both squads dead: 'Save Mole' is over for a joiner, the main task still open", none(HKROT, (5,)) and all_once(MAIN, (5,)))
    check("flag of the talk is not set by itself", not flag(MOLE_TALK))
    give(MOLE_TALK)                                  # Mole's dialog, last phrase
    f = player(6, "qaf")
    tick()
    check("route given: 'go down' (stash) for EVERY player, once", all_once(DOWN, (1, 2, 3, 4, 5, 6)))
    check("route given: the main task is over (a joiner does not get it)", none(MAIN, (6,)))
    give("AGR_START_GO_TO_THE_AGROPROM_UNDERGROUND_QUEST_TASK_INFO")
    g = player(7, "qag")
    tick()
    check("in the underground: 'go down' is over", none(DOWN, (7,)))

    # ---- Mole dead before the talk (fallback)
    reset()
    a = player(1, "qaa")
    b = player(2, "qab")
    give("AGR_STALKER_HELP_1_INFO")
    give("AGR_THE_ORDER_TO_KILL_STALKER_SPACE_RESTRICTOR_INFO")
    tick()
    check("fight: Save Mole given to both", all_once(HKROT, (1, 2)))
    give("AGR_SMART_TERRAIN_4_STALKER_MOLE_SQUAD_DEAD")
    tick()
    check("Mole dead: the route flag is given (SoC: his flash drive)", flag(MOLE_TALK))
    tick()
    check("Mole dead: 'go down' (stash) given to every player, once", all_once(DOWN, (1, 2)))
    h = player(3, "qah")
    tick()
    check("Mole dead: a joiner gets no 'Save Mole' (over) and no main task, but the way down", none(HKROT, (3,)) and none(MAIN, (3,)) and all_once(DOWN, (3,)))

    # ---- documents
    reset()
    a = player(1, "qaa")
    b = player(2, "qab")
    tick()
    check("no case: the documents flag is not set", not flag("AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"))
    b.__items["agr_safe_container_1"] = lua.table_from({})
    tick()
    check("a player picked up the case: the documents flag (Cordon task: take it to the Barkeep) is set", flag("AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"))

    reset("coop_l02_garbage")
    a = player(1, "qaa")
    a.__items["agr_safe_container_1"] = lua.table_from({})
    tick()
    check("the case in an inventory is noticed on any level (Garbage)", flag("AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"))

    # ---- underground
    reset("coop_l03_agroprom_underground")
    a = player(1, "qaa", -38.5, -3.9, 41.3)
    b = player(2, "qab", -38.0, -3.9, 40.0)
    tick()
    check("underground: the stash task for EVERY player, once", all_once(STASH, (1, 2)))
    check("underground: not the surface tasks", all(none(t, (1, 2)) for t in (MAIN, HSTK, HKROT, DOWN)))
    check("underground: stash not found at the entrance", not flag("AGRU_SOC_STASH_FOUND"))
    check("underground: no Ghost task before the flash drive", none(GHOST, (1, 2)))
    st["E"]["__setpos"](a, -69.0, -5.7, -63.0)
    tick()
    check("a player stands at the stash: AGRU_SOC_STASH_FOUND (objective 2 text)", flag("AGRU_SOC_STASH_FOUND"))
    check("stash found only: still no flash flag, no Ghost task", not flag("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO") and none(GHOST, (1, 2)))
    a.__items["dev_flash_agru"] = lua.table_from({})
    tick()
    check("flash drive in an inventory: flag set (objective 3 text, marker dropped)", flag("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO"))
    check("flash drive: 'Find out what happened to Ghost' for EVERY player, once", all_once(GHOST, (1, 2)))
    tick()
    tick()
    check("Ghost task is not given again", all_once(GHOST, (1, 2)))
    c = player(3, "qac", -40.0, -3.9, 40.0)
    c.__alive = False
    tick()
    check("a dead player gets nothing", none(STASH, (3,)) and none(GHOST, (3,)))
    c.__alive = True
    tick()
    check("alive again: he gets the stash task and the Ghost task once", all_once(STASH, (3,)) and all_once(GHOST, (3,)))
    # surface again: the underground stage is over, Ghost goes on on any level
    give("AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO")
    d = player(4, "qad", -40.0, -3.9, 40.0)
    tick()
    check("back on the surface: a joiner in the underground does not get the stash task (done), Ghost goes on", none(STASH, (4,)) and all_once(GHOST, (4,)))

    # ---- Ghost on another level (Bar, Yantar): any level, until the X16 documents / the Saharov fallback
    reset("coop_l05_bar")
    give("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO")
    a = player(1, "qaa")
    tick()
    check("Bar: the Ghost task is given on any level (a player who joined late)", all_once(GHOST, (1,)))
    check("Bar: no Agroprom task", all(none(t, (1,)) for t in (MAIN, HSTK, HKROT, DOWN, STASH)))
    reset("coop_l08_yantar")
    give("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO")
    give("X16_GHOST_DOCS_TAKEN")
    a = player(1, "qaa")
    tick()
    check("Ghost documents taken (X16): the Ghost task is over, nothing is given", none(GHOST, (1,)))
    reset("coop_l08_yantar")
    give("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO")
    give("YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO")
    a = player(1, "qaa")
    tick()
    check("Yantar main chain done (fallback): the Ghost task is over", none(GHOST, (1,)))

    # ---- a tick on another VM generation does not double give
    reset()
    give("AGR_STALKER_HELP_1_INFO")
    a = player(1, "qaa")
    st["env"].install()
    tick()
    check("two installs in a row: the old tick retires, the task is given once", all_once(MAIN, (1,)))

    print("%d checks, %d failed" % (n_checks, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
