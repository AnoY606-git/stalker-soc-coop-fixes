"""Offline check of patches/mutant_loot against a mock engine (no game, a second):  python mutant_loot_mock_test.py
Runs the REAL gamedata/scripts/mutant_loot.script in a Lua 5.1 VM (lupa) and plays the server and the client side:
death roll -> corpse binder arms the use callback -> use_cb (the function the engine calls on the SERVER with who = the player)
-> the part lands in that player's inventory, one part per corpse, repeat/double fire ignored, a second player gets nothing,
feedback flag -> tip on the right machine only, client fallback through the game_sv function.
Needs `pip install lupa` (the same package host_cfg_mock_test.py uses)."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(PATCH, "gamedata", "scripts", "mutant_loot.script")
LTX = os.path.join(PATCH, "gamedata", "configs", "misc", "mutant_loot.ltx")

LUA = r'''
local script_path, ltx_path = ...
local G = {}
for _, k in ipairs({ "string", "table", "math", "io", "os", "pairs", "ipairs", "pcall", "tonumber", "tostring", "type", "setmetatable",
	"getmetatable", "error", "select", "unpack", "next", "assert", "loadfile", "setfenv", "getfenv", "rawget", "rawset", "print", "xpcall" }) do G[k] = _G[k] end
G._G = G
local R = { results = {}, created = {}, tips = {} }

-- engine state
local S = { server = true, now = 100000, local_actor = 0 }
function G.OnServer() return S.server end
function G.OnClient() return not S.server end
function G.time_global() return S.now end
function G.LocalActor() return S.local_actor end
function G.getFS() return { update_path = function() return os.tmpname() end } end
G.callback = { use_object = 15 }
G.game = { translate_string = function(id)
	local t = { st_mutant_loot_found = "Found:", st_mutant_loot_empty = "Nothing useful on the body", mutant_dog_tail = "Dog Tail",
		mutant_flesh_eye = "Flesh Eye", st_tip = "Tip" }
	return t[id] or id
end }

-- vectors
local V = {}
V.__index = V
function V.new(x, y, z) return setmetatable({ x = x, y = y, z = z }, V) end
function V:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end

-- story flags (a flag given on the server is visible on every machine at once: the real game broadcasts it)
local flags = {}
G.story_flags = { story_flags = flags }
function G.story_flags.give_flag(n) flags[string.upper(n)] = true end
function G.story_flags.disable_flag(n) n = string.upper(n) if flags[n] then flags[n] = false end end

-- ltx
local function read_ltx(path)
	local secs, cur = {}, nil
	for line in io.lines(path) do
		line = line:gsub("\r", "")
		local sc = line:find(";", 1, true)
		if sc then line = line:sub(1, sc - 1) end
		line = line:match("^%s*(.-)%s*$")
		local s = line:match("^%[(.-)%]")
		if s then cur = {} secs[s] = cur
		elseif cur and line ~= "" then
			local k, v = line:match("^([^=]-)%s*=%s*(.*)$")
			if k then cur[k] = v end
		end
	end
	return secs
end
local ltx = read_ltx(ltx_path)
function G.ini_file(name)
	return {
		section_exist = function(self, s) return ltx[s] ~= nil end,
		line_exist = function(self, s, k) return ltx[s] ~= nil and ltx[s][k] ~= nil end,
		r_float = function(self, s, k) return tonumber(ltx[s][k]) end,
	}
end
local sysini = {
	dog_normal = { PartSpawnName = "mutant_dog_part" }, flesh_normal = { PartSpawnName = "mutant_flesh_part" }, poltergeist_normal = {},
	mutant_dog_part = { inv_name = "mutant_dog_tail" }, mutant_flesh_part = { inv_name = "mutant_flesh_eye" },
}
function G.system_ini()
	return {
		line_exist = function(self, s, k) return sysini[s] ~= nil and sysini[s][k] ~= nil end,
		r_string = function(self, s, k) return sysini[s][k] end,
	}
end

-- entities: server entities (alife) and live objects
local ents = {}
local live = {}
G.db = { mp_actors = {} }
G.level = { object_by_id = function(id) return live[id] end }
function G.alife()
	if not S.server then return nil end
	return {
		object = function(self, id) return ents[id] end,
		create = function(self, sec, pos, lv, gv, parent)
			R.created[#R.created + 1] = { section = sec, parent = parent }
			return {}
		end,
	}
end
local function add_actor(id, x)
	ents[id] = { position = V.new(x, 0, 0), m_level_vertex_id = 1, m_game_vertex_id = 1 }
	local o = { id = function() return id end, position = function() return ents[id].position end, name = function() return "player" .. id end }
	live[id] = o
	G.db.mp_actors[id] = o
	return o
end
local function add_mutant(id, section, x)
	ents[id] = { position = V.new(x, 0, 0), m_level_vertex_id = 1, m_game_vertex_id = 1 }
	local o = { dead = false, cb = nil, tip = nil }
	o.id = function() return id end
	o.section = function() return section end
	o.alive = function() return not o.dead end
	o.position = function() return ents[id].position end
	o.set_callback = function(self, t, fn, binder) o.cb = { t = t, fn = fn, binder = binder } end
	o.set_tip_text = function(self, s) o.tip = s end
	live[id] = o
	return o
end
G.getLocalActor = function() return live[S.local_actor] end

-- game_sv / game_cl
G.game_sv = {}
G.game_cl = { executeFunctionOnServer = function(fn)
	local was_server, was_local = S.server, S.local_actor
	S.server = true
	local f = G.game_sv[fn]
	R.last_exec = fn
	if f == nil then R.exec_missing = (R.exec_missing or 0) + 1 else f(was_local) end
	S.server = was_server
end }
G.news_manager = { send_tip = function(actor, text, a, sender, b, c)
	R.tips[#R.tips + 1] = { actor = actor:id(), text = text, sender = sender }
end }

-- luabind-like classes
function G.class(name)
	return function(base)
		local c = {}
		c.__index = c
		setmetatable(c, { __index = base, __call = function(cls, ...)
			local o = setmetatable({}, cls)
			if cls.__init then cls.__init(o, ...) end
			return o
		end })
		G[name] = c
		return c
	end
end
G.object_binder = { update = function() end }
G.super = function() end

-- load the real script as module "mutant_loot"
local env = setmetatable({}, { __index = G })
G.mutant_loot = env
local chunk = assert(loadfile(script_path))
setfenv(chunk, env)
chunk()

-- ---------------------------------------------------------------- scenario
local function check(name, cond, info) R.results[#R.results + 1] = { name, cond and true or false, tostring(info or "") } end
local ML = env
local function role(server, me) S.server = server S.local_actor = me or 0 end
local function count_parts(owner, sec)
	local n = 0
	for _, c in ipairs(R.created) do if c.parent == owner and (sec == nil or c.section == sec) then n = n + 1 end end
	return n
end
local function tips_for(actor) local t = {} for _, x in ipairs(R.tips) do if x.actor == actor then t[#t + 1] = x.text end end return t end

local P1, P2 = add_actor(1, 0), add_actor(2, 1)
local dog = add_mutant(100, "dog_normal", 2)
local flesh = add_mutant(101, "flesh_normal", 2)
local polt = add_mutant(102, "poltergeist_normal", 2)

-- default chance is the SoC 0.2
check("default chance is 0.2 for the dog part", math.abs(ML.chance_for("mutant_dog_part") - 0.2) < 1e-6, ML.chance_for("mutant_dog_part"))
ML.test.chance = 1.0

-- both machines: server binder = st_s, client binder of P1 = c1, client binder of P2 = c2
local st_s, st_s2, c1, c2 = {}, {}, {}, {}

role(true, 0)
check("alive mutant arms nothing", (function() ML.tick_dead(dog, st_s) return dog.cb == nil end)())
dog.dead = true
flesh.dead = true
polt.dead = true
check("death roll wins at chance 1", ML.on_death(dog, P1) == true)
check("flesh rolls too", ML.on_death(flesh, P1) == true)
check("poltergeist has no part (no roll)", ML.on_death(polt, P1) == false)
check("corpse flag exists", #ML.parts_on(100) == 1 and ML.parts_on(100)[1] == "mutant_dog_part")
check("game_sv fallback function registered", G.game_sv["mloot_take_100"] ~= nil)
ML.tick_dead(dog, st_s)
ML.tick_dead(flesh, st_s2)
check("server binder armed the use callback with the module function", dog.cb ~= nil and dog.cb.t == 15 and dog.cb.fn == ML.use_cb and dog.cb.binder == st_s)
check("tip text set", dog.tip == "st_mutant_loot_tip")
ML.tick_dead(polt, {})
check("poltergeist corpse is not armed", polt.cb == nil)

-- clients arm their copy and take the first feedback snapshot
local dog_c1, dog_c2 = add_mutant(900, "dog_normal", 2), nil
role(false, 1) ML.tick_dead(dog, c1)
role(false, 2) ML.tick_dead(dog, c2)
check("client binders armed the tip", ML.test.armed[100] == true)

-- P1 presses Use on the dog: the engine calls use_cb on the server with who = P1's actor
S.now = S.now + 5000
role(true, 0)
dog.cb.fn(dog.cb.binder, dog, P1)
check("P1 got exactly the dog part", count_parts(1, "mutant_dog_part") == 1 and #R.created == 1, #R.created)
check("corpse no longer offers the part (flag off)", #ML.parts_on(100) == 0)
check("use log has the server call", ML.test.uses[1] and ML.test.uses[1].server == true and ML.test.uses[1].who == 1)

-- the same player again after the repeat window: empty, no second part
S.now = S.now + 2000
dog.cb.fn(dog.cb.binder, dog, P1)
check("second use gives nothing", #R.created == 1)

-- P2 on the same corpse: nothing
S.now = S.now + 2000
dog.cb.fn(dog.cb.binder, dog, P2)
check("P2 gets nothing from the emptied corpse", count_parts(2) == 0 and #R.created == 1)

-- clients see feedback: only their own, after the poll interval, in order
S.now = S.now + 1000
role(true, 0)
-- (the sequence above happened within one poll; replay it with polls in between to check the tips)
local d2 = add_mutant(110, "dog_normal", 2)
d2.dead = true
ML.on_death(d2, P1)
local c1b = {}
role(false, 1) ML.tick_dead(d2, c1b)
role(false, 2) local c2b = {} ML.tick_dead(d2, c2b)
S.now = S.now + 5000
role(true, 0) d2.cb = nil ML.tick_dead(d2, st_s)
d2.cb.fn(d2.cb.binder, d2, P1)
S.now = S.now + 400
role(false, 1) ML.tick_dead(d2, c1b)
role(false, 2) ML.tick_dead(d2, c2b)
check("P1 client shows Found: Dog Tail", #tips_for(1) >= 1 and tips_for(1)[#tips_for(1)] == "Found: Dog Tail", table.concat(tips_for(1), " | "))
check("P2 client shows nothing for P1's find", #tips_for(2) == 0, table.concat(tips_for(2), " | "))
check("tip uses the mutant_hunter icon", R.tips[#R.tips].sender == "mutant_hunter")
local nt = #R.tips
S.now = S.now + 4000
role(true, 0) d2.cb.fn(d2.cb.binder, d2, P1)           -- P1 again: empty
S.now = S.now + 400
role(false, 1) ML.tick_dead(d2, c1b)
check("P1 second press: Nothing useful", #R.tips == nt + 1 and tips_for(1)[#tips_for(1)] == "Nothing useful on the body", table.concat(tips_for(1), " | "))
S.now = S.now + 2000
role(true, 0) d2.cb.fn(d2.cb.binder, d2, P2)           -- P2 on the emptied corpse
S.now = S.now + 400
role(false, 2) ML.tick_dead(d2, c2b)
check("P2 press on the emptied corpse: Nothing useful on P2's machine", #tips_for(2) == 1 and tips_for(2)[1] == "Nothing useful on the body", table.concat(tips_for(2), " | "))
S.now = S.now + 400
role(false, 1) ML.tick_dead(d2, c1b)
role(false, 2) ML.tick_dead(d2, c2b)
check("no tip is repeated", #R.tips == nt + 2, #R.tips)

-- double fire, client callback first: the client asks the server (game_sv function), the server callback of the same press is ignored
S.now = S.now + 5000
role(false, 1) local c1f = {} ML.tick_dead(flesh, c1f)
S.now = S.now + 400
local n0 = #R.created
local tips0 = #tips_for(1)
role(false, 1) ML.use_cb(c1f, flesh, P1)
check("client fallback used the game_sv function", R.last_exec == "mloot_take_101", R.last_exec)
role(true, 0) flesh.cb.fn(flesh.cb.binder, flesh, P1)                  -- the server callback of the same press
check("double fire gives one flesh part", count_parts(1, "mutant_flesh_part") == 1 and #R.created == n0 + 1, #R.created)
S.now = S.now + 400
role(false, 1) ML.tick_dead(flesh, c1f)
check("double fire shows one tip", #tips_for(1) == tips0 + 1 and tips_for(1)[#tips_for(1)] == "Found: Flesh Eye", table.concat(tips_for(1), " | "))
check("a client never creates items itself", count_parts(1) == #R.created and #R.created == 3, #R.created)
-- client callback on an emptied corpse asks for nothing
local exec0 = R.last_exec
R.last_exec = nil
role(false, 1) ML.use_cb(c1f, flesh, P1)
check("client callback on an empty corpse sends no request", R.last_exec == nil)

-- far away player: refused, the part stays
local far = add_mutant(103, "dog_normal", 2)
far.dead = true
role(true, 0) ML.on_death(far, P1)
ents[2].position = V.new(50, 0, 0)
S.now = S.now + 5000
ML.use_server(2, 103)
check("far player gets nothing and the part stays", count_parts(2) == 0 and #ML.parts_on(103) == 1)
ents[2].position = V.new(1, 0, 0)

-- a non-player user is ignored
G.db.mp_actors[77] = nil
ents[77] = { position = V.new(2, 0, 0), m_level_vertex_id = 1, m_game_vertex_id = 1 }
local npc = { id = function() return 77 end }
S.now = S.now + 5000
ML.use_cb(st_s, far, npc)
check("an NPC cannot take the part", #ML.parts_on(103) == 1)

-- race: two players use a fresh corpse in the same tick: exactly one part
local race = add_mutant(104, "flesh_normal", 2)
race.dead = true
ML.on_death(race, P1)
S.now = S.now + 5000
local n1 = #R.created
ML.use_server(1, 104)
ML.use_server(2, 104)
check("race: exactly one part", #R.created == n1 + 1 and #ML.parts_on(104) == 0)

-- a corpse id that spawns alive again drops old flags
ML.on_alive_spawn(103)
check("alive spawn clears the old corpse flag", #ML.parts_on(103) == 0)

-- feedback flags of an old game are swept on the first notify of a new server session
return R
'''


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    fn = lua.eval("function(src, a, b) return loadstring(src)(a, b) end")
    res = fn(LUA, SCRIPT, LTX)
    bad = 0
    n = 0
    for i in range(1, len(res.results) + 1):
        row = res.results[i]
        name, ok, info = row[1], row[2], row[3]
        n += 1
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else "   [" + str(info) + "]"))
        if not ok:
            bad += 1
    print("%d checks, %d failed" % (n, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
