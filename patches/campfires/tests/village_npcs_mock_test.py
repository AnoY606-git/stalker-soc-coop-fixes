"""Offline check (no game) of the in-game hook village_npcs.lua: runs the REAL hook in a Lua 5.1 VM with a mock of the alife/db/qa API and four
NPCs: one seated, one walking normally, one walking in place (stuck), two standing on top of each other. Expected: exactly the stuck and the overlap
asserts fail, the job assert fails for the NPC without a job."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "village_npcs.lua"), "rb").read().decode()

PRELUDE = r'''
local src = ...
local E = { math = math, string = string, table = table, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber, tostring = tostring, print = print,
	type = type, select = select, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.move = { stand = 0, walk = 1 }
E.qa = { cfg = {}, hooks = {}, results = {}, events = {} }
function E.qa.assert(name, ok, detail) E.qa.results[#E.qa.results + 1] = { name = name, ok = ok and true or false, detail = detail } end
function E.qa.event(t) E.qa.events[#E.qa.events + 1] = t end
function E.OnServer() return true end
E.level = { name = function() return "coop_l01_escape" end, object_by_id = function(id) return E.__objs[id] end,
	vertex_position = function(v) return { x = v, y = 0, z = (v == -206.0) and -138.0 or -157.0 } end }
E.vector = function() local v = {}; function v:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end; return v end
E.__objs, E.__ses, E.__info, E.__jobs, E.db = {}, {}, {}, {}, { mp_actors = {}, storage = {} }
E.alife = function() return { object = function(_, k)
	if k == "esc_smart_terrain_1" then return { npc_info = E.__info, job_data = E.__jobs } end
	return E.__ses[k] end } end
function E.__npc(id, name, job, x, z, mv, kamp)
	E.__ses[id] = { name = function() return name end, alive = function() return true end, position = { x = x, y = 0, z = z } }
	E.__info[id] = { job_id = job and id or nil }
	if job then E.__jobs[id] = { section = job } end
	E.__objs[id] = { position = function() return { x = E.__ses[id].position.x, y = 0, z = E.__ses[id].position.z } end,
		target_movement_type = function() return mv and 1 or 0 end }
	E.db.storage[id] = { active_section = "x@" .. name, kamp = kamp }
end
local fn = assert(loadstring(src)); setfenv(fn, E); fn()
function E.__set(id, x, z) E.__ses[id].position.x, E.__ses[id].position.z = x, z end
return E
'''

lua = lupa51.LuaRuntime()
E = lua.eval("function(s) return loadstring(s) end")(PRELUDE)(SRC)
E.__npc(1, "seated", "kamp_1", -206.0, -138.0, False, lua.table_from({"pos_vertex": -206.0}))
E.__npc(2, "walker", "guard_1", -200.0, -147.0, True, None)
E.__npc(3, "stuck", "kamp_7", -216.0, -148.0, True, lua.table_from({"pos_vertex": -234.0}))
E.__npc(4, "nojob", None, -190.0, -140.0, False, None)
E.__npc(5, "twin_a", "kamp_2", -205.0, -141.0, False, lua.table_from({"arrived": True}))
E.__npc(6, "twin_b", "kamp_3", -205.2, -141.1, False, lua.table_from({"arrived": True}))
hook = E.qa.hooks.village_npcs
t = 0
x2 = -200.0
for t in range(0, 175):
    E.__set(2, x2, -147.0)
    x2 += 1.0 if t % 20 else 1.0
    hook(t, None)
res = [(r["name"], r["ok"]) for r in E.qa.results.values()]
fails = sorted(n for n, ok in res if not ok)
print("\n".join(fails))
exp = ["village job w1 nojob", "village job w2 nojob", "village stuck w1 stuck", "village stuck w2 stuck", "village seat w1 stuck", "village seat w2 stuck",
       "village overlap w1 twin_a/twin_b", "village overlap w2 twin_a/twin_b"]
ok = fails == sorted(exp)
print("PASS" if ok else "FAIL expected %s" % sorted(exp))
print("asserts: %d, events: %d" % (len(res), len(E.qa.events)))
sys.exit(0 if ok else 1)
