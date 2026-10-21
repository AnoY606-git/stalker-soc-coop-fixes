-- Cordon rookie village NPC check (test only, never shipped). Patch campfires: seats of the kamp scheme (scripts\xr_kamp.script).
-- After START seconds (default 120, -Cfg start=N) every NPC that the village smart terrain (esc_smart_terrain_1) holds is looked at twice, WINDOW
-- seconds apart (default 20, -Cfg window=N), and again one window later. Asserts (qa_assert.log of client_S):
--   "village job <name>"      the NPC has a job in smart.npc_info / smart.job_data
--   "village seat <name>"     a kamp NPC stands within 1.3 m of his seat (or has been told to sit where he stands: st.arrived)
--   "village stuck <name>"    NOT stuck: an NPC that wants to move (target_movement_type is not stand) moved at least 0.3 m in the window
--   "village overlap <a>/<b>" no two online NPCs of the village closer than 0.5 m (ground plane) at either sample
-- Every NPC is also logged ("VILLAGE ... job=... scheme=... d_fire=... moved=... move=..." in qa_events.log) so a failure names job and scheme.
-- Run (LISTEN mode, NPC AI only works there; one game test at a time):
--   powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 `
--     -Owner villagenpc -Hooks <repo>\patches\campfires\tests\village_npcs.lua -ExtraDir <stage>\gamedata -SoakSeconds 230 -ResultDir <dir>
-- then: python <games>\tools\stalker_xrmpe\qa_verdict.py <dir>
local FIRE1 = { x = -206.90, y = -19.61, z = -140.08 }
local FIRE2 = { x = -234.92, y = -19.36, z = -156.80 }
local START = tonumber(qa.cfg.start) or 120
local WINDOW = tonumber(qa.cfg.window) or 20
local MOVED_MIN = 0.3
local OVERLAP = 0.5
local SEAT_NEAR = 1.3
local S = { snap = {}, done = {} }

local function d2(a, b) return math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2) end

-- every NPC of the village smart terrain: id -> { name, job, scheme, lo (online object or nil), pos }
local function village()
	local sim = alife()
	local smart = nil
	pcall(function() smart = sim:object("esc_smart_terrain_1") end)
	local out, n = {}, 0
	if smart == nil or smart.npc_info == nil then return out, 0, smart end
	for id, info in pairs(smart.npc_info) do
		local se = sim:object(id)
		if se ~= nil then
			local alive = true
			pcall(function() alive = se:alive() end)
			if alive then
				local job = nil
				pcall(function()
					if info.job_id ~= nil and info.job_id >= 0 and smart.job_data[info.job_id] ~= nil then job = smart.job_data[info.job_id].section end
				end)
				local lo = level.object_by_id(id)
				local pos = se.position
				if lo ~= nil then pos = lo:position() end
				local scheme = "-"
				if lo ~= nil then pcall(function() local st = db.storage[id]; if st ~= nil then scheme = tostring(st.active_section) end end) end
				out[id] = { id = id, name = se:name(), job = job, scheme = scheme, lo = lo, pos = { x = pos.x, y = pos.y, z = pos.z } }
				n = n + 1
			end
		end
	end
	return out, n, smart
end

local function moving(lo)
	local m = false
	pcall(function() m = (lo:target_movement_type() ~= move.stand) end)
	return m
end

local function seat_dist(r)
	local kd = nil
	pcall(function()
		local st = db.storage[r.id]
		local k = st ~= nil and st.kamp or nil
		if k ~= nil then
			if k.arrived == true then
				kd = 0
			elseif k.pos_vertex ~= nil then
				local vp = level.vertex_position(k.pos_vertex)
				kd = d2(vp, r.pos)
			else
				kd = 99
			end
		end
	end)
	return kd
end

local function check(tag, a, b)
	-- a = sample WINDOW seconds ago, b = now
	local bad = 0
	local names = {}
	for id, r in pairs(b) do
		names[#names + 1] = id
	end
	table.sort(names, function(x, y) return b[x].name < b[y].name end)
	for _, id in ipairs(names) do
		local r = b[id]
		local p = a[id]
		qa.assert(string.format("village job %s %s", tag, r.name), r.job ~= nil, "job=" .. tostring(r.job) .. " scheme=" .. r.scheme)
		local moved = -1
		local mv = false
		if r.lo ~= nil and p ~= nil and p.lo ~= nil then
			moved = d2(p.pos, r.pos)
			mv = moving(r.lo) and moving(p.lo)
			qa.assert(string.format("village stuck %s %s", tag, r.name), not (mv and moved < MOVED_MIN),
				string.format("moved %.2f m in %d s while moving, job=%s scheme=%s", moved, WINDOW, tostring(r.job), r.scheme))
		end
		local sd = r.lo ~= nil and seat_dist(r) or nil
		if sd ~= nil then
			qa.assert(string.format("village seat %s %s", tag, r.name), sd <= SEAT_NEAR, string.format("%.1f m from the seat, job=%s", sd, tostring(r.job)))
		end
		qa.event(string.format("VILLAGE %s %-34s %-8s job=%-40s scheme=%-34s d_fire1=%5.1f d_fire2=%5.1f moved=%5.2f move=%s seat=%s pos=%.1f,%.1f,%.1f", tag, r.name,
			r.lo ~= nil and "online" or "offline", tostring(r.job), r.scheme, d2(r.pos, FIRE1), d2(r.pos, FIRE2), moved, tostring(mv), sd ~= nil and string.format("%.1f", sd) or "-",
			r.pos.x, r.pos.y, r.pos.z))
	end
	-- overlap of online NPCs
	for i = 1, #names do
		for j = i + 1, #names do
			local x, y = b[names[i]], b[names[j]]
			if x.lo ~= nil and y.lo ~= nil then
				local d = d2(x.pos, y.pos)
				qa.assert(string.format("village overlap %s %s/%s", tag, x.name, y.name), d >= OVERLAP, string.format("%.2f m apart, jobs %s / %s", d, tostring(x.job), tostring(y.job)))
			end
		end
	end
	qa.event(string.format("VILLAGE %s checked %d npcs of esc_smart_terrain_1", tag, #names))
end

qa.hooks.village_npcs = function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l01_escape" then return end
	-- godmode, and stand next to the fire so the village stays online
	for id, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then v.health = 1 end end
	if t >= 20 and not S.tp then
		S.tp = true
		for id, v in pairs(db.mp_actors or {}) do
			if v ~= nil and v:alive() then
				local tx, ty, tz = FIRE1.x + 3.0, FIRE1.y + 0.5, FIRE1.z + 7.0
				pcall(function() v:set_actor_position(vector():set(tx, ty, tz)) end)
				pcall(function() v:set_actor_direction(-math.atan2(FIRE1.x - tx, FIRE1.z - tz)) end)
			end
		end
		qa.event("VILLAGE player placed next to the village fire")
	end
	local k = 0
	while true do
		local t0 = START + k * WINDOW
		if t >= t0 and S.snap[k] == nil then
			local ok, snap, n = pcall(function() local a, b = village(); return a, b end)
			if ok then
				S.snap[k] = snap
				qa.event(string.format("VILLAGE sample %d at t=%d: %d npcs in the village smart terrain", k, t, n))
				if k > 0 and S.snap[k - 1] ~= nil then
					local ok2, err = pcall(check, "w" .. k, S.snap[k - 1], snap)
					if not ok2 then qa.assert("village check w" .. k .. " ran", false, tostring(err)) end
				end
			else
				qa.assert("village sample " .. k, false, tostring(snap))
				S.snap[k] = {}
			end
		end
		if t < t0 or k >= 2 then break end
		k = k + 1
	end
end
