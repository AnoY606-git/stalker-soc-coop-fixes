"""Offline check (no game) of the kamp seats: runs the REAL scripts\\xr_kamp.script in a Lua 5.1 VM (pip install lupa) against the REAL Cordon
AI mesh (level.ai) with stalkers that walk to their seat and are blocked by a stool and by the barrel, like in the game.

  python kamp_seat_mock_test.py --ai-root <dir> [--old xr_kamp_v1.4.script.txt] [--runs 300] [--all-camps]
  (level.ai files are extracted from the mod archive into <dir>\gamedata.db0\levels\<level> when missing; --all-camps = every fire of the merged configs)

What is simulated: 3 stalkers of squad 1 spawned on top of each other at the stool (the squad spawn point of the village), 2 stalkers at the
second fire; each runs the real go_position action + on_position evaluator every 100 ms of game time and walks 1.5 m/s towards the seat node.
A stalker cannot enter a disc around the stool (0.45 m + 0.3 m body) or the barrel (0.6 m + 0.3 m): he is pushed out to the rim and slides along it. The stalker is "seated" when the real
evaluator says so. Checks per run: every stalker seated within 90 s; no two seated stalkers closer than 0.5 m; nobody inside an obstacle.
With --old the same runs are made with the v1.4 script (seat = exact AI node only): that is the bug (expected to fail in a share of the runs).
"""
import argparse
import math
import os
import struct
import sys

import numpy as np
import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PATCH, "..", "soc_levels", "tools"))
import xrspawn as X  # noqa: E402

sys.path.insert(0, os.path.join(PATCH, "tools"))
import camp_lib as C  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--ai-root", required=True, help="folder with gamedata.db0\levels\<level>\level.ai (missing ones are extracted from the mod archive)")
ap.add_argument("--old", default=None, help="the v1.4 xr_kamp.script to run the same scenes with (shows the bug)")
ap.add_argument("--runs", type=int, default=300)
ap.add_argument("--all-camps", action="store_true", help="also every fire of the campfires patch (kamp sections of the merged configs)")
args = ap.parse_args()
NEW = os.path.join(PATCH, "gamedata", "scripts", "xr_kamp.script")

_ai = {}


def get_ai(level):
    if level not in _ai:
        _ai[level] = X.LevelAI(C.ensure_ai(level, args.ai_root))
    return _ai[level]

SCENES = {
    # name: centre, radius, spawn point, npc count, obstacles (x, z, collision radius), avoid (new script, from the ltx)
    "village fire (3 stalkers, squad 1 spawns on the stool)": dict(
        level="coop_l01_escape", centre=(-206.90, -19.61, -140.08), radius=2.4, spawn=(-206.8, -19.9, -138.6), n=3,
        obstacles=[(-207.22, -138.52, 0.45), (-206.90, -140.08, 0.60)], avoid="-207.22, -19.93, -138.52, 1.0"),
    "second fire (2 stalkers, ring half inside a building)": dict(
        level="coop_l01_escape", centre=(-234.92, -19.36, -156.80), radius=2.2, spawn=(-216.0, -20.4, -147.5), n=2,
        obstacles=[(-234.92, -156.80, 0.60)], avoid=None),
    "village fire, unknown obstacles on 3 ring spots (not in avoid)": dict(
        level="coop_l01_escape", centre=(-206.90, -19.61, -140.08), radius=2.4, spawn=(-206.8, -19.9, -138.6), n=3,
        obstacles=[(-204.5, -139.3, 0.9), (-206.5, -137.3, 0.9), (-208.8, -141.5, 0.9), (-206.90, -140.08, 0.60)], avoid=None),
}


def load_world(ai, centre, extent=40.0):
    sel = np.where((np.abs(ai.x - centre[0]) < extent) & (np.abs(ai.z - centre[2]) < extent))[0]
    return ([(int(n), float(ai.x[n]), float(ai.y[n]), float(ai.z[n]), int(ai.xi[n]), int(ai.zi[n])) for n in sel])


PRELUDE = r'''
local script_path, nodes_tbl, cfg = ...
local E = { string = string, table = table, math = math, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select,
	unpack = unpack, next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.this = E
E.__time = 0
function E.time_global() return E.__time end
function E.abort(fmt, ...) error(string.format(fmt, ...)) end
function E.printf(...) end
E.super = function() end
E.action_base = { initialize = function() end, execute = function() end, finalize = function() end }
E.property_evaluator = {}
function E.class(name)
	local C = {}
	C.__index = C
	local mt = { __call = function(cls, ...)
		local o = setmetatable({}, cls)
		if cls.__init then cls.__init(o, ...) end
		return o
	end }
	setmetatable(C, mt)
	E[name] = C
	return function(base)
		mt.__index = base
		return C
	end
end
-- vector
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function V:sub(a, b) self.x, self.y, self.z = a.x - b.x, a.y - b.y, a.z - b.z; return self end
function V:magnitude() return math.sqrt(self.x ^ 2 + self.y ^ 2 + self.z ^ 2) end
function V:normalize() local m = self:magnitude(); if m > 0 then self.x, self.y, self.z = self.x / m, self.y / m, self.z / m end; return self end
function V:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
-- level / AI map
local NO = 4294967295
local grid, N = {}, {}
for i = 1, #nodes_tbl do
	local n = nodes_tbl[i]
	N[n[1]] = n
	local k = n[5] .. "," .. n[6]
	grid[k] = grid[k] or {}
	table.insert(grid[k], n[1])
end
local BX, BZ, CELL = cfg.bx, cfg.bz, cfg.cell
local function cell_of(x, z) return math.floor((x - BX) / CELL + 0.5), math.floor((z - BZ) / CELL + 0.5) end
E.level = {
	vertex_id = function(p)
		local ix, iz = cell_of(p.x, p.z)
		local best, bd
		for _, id in ipairs(grid[ix .. "," .. iz] or {}) do
			local d = math.abs(N[id][3] - p.y)
			if bd == nil or d < bd then best, bd = id, d end
		end
		return best or NO
	end,
	vertex_position = function(id) local n = N[id]; return E.vector():set(n[2], n[3], n[4]) end,
}
E.game_object = { level_path = 1 }
E.xr_logic = { assign_storage_and_bind = function() return {} end, cfg_get_switch_conditions = function() return {} end,
	is_active = function() return true end }
E.utils = {
	cfg_get_string = function(ini, s, f, npc, m, g, d) local v = ini[s] and ini[s][f]; if v == nil then return d end return v end,
	cfg_get_number = function(ini, s, f, npc, m, g, d) local v = ini[s] and tonumber(ini[s][f]); if v == nil then return d end return v end,
	cfg_get_bool = function(ini, s, f, npc, m, g, d) local v = ini[s] and ini[s][f]; if v == nil then return d end return v == "true" end,
}
E.state_mgr = { set_state = function(npc, st) npc.__state = st end }
E.sr_camp = { get_current_camp = function() return nil end }
E.xr_animpoint_predicates = {}
E.stalker_ids = {}
E.xr_motivator = { addCommonPrecondition = function() end }

local src = io.open(script_path, "rb"):read("*a")
local fn = assert(loadstring(src, "xr_kamp"))
setfenv(fn, E)
fn()

-- ---------------------------------------------------------------- simulation
local function make_npc(id, x, y, z)
	local o = { __id = id, __x = x, __y = y, __z = z, __dest = nil }
	function o:id() return self.__id end
	function o:position() return E.vector():set(self.__x, self.__y, self.__z) end
	function o:level_vertex_id() return E.level.vertex_id(self:position()) end
	function o:accessible() return true end
	function o:accessible_nearest(p) return E.level.vertex_id(p) end
	function o:set_dest_level_vertex_id(v) self.__dest = v end
	function o:set_path_type() end
	function o:set_desired_position() end
	function o:set_desired_direction() end
	function o:name() return "npc" .. self.__id end
	return o
end

-- returns the list of final states
function E.run(seed, scene)
	E.math.randomseed(seed)
	E.kamps = nil
	E.__time = 0
	-- fresh state of the script
	fn = assert(loadstring(src, "xr_kamp")); setfenv(fn, E); fn()
	local ini = { kamp = { center_pos = scene.cpos, radius = tostring(scene.radius), use_camp = "false", def_state_moving = "walk", avoid = scene.avoid } }
	local npcs = {}
	for i = 1, scene.n do
		local o = make_npc(100 + i, scene.sx, scene.sy, scene.sz)
		local st = {}
		E.xr_logic.assign_storage_and_bind = function() return st end
		E.set_scheme(o, ini, "kamp", "kamp", "smart")
		o.__st = st
		o.__ev = E.evaluator_on_position("p", st); o.__ev.object = o
		o.__act = E.action_go_position(o, "go", st); o.__act.object = o
		o.__started = false
		npcs[i] = o
	end
	local step, speed = 100, 1.5
	local seat_time = {}
	for t = 0, scene.max_ms, step do
		E.__time = E.__time + step
		for _, o in ipairs(npcs) do
			if o.__ev:evaluate() then
				if seat_time[o] == nil then seat_time[o] = E.__time end
				o.__dest = nil
			else
				if not o.__started then o.__act:initialize(); o.__started = true end
				o.__act:execute()
				if o.__dest ~= nil and o.__dest ~= NO then
					local n = N[o.__dest]
					local dx, dz = n[2] - o.__x, n[4] - o.__z
					local d = math.sqrt(dx * dx + dz * dz)
					if d > 0.01 then
						local m = math.min(d, speed * step / 1000)
						local nx, nz = o.__x + dx / d * m, o.__z + dz / d * m
						-- solid obstacles: a body that would end inside the disc is pushed out to its rim (sliding along it)
						for _, ob in ipairs(scene.obstacles) do
							local ex, ez = nx - ob[1], nz - ob[2]
							local od = math.sqrt(ex * ex + ez * ez)
							local rim = ob[3] + 0.3
							if od < rim then
								if od < 0.001 then ex, ez, od = 1, 0, 1 end
								nx, nz = ob[1] + ex / od * rim, ob[2] + ez / od * rim
							end
						end
						o.__x, o.__z = nx, nz
					end
				end
			end
		end
	end
	local out = {}
	for i, o in ipairs(npcs) do
		out[i] = { x = o.__x, z = o.__z, seated = o.__ev:evaluate(), t = seat_time[o] or -1 }
	end
	return out
end
return E
'''


def run_script(path, scene, runs):
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    ai = get_ai(scene["level"])
    nodes = load_world(ai, scene["centre"])
    tbl = lua.table_from([lua.table_from(list(n)) for n in nodes])
    cfg = lua.table_from({"bx": float(ai.bb[0]), "bz": float(ai.bb[2]), "cell": float(ai.size)})
    chunk = lua.eval("function(src) return loadstring(src) end")(PRELUDE)
    E = chunk(path, tbl, cfg)
    sc = lua.table_from({
        "cpos": "%.2f, %.2f, %.2f" % scene["centre"], "radius": scene["radius"], "sx": scene["spawn"][0], "sy": scene["spawn"][1],
        "sz": scene["spawn"][2], "n": scene["n"], "max_ms": 90000,
        "obstacles": lua.table_from([lua.table_from(list(o)) for o in scene["obstacles"]]),
        "avoid": scene["avoid"],
    })
    res = []
    for seed in range(1, runs + 1):
        out = E.run(seed, sc)
        res.append([(out[i]["x"], out[i]["z"], bool(out[i]["seated"]), out[i]["t"]) for i in range(1, scene["n"] + 1)])
    return res


def judge(res, scene):
    bad_unseated = bad_close = bad_inside = 0
    for r in res:
        if any(not s for _, _, s, _ in r):
            bad_unseated += 1
        pts = [(x, z) for x, z, s, _ in r]
        if any(math.dist(pts[i], pts[j]) < 0.5 for i in range(len(pts)) for j in range(i + 1, len(pts))):
            bad_close += 1
        for x, z in pts:
            if any(math.hypot(x - ox, z - oz) < rr for ox, oz, rr in scene["obstacles"]):
                bad_inside += 1
                break
    return bad_unseated, bad_close, bad_inside


def camp_scenes():
    """one scene per fire of the merged configs: n stalkers (one per job) spawned stacked 8 m from the fire, barrel and stools solid."""
    furn = [(n, p) for n, p, kind in C.covers() if kind in ("animpoint_sit_normal", "animpoint_sit_high")]
    out = {}
    for camp in C.camps():
        ai = get_ai(camp["level"])
        cx, cy, cz = camp["centre"]
        sel = np.where((np.abs(ai.x - cx) < 12) & (np.abs(ai.z - cz) < 12) & (np.abs(ai.y - cy) < 2.0))[0]
        best = None
        for n in sel:
            d = math.hypot(ai.x[n] - cx, ai.z[n] - cz)
            if 7.5 <= d <= 8.5 and (best is None or abs(ai.y[n] - cy) < abs(ai.y[best] - cy)):
                best = n
        if best is None:
            continue
        prefix = C.LEVEL_PREFIX[camp["level"]] + "_"
        obst = [(cx, cz, 0.6)] + [(p[0], p[2], 0.45) for n, p in furn if n.startswith(prefix) and math.hypot(p[0] - cx, p[2] - cz) < camp["radius"] + 2.0]
        avoid = " | ".join("%.2f, %.2f, %.2f, %.2f" % a for a in camp["avoid"]) or None
        out["%s fire %.0f,%.0f (%d jobs, r %.1f)" % (camp["level"][-8:], cx, cz, len(camp["jobs"]), camp["radius"])] = dict(
            level=camp["level"], centre=camp["centre"], radius=camp["radius"], spawn=(float(ai.x[best]), float(ai.y[best]), float(ai.z[best])),
            n=len(camp["jobs"]), obstacles=obst, avoid=avoid)
    return out


scenes = dict(SCENES)
if args.all_camps:
    scenes = camp_scenes()
    scenes.update(SCENES)
fails = 0
for label, path in (("v1.4 script", args.old), ("new script", NEW)):
    if path is None:
        continue
    print("== " + label)
    for name, sc in scenes.items():
        scene = dict(sc)
        if label == "v1.4 script":
            scene["avoid"] = None
        res = run_script(path, scene, args.runs)
        u, c, i = judge(res, sc)
        times = sorted(t for r in res for _, _, s, t in r if s and t >= 0)
        med = times[len(times) // 2] / 1000 if times else -1
        print("  %-62s never seated: %3d/%d | two closer than 0.5 m: %3d | inside an obstacle: %3d | median seat time %.1f s"
              % (name, u, args.runs, c, i, med))
        if label == "new script" and (u or c or i):
            fails += 1
print("FAIL" if fails else "PASS")
sys.exit(1 if fails else 0)
