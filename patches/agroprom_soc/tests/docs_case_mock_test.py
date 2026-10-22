"""Offline check (no game) of the documents case in coop_scn_agroprom_soc.script (1.4.3 fix: two cases with two players).
usage: python docs_case_mock_test.py     (needs `pip install lupa`)
Runs the REAL script with an engine mock (alife objects, patrol, inventories) and proves:
  * the case is spawned by the server once, on Agroprom, after the first player arrived, however many ticks run
  * no spawn before a player arrived, none on another level, none when the flag of an earlier spawn is in the save
  * extra cases of old saves are released: two in one inventory, one in the inventory and one on the table, one per player;
    before the hand-in the carried case is kept, after it the Barkeep's
"""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "gamedata", "scripts", "coop_scn_agroprom_soc.script"))
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
local E = { string = string, table = table, math = math, io = io, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, error = error, select = select, unpack = unpack, next = next,
	assert = assert, rawget = rawget, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__time = 0
E.__calls = {}
function E.printf_msg() end
function E.time_global() return E.__time end
function E.OnServer() return true end
function E.IsActorNetReady() return true end
function E.GiveTaskToClient() end
local V = {} V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z return self end
function V:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[n] == true end, give_flag = function(n) flags[n] = true end }
E.__flags = flags
E.__level = "coop_l03_agroprom"
E.level = { name = function() return E.__level end, add_call = function(f) E.__calls[#E.__calls + 1] = f end }
-- alife: objects by id; an item's parent_id is 65535 on the ground
local objs = {}
local next_id = 1000
E.__objs = objs
E.__created = 0
local function new_se(section, parent)
	next_id = next_id + 1
	local se = { id = next_id, parent_id = parent or 65535, __section = section }
	function se:section_name() return self.__section end
	objs[se.id] = se
	return se
end
E.__new_se = new_se
E.alife = function() return {
	object = function(self, id) return objs[id] end,
	release = function(self, se) objs[se.id] = nil end,
	create = function(self, section, pos, lv, gv) E.__created = E.__created + 1 return new_se(section) end,
} end
E.patrol = function(name) return { point = function() return E.vector() end, level_vertex_id = function() return 1 end, game_vertex_id = function() return 1 end } end
E.db = { mp_actors = {} }
function E.__player(pid, oid)
	local o = { __id = oid, __alive = true, __pos = E.vector():set(500, 0, 500) }
	function o:id() return self.__id end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec)
		for _, se in pairs(objs) do if se.parent_id == self.__id and se.__section == sec then return se end end
		return nil
	end
	function o:iterate_inventory(fn, obj)
		local ids = {}
		for id, se in pairs(objs) do if se.parent_id == self.__id then ids[#ids + 1] = id end end
		table.sort(ids)
		for _, id in ipairs(ids) do
			local se = objs[id]
			fn(obj, { section = function() return se.__section end, id = function() return se.id end })
		end
	end
	E.db.mp_actors[pid] = o
	return o
end
function E.__count(section, parent)
	local n = 0
	for _, se in pairs(objs) do if se.__section == section and (parent == nil or se.parent_id == parent) then n = n + 1 end end
	return n
end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_scn_agroprom_soc"))
setfenv(fn, env)
fn()
return E
'''

CASE = "agr_safe_container_1"


def fresh():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    E = lua.execute(PRELUDE, SCRIPT)
    return lua, E


def run(E, seconds):
    for _ in range(int(seconds)):
        E.__time = E.__time + 1000
        for i in range(1, len(E.__calls) + 1):
            E.__calls[i]()


# 1. one spawn, server side, once
lua, E = fresh()
E.__player(1, 1)
E.__player(2, 2)
run(E, 5)
check("no player arrived yet: no case", E.__created == 0, E.__created)
E.__flags["AGR_STALKER_HELP_1_INFO"] = True
run(E, 30)
check("first player on Agroprom: the case is spawned once (two players, 30 ticks)", E.__created == 1 and E.__count(CASE) == 1, E.__created)
check("the spawn flag is set", E.__flags["AGR_SOC_DOCS_SPAWNED"] is True)

lua, E = fresh()
E.__player(1, 1)
E.__level = "coop_l02_garbage"
E.__flags["AGR_STALKER_HELP_1_INFO"] = True
run(E, 15)
check("other level: no case", E.__created == 0)

lua, E = fresh()
E.__player(1, 1)
E.__flags["AGR_STALKER_HELP_1_INFO"] = True
E.__flags["AGR_SOC_DOCS_SPAWNED"] = True
E.__new_se(CASE)
run(E, 15)
check("save with the case already spawned: nothing new", E.__created == 0 and E.__count(CASE) == 1)

lua, E = fresh()
E.__player(1, 1)
E.__flags["AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO"] = True
run(E, 5)
check("fallback: back from the underground also spawns it, once", E.__created == 1)

# 2. old saves with two cases
lua, E = fresh()
E.__player(1, 1)
E.__player(2, 2)
E.__flags["AGR_SOC_DOCS_SPAWNED"] = True
E.__new_se(CASE, 1)
E.__new_se(CASE, 1)
run(E, 3)
check("two cases in one inventory: one is released", E.__count(CASE) == 1 and E.__count(CASE, 1) == 1, E.__count(CASE))
check("the documents flag is set", E.__flags["AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"] is True)

lua, E = fresh()
E.__player(1, 1)
E.__flags["AGR_SOC_DOCS_SPAWNED"] = True
E.__new_se(CASE)        # still on the table
E.__new_se(CASE, 1)     # picked up
run(E, 15)
check("one carried, one on the table: the table one is released", E.__count(CASE) == 1 and E.__count(CASE, 1) == 1)

lua, E = fresh()
E.__player(1, 1)
E.__player(2, 2)
E.__flags["AGR_SOC_DOCS_SPAWNED"] = True
E.__new_se(CASE, 1)
E.__new_se(CASE, 2)
run(E, 15)
check("one case per player: one is released", E.__count(CASE) == 1)

lua, E = fresh()
E.__player(1, 1)
E.__flags["AGR_SOC_DOCS_SPAWNED"] = True
E.__flags["AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"] = True
E.__flags["BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO"] = True
E.__new_se(CASE, 777)   # the Barkeep's
E.__new_se(CASE, 1)     # the extra one a player kept
E.__level = "coop_l05_bar"
run(E, 15)
check("after the hand-in: the Barkeep's case is kept, the player's extra one released", E.__count(CASE) == 1 and E.__count(CASE, 777) == 1)

lua, E = fresh()
E.__player(1, 1)
E.__flags["AGR_SOC_DOCS_SPAWNED"] = True
E.__new_se(CASE, 1)
run(E, 30)
check("a single case is never touched", E.__count(CASE) == 1 and E.__count(CASE, 1) == 1)

print("%d checks, %d failed" % (n_checks, fails))
sys.exit(1 if fails else 0)
