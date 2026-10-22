-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): two-client QA harness for Shadow of COOP on xrMPE 0.9.
-- qa_build.py appends this file (then your hook files) to shipped scripts of a COPY of coop.addon; run_coop.ps1 starts the
-- clients.  Everything runs inside the game; every client writes its own files into its own $logs$ folder:
--   qa_state.log   one JSON snapshot per 5 s (shared state + per-player state), read by qa_compare.py
--   qa_events.log  harness events (spawn, scenario steps, commands)
--   qa_assert.log  "PASS|FAIL <name> <detail>" lines written by qa.assert / qa.eventually (your hooks)
-- Config comes from $logs$\qa_role.txt (key=value lines, written by run_coop.ps1): role=A|B, scenario=..., clients=N, ...
-- Control: run_coop.ps1 (or you) appends commands to $logs$\qa_cmd.txt: screenshot | snap | console <cmd> | flag <name> | setflag <name>
-- Lua facts used here (verified on xrMPE 0.9): log() does not reach the file, so use io.open + close; abort() is a no-op;
-- game.respawn_dead_players() (server side) spawns spectators as actors; releasing an object in the frame it was created crashes.
-------------------------------------------------------------------------------------------------------
if not _G.qa then
_G.qa = { hooks = {}, cfg = {}, t0 = nil, last = 0, last_snap = 0, last_respawn = 0, spawned_at = nil, cmd_done = 0,
          pending = {}, scen = {}, ticks = 0, level = nil, snaps = 0 }
local qa = _G.qa

local function path(name) return getFS():update_path("$logs$", name) end

local function append(name, line)
	local ok = pcall(function()
		local f = io.open(path(name), "a")
		if f then f:write(line, "\n"); f:close() end
	end)
	return ok
end

local function now_s() return (time_global() - (qa.t0 or time_global())) / 1000 end

function qa.event(msg) append("qa_events.log", string.format("[%6.1f] %s", now_s(), tostring(msg))) end

-- ---------- config -------------------------------------------------------------------------------------------------
local function read_cfg()
	local f = io.open(path("qa_role.txt"), "r")
	if not f then return end
	for line in f:lines() do
		local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
		if k then qa.cfg[k] = v end
	end
	f:close()
end

-- ---------- tiny JSON writer (sorted keys, so snapshots diff cleanly) -----------------------------------------------
local function jstr(s)
	s = tostring(s)
	s = string.gsub(s, '[%c"\\]', function(c)
		if c == '"' then return '\\"' elseif c == "\\" then return "\\\\" end
		return string.format("\\u%04x", string.byte(c))
	end)
	return '"' .. s .. '"'
end

local function is_array(t)
	local n = 0
	for _ in pairs(t) do n = n + 1 end
	return n == #t
end

function qa.json(v)
	local tv = type(v)
	if tv == "table" then
		local out = {}
		if next(v) == nil then return "[]" end
		if is_array(v) then
			for i = 1, #v do out[#out + 1] = qa.json(v[i]) end
			return "[" .. table.concat(out, ",") .. "]"
		end
		local keys = {}
		for k in pairs(v) do keys[#keys + 1] = tostring(k) end
		table.sort(keys)
		for _, k in ipairs(keys) do
			local val = v[k]
			if val == nil then val = v[tonumber(k)] end
			out[#out + 1] = jstr(k) .. ":" .. qa.json(val)
		end
		return "{" .. table.concat(out, ",") .. "}"
	elseif tv == "number" then
		if v ~= v or v == math.huge or v == -math.huge then return "null" end
		return string.format("%.14g", v)
	elseif tv == "boolean" then return tostring(v)
	elseif v == nil then return "null" end
	return jstr(v)
end

-- ---------- helpers ------------------------------------------------------------------------------------------------
local function safe(f, ...)
	local ok, r = pcall(f, ...)
	if ok then return r end
	return nil
end

function qa.local_object()
	local id = safe(LocalActor)
	if not id or id == 0 then return nil end
	return safe(level.object_by_id, id)
end

local function vec(p) return { tonumber(string.format("%.1f", p.x)), tonumber(string.format("%.1f", p.y)), tonumber(string.format("%.1f", p.z)) } end

function qa.assert(name, ok, detail)
	append("qa_assert.log", (ok and "PASS " or "FAIL ") .. tostring(name) .. " " .. tostring(detail or ""))
	qa.event((ok and "ASSERT PASS " or "ASSERT FAIL ") .. tostring(name) .. " " .. tostring(detail or ""))
end

-- qa.eventually("name", function() return true/false, "detail" end, timeout_s): polls every tick (never a single early check);
-- PASS as soon as fn() is true, FAIL at timeout.  Starts counting at the call.
function qa.eventually(name, fn, timeout_s)
	qa.pending[#qa.pending + 1] = { name = name, fn = fn, deadline = now_s() + (timeout_s or 30), last = "" }
end

-- qa.once("name", function(t, lo) ... end): runs once, the first tick after THIS client's own player has spawned.
function qa.once(name, fn)
	local key = "once_" .. name
	qa.hooks[key] = function(t, lo)
		qa.hooks[key] = nil
		fn(t, lo)
	end
end

-- ---------- shared / per-player state ------------------------------------------------------------------------------
local function story_flag_list()
	local out = {}
	local sf = safe(function() return story_flags.story_flags end)
	if type(sf) == "table" then
		for k, v in pairs(sf) do
			if v ~= false and v ~= nil and v ~= 0 then out[#out + 1] = tostring(k) end
		end
	end
	table.sort(out)
	return out
end

local function info_list()
	local out = {}
	local ids = safe(function() return story_flags_table.flags_to_id end)
	if type(ids) == "table" then
		for name in pairs(ids) do
			if safe(has_alife_info, name) then out[#out + 1] = name end
		end
	end
	table.sort(out)
	return out
end

local function task_map(lo)
	local res = {}
	local cand = {}
	local tm = safe(function() return task_manager.get_task_manager().task_info end)
	if type(tm) == "table" then for id in pairs(tm) do cand[tostring(id)] = true end end
	if qa.cfg.tasks then for id in string.gmatch(qa.cfg.tasks, "[^,]+") do cand[id] = true end end
	if qa.task_ids then for _, id in ipairs(qa.task_ids) do cand[id] = true end end
	for id in pairs(cand) do
		local t = lo and safe(function() return lo:get_task(id, true) end)
		if t then
			local st = safe(function() return t:get_state() end)
			res[id] = st ~= nil and tostring(st) or "present"
		end
	end
	return res
end

local function snapshot(lo)
	local side = (safe(OnServer) and "server" or "client")
	local snap = { v = 1, role = qa.cfg.role or "?", t = tonumber(string.format("%.1f", now_s())), side = side,
	               spawned = qa.spawned_at ~= nil, ticks = qa.ticks }
	snap.shared = { level = safe(level.name), flags = story_flag_list(), infos = info_list(), tasks = task_map(lo) }
	if lo then
		local p = lo:position()
		snap.player = { id = lo:id(), name = safe(function() return lo:name() end), pos = vec(p), alive = safe(function() return lo:alive() end),
		                health = safe(function() return lo.health end), section = lo:section() }
		-- nearby objects by section within 50 m (client-side view; per-player field)
		local near, total = {}, 0
		for id = 1, 65534 do
			local o = safe(level.object_by_id, id)
			if o ~= nil and o:id() ~= lo:id() and o:parent() == nil then
				local d = o:position():distance_to(p)
				if d <= 50 then
					local s = o:section()
					near[s] = (near[s] or 0) + 1
					total = total + 1
				end
			end
		end
		snap.near = near
		snap.near_total = total
	end
	local others = {}
	local me = safe(LocalActor)
	if type(db.mp_actors) == "table" then
		for id, v in pairs(db.mp_actors) do
			if v ~= nil and id ~= me then
				others[#others + 1] = { id = id, name = safe(function() return v:name() end), pos = safe(function() return vec(v:position()) end),
				                        alive = safe(function() return v:alive() end) }
			end
		end
		table.sort(others, function(a, b) return a.id < b.id end)
	end
	snap.others = others
	snap.n_actors = (type(db.mp_actors) == "table") and (function() local c = 0 for _ in pairs(db.mp_actors) do c = c + 1 end return c end)() or 0
	append("qa_state.log", qa.json(snap))
	qa.snaps = qa.snaps + 1
end

-- ---------- commands from run_coop.ps1 -----------------------------------------------------------------------------
local function run_command(line, lo)
	local cmd, arg = string.match(line, "^%s*(%S+)%s*(.-)%s*$")
	if not cmd then return end
	qa.event("CMD " .. line)
	if cmd == "screenshot" then
		local ok, err = pcall(function() get_console():execute("screenshot") end)
		qa.event("screenshot " .. (ok and "requested" or tostring(err)))
	elseif cmd == "snap" then
		snapshot(lo)
	elseif cmd == "console" then
		pcall(function() get_console():execute(arg) end)
	elseif cmd == "flag" then
		pcall(function() story_flags.give_flag(arg) end)
	elseif cmd == "setflag" then
		pcall(function() story_flags.set_flag(arg, true) end)
	end
end

local function poll_commands(lo)
	local f = io.open(path("qa_cmd.txt"), "r")
	if not f then return end
	local n = 0
	for line in f:lines() do
		n = n + 1
		if n > qa.cmd_done then run_command(line, lo) end
	end
	f:close()
	qa.cmd_done = n
end

-- ---------- built-in scenarios (selected with scenario=... in qa_role.txt) ----------------------------------------------
-- flag_sync:      the SERVER gives a story flag once all clients are in; both clients must show it (qa_compare --require-flag).
-- mutate_flag_b:  mutation twin: client B sets a story flag LOCALLY only; the comparer must report a shared-state mismatch.
qa.scen.flag_sync = function(t, lo)
	if not safe(OnServer) or qa.scen_done then return end
	local want = tonumber(qa.cfg.clients or "2") or 2
	local alive = 0
	if type(db.mp_actors) == "table" then
		for id, v in pairs(db.mp_actors) do if v ~= nil and safe(function() return v:alive() end) then alive = alive + 1 end end
	end
	if alive >= want then
		qa.scen_wait = qa.scen_wait or t
		if t - qa.scen_wait > 6 then
			qa.scen_done = true
			local flag = qa.cfg.flag or "QA_SYNC_FLAG_1"
			local ok, err = pcall(function() story_flags.give_flag(flag) end)
			qa.event("SCENARIO flag_sync: server give_flag(" .. flag .. ") " .. (ok and "ok" or tostring(err)))
		end
	end
end

qa.scen.mutate_flag_b = function(t, lo)
	if qa.cfg.role ~= "B" or qa.scen_done then return end
	if t > 12 then
		qa.scen_done = true
		local ok, err = pcall(function() story_flags.set_flag("QA_MUTANT_ONLY_B", true) end)
		qa.event("SCENARIO mutate_flag_b: local set_flag on B only " .. (ok and "ok" or tostring(err)))
	end
end

-- ---------- main tick (level.add_call; returning false keeps it registered) --------------------------------------------
local function tick()
	local nowms = time_global()
	if qa.t0 == nil then
		qa.t0 = nowms
		read_cfg()
		qa.event("HARNESS start role=" .. tostring(qa.cfg.role) .. " scenario=" .. tostring(qa.cfg.scenario) ..
		         " server=" .. tostring(safe(OnServer)) .. " dedicated=" .. tostring(safe(IsDedicatedServer)))
	end
	qa.ticks = qa.ticks + 1
	if nowms - qa.last < 1000 then return false end
	qa.last = nowms
	local t = now_s()
	local ln = safe(level.name)
	if qa.level ~= ln then
		qa.event("LEVEL " .. tostring(ln) .. " (previous " .. tostring(qa.level) .. ")")
		qa.level = ln
		qa.first_level = qa.first_level or ln
		qa.spawned_at = nil
	end
	pcall(function() get_console():execute("flush") end)
	local lo = qa.local_object()
	local spectator = (lo == nil) or (safe(function() return lo:section() end) == "spectator")
	if not spectator and qa.cfg.player and qa.cfg.player ~= "" and not safe(IsDedicatedServer) then
		-- a spectating remote client's LocalActor() is the player it is watching: only its OWN actor counts as spawned
		local nm = safe(function() return lo:name() end)
		if nm == nil or string.lower(tostring(nm)) ~= string.lower(qa.cfg.player) then spectator = true end
	end

	-- hands-free spawn: spectators count as dead players for the server-side game.respawn_dead_players()
	local am_server = safe(OnServer)
	local want = tonumber(qa.cfg.clients or "2") or 2
	-- -Cfg no_respawn=1: no hands-free respawn (after leaving the start level; levels without player respawn points, e.g. the Sarcophagus, crash in
	-- game_sv_deathmatch::assign_RP when respawn_dead_players is called there)
	if qa.cfg.no_hands_free == "1" then
		-- -Cfg no_hands_free=1: never call respawn_dead_players (save-pack checks: see what the engine does with a loaded save by itself)
	elseif qa.cfg.no_respawn == "1" and qa.level ~= nil and qa.level ~= qa.first_level then
		-- keep respawning on the start level only
	elseif am_server and t > 8 and nowms - qa.last_respawn > 8000 then
		local alive = 0
		if type(db.mp_actors) == "table" then
			for id, v in pairs(db.mp_actors) do if v ~= nil and safe(function() return v:alive() end) then alive = alive + 1 end end
		end
		if alive < want then
			qa.last_respawn = nowms
			local ok, err = pcall(function() game.respawn_dead_players() end)
			qa.event("server respawn_dead_players (alive actors " .. alive .. "/" .. want .. ") " .. (ok and "called" or tostring(err)))
		end
	elseif (not am_server) and spectator and t > 10 and nowms - qa.last_respawn > 10000 then
		qa.last_respawn = nowms   -- remote client: harmless if it is a no-op, the server loop above does the real work
		local ok, err = pcall(function() game.respawn_dead_players() end)
		qa.event("client respawn_dead_players " .. (ok and "called" or tostring(err)))
	end

	if not spectator and qa.spawned_at == nil then
		qa.spawned_at = nowms
		local p = lo:position()
		qa.event(string.format("SPAWNED section=%s name=%s id=%d pos=%.1f,%.1f,%.1f level=%s", lo:section(), tostring(safe(function() return lo:name() end)), lo:id(), p.x, p.y, p.z, tostring(ln)))
	end

	poll_commands(lo)
	local ts = qa.spawned_at and (nowms - qa.spawned_at) / 1000 or nil
	if ts == nil and safe(IsDedicatedServer) then ts = t end   -- a dedicated server has no player: run scenarios/hooks on its own clock
	if ts then
		local sc = qa.scen[qa.cfg.scenario or ""]
		if sc then local ok, err = pcall(sc, ts, lo) if not ok then qa.event("scenario error " .. tostring(err)) qa.scen[qa.cfg.scenario] = nil end end
		for name, h in pairs(qa.hooks) do
			local ok, err = pcall(h, ts, lo)
			if not ok then qa.event("hook " .. name .. " error " .. tostring(err)); qa.hooks[name] = nil end
		end
	end
	-- qa.eventually pollers
	for i = #qa.pending, 1, -1 do
		local p = qa.pending[i]
		local ok, r, detail = pcall(p.fn)
		if ok and r then
			qa.assert(p.name, true, detail or "")
			table.remove(qa.pending, i)
		elseif t > p.deadline then
			qa.assert(p.name, false, "timeout " .. tostring(ok and detail or r))
			table.remove(qa.pending, i)
		end
	end
	if nowms - qa.last_snap >= 5000 then
		qa.last_snap = nowms
		local ok, err = pcall(snapshot, lo)
		if not ok then qa.event("snapshot error " .. tostring(err)) end
	end
	return false
end

do
	local ok, err = pcall(function() level.add_call(tick, function() end) end)
	append("qa_events.log", "harness loaded, add_call " .. (ok and "ok" or tostring(err)))
end
end
