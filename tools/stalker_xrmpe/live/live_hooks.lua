-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): LIVE console for a running Shadow of COOP session.  Loaded with run_coop-style -Hooks (start_live.ps1
-- appends it after qa_harness.lua to the shipped scripts of the lane addon).  Runs on EVERY role (dedicated server S, clients A, B ...).
--
-- Protocol (all files in this role's $logs$ folder, written by lua.ps1):
--   live_cmd_<n>.lua   Lua chunk number n (n = 1, 2, 3 ...; lua.ps1 renames a .tmp into place so a half-written file is never read)
--   live_res_<n>.txt   result: first line "OK <ms>" or "ERR <ms>", then printed output, return values, error text, last line "--END--"
--   live_ready.txt     written once this role is polling ("role level time")
-- The chunk is first tried as an expression ("return <chunk>"), then as statements.  Globals you set persist between commands
-- (one shared environment per role).  Polling is every 250 ms.
--
-- Helpers (table `live`): find, near, count, tp, face, spawn, hit, kill, shot, inv, players, reload, save, state, defer, dump
-- See live\README.md.  Do not call OnServer()/getFS() at file top level: this file runs at script load.
-------------------------------------------------------------------------------------------------------
if not _G.live then
_G.live = { seq = 0, last = 0, out = nil, tasks = {}, shots = 0 }
local live = _G.live
if _G.qa then _G.qa.last_snap = 1e15 end   -- the 5 s object-scan snapshot of the QA harness only costs frame time in a live session

local function logpath(name) return getFS():update_path("$logs$", name) end
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function is_server() return safe(OnServer) == true end

-- ---------- value formatting --------------------------------------------------------------------------------------------
local function f1(n) return string.format("%.1f", n) end
local function vstr(p) return "(" .. f1(p.x) .. ", " .. f1(p.y) .. ", " .. f1(p.z) .. ")" end

function live.dump(v, depth, seen)
	depth = depth or 3
	local tv = type(v)
	if tv == "table" then
		if depth <= 0 then return "{...}" end
		local mt = getmetatable(v)
		if mt and mt.__tostring then return tostring(v) end
		local parts, n = {}, 0
		for k, x in pairs(v) do
			n = n + 1
			if n > 40 then parts[#parts + 1] = "..." break end
			parts[#parts + 1] = (type(k) == "number" and "" or (tostring(k) .. "=")) .. live.dump(x, depth - 1)
		end
		return "{" .. table.concat(parts, ", ") .. "}"
	elseif tv == "string" then
		return v
	elseif tv == "userdata" then
		local ok, x, y, z = pcall(function() return v.x, v.y, v.z end)
		if ok and type(x) == "number" and type(z) == "number" then return vstr(v) end
		local ok2, nm = pcall(function() return v:name() end)
		if ok2 and nm then
			local ok3, sec = pcall(function() return v:section() end)
			if not ok3 then ok3, sec = pcall(function() return v:section_name() end) end
			return "<" .. tostring(nm) .. (ok3 and (" " .. tostring(sec)) or "") .. " id=" .. tostring(safe(function() return v:id() end) or safe(function() return v.id end)) .. ">"
		end
		return tostring(v)
	end
	return tostring(v)
end

-- a list of records prints as lines (with a header count)
local list_mt = { __tostring = function(t)
	local out = { string.format("[%d result(s)] (snapshot at game time %ds; NPCs walk, so two calls can differ)", #t, math.floor((safe(time_global) or 0) / 1000)) }
	for i = 1, math.min(#t, 60) do out[#out + 1] = t[i].line or live.dump(t[i], 2) end
	if #t > 60 then out[#out + 1] = "... " .. (#t - 60) .. " more" end
	return table.concat(out, "\n")
end, __len = nil }
local function newlist() return setmetatable({}, list_mt) end

-- ---------- players ----------------------------------------------------------------------------------------------------
function live.players()
	local res = {}
	if type(db.mp_actors) == "table" then
		for id, o in pairs(db.mp_actors) do
			if o ~= nil then res[#res + 1] = { id = id, obj = o, name = safe(function() return o:name() end), alive = safe(function() return o:alive() end) } end
		end
	end
	if #res == 0 then
		local me = safe(LocalActor)
		local o = me and safe(level.object_by_id, me)
		if o then res[1] = { id = me, obj = o, name = safe(function() return o:name() end), alive = safe(function() return o:alive() end) } end
	end
	table.sort(res, function(a, b) return a.id < b.id end)
	return res
end

-- The harness players are named qaA, qaB ... A LOADED save also brings back the saved actor ("ghost", the story character standing in the
-- world) while the real harness player spawns in the lobby box (105, -15.8, -10), where set_actor_position does not move it.
-- "me" / first_player() is therefore the alive player that is NOT in the lobby box (prefer harness-named), else any alive player.
local LOBBY = { x = 105, y = -15.8, z = -10 }
local function in_lobby(p)
	local ok, d = pcall(function() local q = p.obj:position() return math.sqrt((q.x - LOBBY.x) ^ 2 + (q.z - LOBBY.z) ^ 2) end)
	return ok and d < 30
end
local function is_real(p) return p.name ~= nil and string.find(string.lower(tostring(p.name)), "^qa[a-d]$") ~= nil end
local function first_player()
	local ps = live.players()
	for _, p in ipairs(ps) do if p.alive and is_real(p) and not in_lobby(p) then return p end end
	for _, p in ipairs(ps) do if p.alive and not in_lobby(p) then return p end end
	for _, p in ipairs(ps) do if p.alive then return p end end
	return ps[1]
end
live.first_player = first_player

-- resolve a position: vector / {x,y,z} / {x=,y=,z=} / game_object / object id / player name / "me" (first player)
local function resolve_pos(p)
	if p == nil or p == "me" or p == "player" then
		local pl = first_player()
		if not pl then error("no player to take a position from") end
		return pl.obj:position()
	end
	local tp = type(p)
	if tp == "table" then
		local x, y, z = p.x or p[1], p.y or p[2], p.z or p[3]
		return vector():set(x, y, z)
	elseif tp == "number" then
		local o = safe(level.object_by_id, p)
		if o then return o:position() end
		local se = safe(function() return alife():object(p) end)
		if se then return se.position end
		error("no object with id " .. p)
	elseif tp == "string" then
		for _, pl in ipairs(live.players()) do if string.lower(tostring(pl.name)) == string.lower(p) then return pl.obj:position() end end
		error("unknown position/player '" .. p .. "'")
	end
	local ok, x = pcall(function() return p.x end)
	if ok and x then return p end
	local ok2, pos = pcall(function() return p:position() end)
	if ok2 and pos then return pos end
	error("cannot read a position from " .. tostring(p))
end
live.pos = resolve_pos

-- ---------- object scan --------------------------------------------------------------------------------------------------
-- Server (alife present): every server entity (online or offline).  Client: online objects only.
local function scan(fn)
	local sim = safe(alife)
	local n = 0
	local obj_by_id = level.object_by_id
	if sim ~= nil then
		for id = 0, 65534 do
			local se = sim:object(id)
			if se ~= nil then
				n = n + 1
				fn(id, se, obj_by_id(id))
			end
		end
	else
		for id = 0, 65534 do
			local o = obj_by_id(id)
			if o ~= nil then n = n + 1 fn(id, nil, o) end
		end
	end
	return n
end

local function rec(id, se, o, from)
	local r = { id = id, online = (o ~= nil) }
	r.section = (se and safe(function() return se:section_name() end)) or (o and safe(function() return o:section() end)) or "?"
	r.name = (se and safe(function() return se:name() end)) or (o and safe(function() return o:name() end)) or "?"
	r.pos = (se and se.position) or (o and o:position())
	if r.pos and from then r.dist = r.pos:distance_to(from) end
	local cid = safe(function() return (se or o):clsid() end)
	r.mutant = cid ~= nil and safe(IsMonster, nil, cid) == true
	r.actor = string.find(r.section, "^actor") ~= nil
	r.stalker = cid ~= nil and safe(IsStalker, nil, cid) == true and not r.actor
	r.creature = r.mutant or r.stalker or r.actor
	if r.creature then
		if o then r.alive = safe(function() return o:alive() end) else r.alive = safe(function() return se:alive() end) end
	end
	if o then
		r.cname = safe(function() return o:character_name() end)
		local st = db.storage and db.storage[id]
		if st then r.job = tostring(st.active_scheme) .. ":" .. tostring(st.active_section) end
	end
	r.npc = r.stalker
	r.line = string.format("#%-5s %-34s %-24s%s%s %s%s", tostring(id), tostring(r.name), tostring(r.section),
		r.dist and (" d=" .. f1(r.dist)) or "", r.online and " online" or " offline",
		r.pos and vstr(r.pos) or "", (r.alive == false and " DEAD" or "") .. (r.job and (" job=" .. r.job) or ""))
	return r
end

-- live.find("bandit")  -> every object whose name or section contains the text (plain, case-insensitive), nearest player first
function live.find(q, limit)
	q = string.lower(tostring(q))
	local from = safe(function() return resolve_pos("me") end)
	local res = newlist()
	scan(function(id, se, o)
		local nm = string.lower(tostring((se and safe(function() return se:name() end)) or (o and safe(function() return o:name() end)) or ""))
		local sc = string.lower(tostring((se and safe(function() return se:section_name() end)) or (o and safe(function() return o:section() end)) or ""))
		if string.find(nm, q, 1, true) or string.find(sc, q, 1, true) then res[#res + 1] = rec(id, se, o, from) end
	end)
	table.sort(res, function(a, b) return (a.dist or 1e9) < (b.dist or 1e9) end)
	if limit then for i = #res, limit + 1, -1 do res[i] = nil end end
	return res
end

-- live.near(pos, radius [, filter]) -> objects within radius metres of pos, sorted by distance. pos: see resolve_pos ("me" by default).
-- filter: "npc" (human NPCs), "alive", or a function(rec) -> bool.  Items carried by someone are skipped.
function live.near(pos, radius, filter)
	local p = resolve_pos(pos)
	radius = radius or 20
	local res = newlist()
	local sim = safe(alife)
	scan(function(id, se, o)
		local pid = (se and safe(function() return se.parent_id end)) or (o and safe(function() return o:parent() ~= nil and 1 or 65535 end)) or 65535
		if pid ~= 65535 and pid ~= nil then return end
		local pp = (se and se.position) or (o and o:position())
		if pp and pp:distance_to(p) <= radius then
			local r = rec(id, se, o, p)
			local keep = true
			if filter == "npc" or filter == "stalker" then keep = r.stalker and r.alive ~= false
			elseif filter == "mutant" then keep = r.mutant and r.alive ~= false
			elseif filter == "creature" then keep = r.creature and r.alive ~= false
			elseif filter == "alive" then keep = r.alive == true
			elseif type(filter) == "function" then keep = filter(r) end
			if keep then res[#res + 1] = r end
		end
	end)
	table.sort(res, function(a, b) return a.dist < b.dist end)
	return res
end

function live.count(pos, radius, filter) return #live.near(pos, radius, filter) end

-- live.census(pos, radius [, filter]) -> count AND list from ONE scan (separate live.count / live.near calls are different snapshots and can disagree)
function live.census(pos, radius, filter) return live.near(pos, radius, filter) end

-- ---------- actions --------------------------------------------------------------------------------------------------------
-- live.tp(x, y, z [, who])  who = player name / id (default: every alive player).  Server only (clients just print the error).
function live.tp(x, y, z, who)
	local p
	if type(x) == "table" or type(x) == "userdata" then who = y; p = resolve_pos(x) else p = vector():set(x, y, z) end
	local moved = {}
	local sv = is_server() and type(_G.teleport_actor_sv) == "function"
	for _, pl in ipairs(live.players()) do
		if pl.alive and (who == nil or who == pl.id or string.lower(tostring(pl.name)) == string.lower(tostring(who))) then
			-- set_actor_position on the server's proxy object does NOT move a client player (the answer used to say "moved" anyway).
			-- teleport_actor_sv is what the mod's own xrmpe_teleport_actors uses and it moves the real client actor.
			local dir = safe(function() return pl.obj:direction() end) or vector():set(0, 0, 1)
			if sv then pcall(_G.teleport_actor_sv, pl.id, p, dir) else pcall(function() pl.obj:set_actor_position(p) end) end
			moved[#moved + 1] = pl
		end
	end
	if #moved == 0 then return "no matching alive player: nothing moved" end
	-- do not claim success before the position really changed: wait (up to 10 s) until every player is within 3 m, else say what is wrong
	local c0 = os.clock()
	local method = sv and "teleport_actor_sv" or "set_actor_position"
	return live.async(function()
		local far, parts = 0, {}
		for _, pl in ipairs(moved) do
			local q = safe(function() return pl.obj:position() end)
			local d = q and q:distance_to(p) or 1e9
			if d > 3 then far = far + 1 end
			parts[#parts + 1] = string.format("%s now %s (%.1f m from target)", tostring(pl.name), q and vstr(q) or "?", d)
		end
		if far == 0 then return string.format("%d player(s) moved to %s via %s in %.1f s: %s", #moved, vstr(p), method, os.clock() - c0, table.concat(parts, "; ")) end
		if os.clock() - c0 < 10 then return nil end
		local scene = safe(function() return coop_scenes and coop_scenes.status and coop_scenes.status() end)
		return string.format("NOT MOVED: %d of %d player(s) still away from %s after 10 s via %s: %s.  %s", far, #moved, vstr(p), method, table.concat(parts, "; "),
			(scene and string.find(tostring(scene), "active=nil", 1, true) == nil)
				and ("A cutscene is probably running and puts players back (coop_scenes: " .. tostring(scene) .. "); wait for active=nil and retry.")
				or "No cutscene reported; the server-side position of a client that is still in the lobby is not updated: ask the client (-Role A) with db.actor:position().")
	end, 15)
end

function live.face(yaw_deg, who)
	local n = 0
	for _, pl in ipairs(live.players()) do
		if pl.alive and (who == nil or who == pl.id or string.lower(tostring(pl.name)) == string.lower(tostring(who))) then
			pl.obj:set_actor_direction(math.rad(yaw_deg))
			n = n + 1
		end
	end
	return n
end

-- live.spawn("section" [, pos]) -> server entity id.  Server (alife) only.  pos defaults to 4 m in front of the first player.
function live.spawn(section, pos)
	local sim = alife()
	if not sim then error("spawn needs the server role (alife)") end
	local pl = first_player()
	local p, lv
	if pos == nil then
		-- a walkable AI-mesh vertex 4 m in front of the player (a spawn on an invalid vertex crashes the server: "Invalid vertex for object")
		local d = pl.obj:direction()
		lv = safe(function() return level.vertex_in_direction(pl.obj:level_vertex_id(), d, 4) end)
		if lv == nil or lv >= 4000000000 then lv = pl.obj:level_vertex_id() end
		p = level.vertex_position(lv)
	else
		p = resolve_pos(pos)
		lv = safe(function() return level.vertex_id(p) end)
		if lv == nil or lv >= 4000000000 then error("position " .. vstr(p) .. " is not on the AI mesh") end
		p = level.vertex_position(lv)
	end
	local gv = pl.obj:game_vertex_id()
	local se = sim:create(section, p, lv, gv)
	return se and se.id or nil
end

local function get_obj(o)
	local t = type(o)
	if t == "number" then return safe(level.object_by_id, o) end
	if t == "string" then
		local f = live.find(o, 1)[1]
		if f then return safe(level.object_by_id, f.id) end
		return nil
	end
	return o
end
live.obj = get_obj

-- live.hit(obj, power [, bone [, type]]) -> true.  One hit of `power` (0..1 of max health). obj = id / name / game_object;
-- type: "wound" (default), "fire_wound", "strike", "explosion".  The engine applies a hit on the NEXT frame: health/alive change after it.
function live.hit(o, power, bone, htype)
	local obj = get_obj(o)
	if obj == nil then error("object not online (hit needs an online object): " .. tostring(o)) end
	local h = hit()
	h.type = hit[htype or "wound"]
	h.power = power or 0.2
	h.impulse = 0
	h.direction = vector():set(0, 0, 1)
	local pl = first_player()
	h.draftsman = pl and pl.obj or obj
	if bone then h.bone = bone end
	obj:hit(h)
	return true
end

-- live.async(step [, timeout_s]): return this from a command; step() runs every frame until it returns a non-nil value (that value becomes
-- the command's result) or the timeout passes.  Used by kill / waits so the answer arrives when the thing really happened.
function live.async(step, timeout_s)
	return setmetatable({ step = step, timeout = timeout_s or 20 }, { __pending = true })
end

-- live.kill(obj [, power [, bone [, type [, maxhits]]]]) : one hit per frame until dead; the answer says how many hits it took.
-- If health stops dropping (a wounded stalker sits at about 0.1 and ignores small hits), the power doubles every 5 useless hits up
-- to 1.0; if even that does nothing for 10 hits, it falls back to game_object:kill() and says so (with the invulnerable flag).
function live.kill(o, power, bone, htype, maxhits)
	local n, stuck, pw = 0, 0, power or 0.1
	local c0 = os.clock()
	local obj = get_obj(o)
	if obj == nil then error("object not online: " .. tostring(o)) end
	local id = obj:id()
	local last_hp, forced = nil, false
	return live.async(function()
		local ob = safe(level.object_by_id, id)
		if ob == nil then return "object left the level after " .. n .. " hits" end
		local hp = ob.health
		if not ob:alive() then
			if forced then return string.format("killed by game_object:kill() after %d hits had no effect (health stuck at %.3f, invulnerable=%s)", n, last_hp or -1, tostring(safe(function() return ob:invulnerable() end))) end
			return string.format("dead after %d hits (start power %s, end power %s, %.1f s)", n, tostring(power or 0.1), tostring(pw), os.clock() - c0)
		end
		-- stuck = this hit did not take health below the lowest value seen (something may heal it back up between frames)
		if last_hp ~= nil and hp >= last_hp - 0.0005 then stuck = stuck + 1 else stuck = 0 end
		if last_hp == nil or hp < last_hp then last_hp = hp end
		if stuck >= 5 and pw < 1 then pw = math.min(1, pw * 2); stuck = 0 end
		if (stuck >= 10 and pw >= 1) or n >= (maxhits or 200) then
			if forced then return string.format("STILL ALIVE after %d hits and game_object:kill(), health %.3f", n, hp) end
			local pl = first_player()
			forced = true
			ob:kill(pl and pl.obj or ob)
			return nil
		end
		live.hit(ob, pw, bone, htype)
		n = n + 1
	end, 60)
end

-- live.peace(): make every NPC community neutral to the others AND to the players (community "actor"), and every online NPC neutral to
-- every player.  Without it a spawned bandit is shot by the village, or shoots the test player (death -> GAME OVER -> save reload).
function live.peace()
	-- names must exist in the game's community list: an unknown one is a C++ assert that kills the server ("item not found, id military")
	local cs = { "actor", "stalker", "bandit", "monolith", "army", "killer", "ecolog", "dolg", "freedom", "zombied" }
	for _, a in ipairs(cs) do for _, b in ipairs(cs) do if a ~= b then pcall(relation_registry.set_community_relation, a, b, 0) end end end
	local pls = live.players()
	for _, pl in ipairs(pls) do
		for _, c in ipairs(cs) do if c ~= "actor" then pcall(relation_registry.set_community_goodwill, c, pl.id, 0) end end
	end
	local n = 0
	scan(function(id, se, o)
		if o and safe(IsStalker, nil, o:clsid()) and string.find(o:section(), "^actor") == nil and o:alive() then
			for _, pl in ipairs(pls) do if pl.obj and pl.obj:alive() then pcall(function() o:set_relation(game_object.neutral, pl.obj) end) end end
			n = n + 1
		end
	end)
	return "communities neutral to each other and to the players; " .. n .. " online NPCs set neutral to " .. #pls .. " player(s)"
end

-- live.shot([name]) : engine screenshot (clients only: a dedicated server has no screen).  lua.ps1 copies the file to live\shots.
function live.shot(name)
	if safe(IsDedicatedServer) then error("the dedicated server has no screen: use -Role A") end
	-- "screenshot jpg" only: a "flush" in the same frame makes the engine drop the screenshot, and a bare "screenshot" writes nothing here
	get_console():execute("screenshot jpg")
	live.shots = live.shots + 1
	return "SHOT:" .. tostring(name or ("live" .. live.shots))
end

-- live.inv([player]) -> table of {section, count} + money, as lines.  player = name / id / game_object (default first player)
function live.inv(who)
	local obj
	if who == nil then local pl = first_player() obj = pl and pl.obj
	elseif type(who) == "string" then for _, pl in ipairs(live.players()) do if string.lower(tostring(pl.name)) == string.lower(who) then obj = pl.obj end end
	else obj = get_obj(who) end
	if not obj then error("no such player") end
	local counts, order, total = {}, {}, 0
	obj:iterate_inventory(function(owner, item)
		local s = item:section()
		if counts[s] == nil then counts[s] = 0 order[#order + 1] = s end
		counts[s] = counts[s] + 1
		total = total + 1
	end, obj)
	table.sort(order)
	local res = newlist()
	for _, s in ipairs(order) do res[#res + 1] = { section = s, count = counts[s], line = string.format("%-34s x%d", s, counts[s]) } end
	res.total = total
	res.money = safe(function() return obj:money() end)
	res.owner = safe(function() return obj:name() end)
	local mt = getmetatable(res)
	setmetatable(res, { __tostring = function(t)
		local out = { string.format("inventory of %s: %d items, %d kinds, money %s", tostring(t.owner), t.total, #t, tostring(t.money)) }
		for i = 1, #t do out[#out + 1] = t[i].line end
		return table.concat(out, "\n")
	end })
	return res
end

function live.state()
	local pls = live.players()
	local names = {}
	for _, p in ipairs(pls) do names[#names + 1] = tostring(p.name) .. "#" .. tostring(p.id) .. (p.alive and "" or "(dead)") end
	local srv = is_server()
	local sim = safe(alife)
	return string.format("level=%s server=%s dedicated=%s alife=%s players=[%s] time_global=%d", tostring(safe(level.name)), tostring(srv),
		tostring(safe(IsDedicatedServer)), tostring(sim ~= nil), table.concat(names, ","), time_global())
end

-- live.save(): the server's own save (game_sv.saveGame, writes "quicksave - N.scop", N rotating 1..5, into this role's savedgames\<addon>\).
-- save_live.ps1 calls this and copies the new file into live\saves.
function live.save()
	if not is_server() then error("save needs the server role (S, or A in a listen session)") end
	game_sv.saveGame(0)
	return "save requested"
end

-- live.load_last(): game_sv.loadLastSave (newest save of this session). The level reloads and the Lua VM restarts.
function live.load_last()
	game_sv.loadLastSave(0)
	return "load requested"
end

-- ---------- travel between levels (party vote, started from Cordon) -----------------------------------------------------
local GUIDE = {
	AES_1 = "coop_l11_stancia_1", AES_2 = "coop_l11_stancia_2", AGRU = "coop_l03_agroprom_underground", AGR = "coop_l03_agroprom",
	BAR = "coop_l05_bar", CON = "coop_l11_control_monolith", GAR = "coop_l02_garbage", MIL = "coop_l07_military", PRI = "coop_l10_pripyat",
	RAD = "coop_l09_radar", ROS = "coop_l06_rostok", SAR = "coop_l11_sarcofag", VAL = "coop_l04_darkvalley", X10 = "coop_l09_x10",
	X16 = "coop_l08_x16", X18 = "coop_l04_x18", YAN = "coop_l08_yantar",
}
live.GUIDE = GUIDE
local FALLBACK = { BAR = { "esc_smart_terrain_1_guide_temp_6_walk", "esc_smart_terrain_1_guide_temp_6_look" },
                   SAR = { "esc_smart_terrain_1_guide_temp_15_walk", "esc_smart_terrain_1_guide_temp_15_look" } }

-- live.travel("bar" | "BAR" | "coop_l05_bar") : from Cordon, gives the guide flag and votes yes for every player every 8 s (what the Yes buttons do).
-- The answer arrives from the NEW Lua VM after the level change ("arrived on <level> after N s"), because a level change restarts the VM.
function live.travel(dest)
	local d = string.upper(tostring(dest))
	local code, lvl
	if GUIDE[d] then code, lvl = d, GUIDE[d]
	else
		local low = string.lower(tostring(dest))
		for c, l in pairs(GUIDE) do if l == low or l == "coop_" .. low or l == "coop_l" .. low then code, lvl = c, l end end
	end
	if not code then local ks = {} for c in pairs(GUIDE) do ks[#ks + 1] = c end table.sort(ks) error("unknown destination " .. tostring(dest) .. "; codes: " .. table.concat(ks, ",")) end
	if safe(level.name) == lvl then return "already on " .. lvl end
	if safe(level.name) ~= "coop_l01_escape" then error("the guide vote starts on Cordon (now " .. tostring(safe(level.name)) .. ")") end
	story_flags.give_flag("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_" .. code .. "_INFO")
	local c0, last, fb = os.clock(), -100, false
	local job = live.async(function()
		local t = os.clock() - c0
		if t > 3 and t - last >= 8 then
			last = t
			local n = 0
			for _, pl in ipairs(live.players()) do if pl.alive and pcall(coop_map_vote.on_yes, pl.id) then n = n + 1 end end
			live.note("travel vote yes for " .. n .. " player(s) at " .. string.format("%.0f", t) .. " s")
			if not fb and t > 40 and FALLBACK[code] then
				fb = true
				pcall(function() xr_effects.xrmpe_teleport_actors(nil, nil, FALLBACK[code]) end)
				live.note("travel fallback teleport to the guide spot")
			end
		end
	end, 240)
	job.persist = { kind = "level", dest = lvl, t0 = os.time() }
	return job
end

-- notes go to live_notes.log (read it with: type <role logs>\live_notes.log)
function live.note(msg)
	local f = io.open(logpath("live_notes.log"), "a")
	if f then f:write(string.format("[%d] %s\n", math.floor(os.clock()), tostring(msg))) f:close() end
end

-- live.defer(seconds, fn) : run fn later from the poll loop (fn's errors go to live_defer.log)
function live.defer(sec, fn) live.tasks[#live.tasks + 1] = { at = time_global() + sec * 1000, fn = fn } end

-- live.reload("xr_effects", "C:\\path\\xr_effects.script") : re-run a script file into the namespace of the loaded script of that name.
-- Functions and tables assigned at top level are replaced for every caller that looks them up through the namespace; `local` variables
-- and local functions of the old file stay as they were for code already compiled.  Config (ltx/xml) changes are NOT reloadable.
live.reload_dirs = {}
function live.reload(name, path)
	name = string.gsub(tostring(name), "%.d?script$", "")
	if not path then
		for _, d in ipairs(live.reload_dirs) do
			for _, ext in ipairs({ ".script", ".dscript" }) do
				local p = d .. "\\" .. name .. ext
				local f = io.open(p, "r")
				if f then f:close() path = p break end
			end
			if path then break end
		end
	end
	if not path then error("no path given and no file '" .. name .. ".script' in " .. table.concat(live.reload_dirs, ";")) end
	local f = io.open(path, "rb")
	if not f then error("cannot open " .. path) end
	local src = f:read("*a")
	f:close()
	local chunk, err = loadstring(src, "@" .. path)
	if not chunk then error("syntax error: " .. tostring(err)) end
	local ns = _G[name]
	if type(ns) ~= "table" then error("script namespace '" .. name .. "' is not loaded in this role (" .. type(ns) .. ")") end
	local before = 0
	for _ in pairs(ns) do before = before + 1 end
	setfenv(chunk, ns)
	chunk()
	local after = 0
	for _ in pairs(ns) do after = after + 1 end
	return string.format("reloaded %s from %s (%d -> %d names in the namespace)", name, path, before, after)
end

-- ---------- command execution ------------------------------------------------------------------------------------------------
local env = setmetatable({}, { __index = _G })
env.live = live
env.print = function(...)
	local t = {}
	for i = 1, select("#", ...) do t[#t + 1] = live.dump((select(i, ...)), 3) end
	live.out[#live.out + 1] = table.concat(t, "\t")
end
env.printf = env.print

local function compile(src)
	local fn = loadstring("return " .. src, "=live")
	if fn then return fn end
	local fn2, err2 = loadstring(src, "=live")
	if fn2 then return fn2 end
	-- "stmts; expr": split at the last ';' or newline and return the tail as an expression
	local head, tail = string.match(src, "^(.*)[;\n]%s*([^;\n]+)%s*$")
	if head and tail then
		local fn3 = loadstring(head .. "\nreturn " .. tail, "=live")
		if fn3 then return fn3 end
	end
	return nil, err2
end

local function run_chunk(src)
	live.out = {}
	local fn, err = compile(src)
	if not fn then return false, "syntax error: " .. tostring(err) end
	setfenv(fn, env)
	local res = { pcall(fn) }
	if not res[1] then return false, tostring(res[2]) end
	local first = res[2]
	if type(first) == "table" and getmetatable(first) and getmetatable(first).__pending then return true, nil, first end
	for i = 2, #res do live.out[#live.out + 1] = live.dump(res[i], 3) end
	return true
end

local function write_result(n, ok, ms)
	local f = io.open(logpath("live_res_" .. n .. ".txt"), "w")
	if not f then return end
	f:write((ok and "OK " or "ERR ") .. ms .. "\n")
	for _, l in ipairs(live.out) do f:write(l, "\n") end
	f:write("--END--\n")
	f:close()
end

local function ms_since(c0) return math.floor((os.clock() - c0) * 1000) end

-- a command that returned live.async(...): its step runs every frame (see tick); the answer is written when it finishes
local function step_pending()
	local p = live.pend
	if not p then return end
	-- tick() is called from several update hooks per frame; run the step once per frame (time_global is constant within a frame)
	local now = time_global()
	if p.frame == now then return end
	p.frame = now
	local ok, r1 = pcall(p.job.step)
	if not ok then
		live.out = { tostring(r1) }
		write_result(p.n, false, ms_since(p.c0))
		live.pend = nil
	elseif r1 ~= nil then
		live.out = { live.dump(r1, 3) }
		write_result(p.n, true, ms_since(p.c0))
		live.pend = nil
		os.remove(logpath("live_pend.txt"))
	elseif os.clock() - p.c0 > p.job.timeout then
		live.out = { "timeout: the async command did not finish in " .. p.job.timeout .. " s" }
		write_result(p.n, false, ms_since(p.c0))
		live.pend = nil
	end
end

local function poll()
	for _ = 1, 20 do   -- drain a burst of queued commands (not while an async one is still running: keeps the order)
		if live.pend then break end
		local n = live.seq + 1
		local f = io.open(logpath("live_cmd_" .. n .. ".lua"), "rb")
		if not f then break end
		local src = f:read("*a")
		f:close()
		live.seq = n
		-- a level change restarts the Lua VM: the sequence number must survive it (else old commands would run again)
		local sf = io.open(logpath("live_seq.txt"), "w")
		if sf then sf:write(tostring(n)) sf:close() end
		local c0 = os.clock()
		local ok, err, pend = run_chunk(src)
		if pend then
			live.pend = { n = n, job = pend, c0 = c0 }
			if pend.persist then
				local pf = io.open(logpath("live_pend.txt"), "w")
				if pf then pf:write(string.format("%d|%s|%s|%d", n, pend.persist.kind, pend.persist.dest, pend.persist.t0)) pf:close() end
			end
		else
			if not ok then live.out[#live.out + 1] = tostring(err) end
			write_result(n, ok, ms_since(c0))
		end
	end
end

local function tick()
	local now = time_global()
	if live.pend then step_pending() end
	if now - live.last < 250 then return false end
	live.last = now
	if not live.ready then
		live.ready = true
		-- after a VM restart: continue the numbering and answer a pending level-change command (travel) from this new VM
		local sf = io.open(logpath("live_seq.txt"), "r")
		if sf then local v = tonumber(sf:read("*a")) sf:close() if v and v > live.seq then live.seq = v end end
		local pf = io.open(logpath("live_pend.txt"), "r")
		if pf then
			local txt = pf:read("*a") pf:close()
			local n, kind, dest, t0 = string.match(txt, "^(%d+)|([^|]*)|([^|]*)|(%d+)")
			if n and kind == "level" then
				if safe(level.name) == dest then
					live.out = { string.format("arrived on %s after %d s (the Lua VM restarted: that is why this answer comes from the new level)", dest, os.time() - tonumber(t0)) }
					write_result(tonumber(n), true, (os.time() - tonumber(t0)) * 1000)
					os.remove(logpath("live_pend.txt"))
				end
			end
		end
		local f = io.open(logpath("live_ready.txt"), "w")
		if f then f:write(string.format("role=%s level=%s time=%d\n", tostring(_G.qa and _G.qa.cfg and _G.qa.cfg.role), tostring(safe(level.name)), now)) f:close() end
		-- reload directories (written by start_live.ps1 into live_role.txt: reload_dir=<path>)
		local rf = io.open(logpath("qa_role.txt"), "r")
		if rf then
			for line in rf:lines() do
				local d = string.match(line, "^%s*reload_dir%s*=%s*(.-)%s*$")
				if d and d ~= "" then live.reload_dirs[#live.reload_dirs + 1] = d end
				local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
				if k == "live_save" then live.save_mode = (v == "1") end
				if k == "live_keep_snap" and v == "1" and _G.qa then _G.qa.last_snap = 0 end   -- run_coop -Save: the comparer needs the harness snapshots
				if k == "clients" then live.want = tonumber(v) or 1 end
			end
			rf:close()
		end
	end
	-- save mode: the saved actor ("ghost") counts as an alive player for the harness, so its hands-free respawn never spawns the real client.
	-- Here the server respawns spectators itself as long as fewer harness-named players than clients are alive.
	if live.save_mode and is_server() and now - (live.last_resp or 0) > 6000 and now > 8000 then
		live.last_resp = now
		local reals = 0
		for _, p in ipairs(live.players()) do if p.alive and is_real(p) then reals = reals + 1 end end
		if reals < (live.want or 1) then
			local ok3, err3 = pcall(function() game.respawn_dead_players() end)
			live.note("save mode: respawn_dead_players (real players " .. reals .. "/" .. (live.want or 1) .. ") " .. (ok3 and "called" or tostring(err3)))
		end
	end
	local ok, err = pcall(poll)
	if not ok then
		local f = io.open(logpath("live_defer.log"), "a")
		if f then f:write("poll error ", tostring(err), "\n") f:close() end
	end
	for i = #live.tasks, 1, -1 do
		local t = live.tasks[i]
		if now >= t.at then
			table.remove(live.tasks, i)
			local ok2, err2 = pcall(t.fn)
			if not ok2 then
				local f = io.open(logpath("live_defer.log"), "a")
				if f then f:write("deferred error ", tostring(err2), "\n") f:close() end
			end
		end
	end
	return false
end

do
	local ok, err = pcall(function() level.add_call(tick, function() end) end)
	local f = io.open(getFS():update_path("$logs$", "live_load.txt"), "a")
	if f then f:write("live_hooks loaded, add_call ", ok and "ok" or tostring(err), "\n") f:close() end
end
end
