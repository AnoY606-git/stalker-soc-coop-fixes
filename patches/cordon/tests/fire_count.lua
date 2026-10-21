-- Rookie village campfire census (test only, never shipped).
-- Counts the stalkers within 15 m of the village fire (esc_campfire, -206.9 -19.6 -140.1) after the alife settled and logs
-- name / section / profile / smart terrain job / active scheme / online flag / distance for each of them (qa_events.log, lines "FIRE ...").
-- Run in LISTEN mode (NPC AI only works there):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Hooks fire_count.lua -ExtraDir <stage>\gamedata -SoakSeconds 330
-- Also teleports the player next to the fire. Engine screenshots taken from a hook show the harness lobby window over the scene (the
-- lobby is engine side and cannot be closed from script), so the census lines are the evidence. -Cfg fast=1 = one census after 60 s.
local FIRE = { x = -206.90, y = -19.61, z = -140.08 }
local RADIUS = 15
local SAMPLES = { 60, 120, 200, 300 }
local FINAL = 330
if qa.cfg.fast == "1" then SAMPLES = { 60 }; FINAL = 140 end
local S = { done = {}, shot = {}, tp = false }

local function d3(p) return math.sqrt((p.x - FIRE.x) ^ 2 + (p.y - FIRE.y) ^ 2 + (p.z - FIRE.z) ^ 2) end

local function census(tag)
	local sim = alife()
	local smart = nil
	pcall(function() smart = sim:object("esc_smart_terrain_1") end)
	local jobs = {}
	if smart ~= nil and smart.npc_info ~= nil then
		for id, info in pairs(smart.npc_info) do
			local sec = "?"
			pcall(function()
				if info.job_id ~= nil and info.job_id >= 0 and smart.job_data[info.job_id] ~= nil then sec = smart.job_data[info.job_id].section end
			end)
			jobs[id] = sec
		end
	end
	local rows, total_sm = {}, 0
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil then
			local isst = false
			pcall(function() isst = (se:clsid() == clsid.script_stalker) end)
			if isst then
				local lo = level.object_by_id(id)
				local pos = se.position
				if lo ~= nil then pos = lo:position() end
				local d = d3(pos)
				if jobs[id] ~= nil then total_sm = total_sm + 1 end
				if d <= RADIUS or jobs[id] ~= nil then
					local sch = "-"
					if lo ~= nil then pcall(function() local st = db.storage[id]; if st ~= nil then sch = tostring(st.active_section) end end) end
					local prof = "?"
					pcall(function() prof = se:profile_name() end)
					local alive = true
					pcall(function() alive = se:alive() end)
					rows[#rows + 1] = { d = d, id = id, name = se:name(), sec = se:section_name(), prof = prof, job = jobs[id] or "-", sch = sch, on = (lo ~= nil), alive = alive, pos = pos }
				end
			end
		end
	end
	table.sort(rows, function(a, b) return a.d < b.d end)
	local n15, n15on = 0, 0
	for _, r in ipairs(rows) do
		if r.d <= RADIUS and r.alive then
			n15 = n15 + 1
			if r.on then n15on = n15on + 1 end
		end
	end
	qa.event(string.format("FIRE %s within %dm: total=%d online=%d | village smart holds %d npcs", tag, RADIUS, n15, n15on, total_sm))
	for _, r in ipairs(rows) do
		qa.event(string.format("FIRE %s   d=%5.1f %-8s %-34s %-18s prof=%-22s job=%-40s scheme=%s pos=%.1f,%.1f,%.1f", tag, r.d, r.on and "online" or "offline", r.name, r.sec, r.prof, r.job, r.sch, r.pos.x, r.pos.y, r.pos.z))
	end
	return n15
end

qa.hooks.fire_count = function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l01_escape" then return end
	if t >= 5 and not S.logged_start then
		S.logged_start = true
		pcall(function() level.set_time_factor(5) end)
		pcall(function()
			local l = gulag_general.load_ltx("x")
			local a = string.find(l, "{!is_squad_commander} false, {=actor_has_weapon}", 1, true)
			local m = string.find(l, "[meet@generic_lager]", 1, true)
			qa.event("FIRE gulag_general ltx len=" .. tostring(#l) .. " base_use_line=" .. tostring(a ~= nil) .. " generic_lager=" .. tostring(m ~= nil))
		end)
		pcall(function()
			local i = debug.getinfo(gulag_general.load_job, "S")
			qa.event("FIRE gulag_general.load_job source=" .. tostring(i.source) .. " short=" .. tostring(i.short_src) .. " line=" .. tostring(i.linedefined))
		end)
		if lo ~= nil then
			local p = lo:position()
			qa.event(string.format("FIRE actor spawned at %.1f,%.1f,%.1f dist to fire %.1f", p.x, p.y, p.z, d3(p)))
		end
	end
	for _, st in ipairs(SAMPLES) do
		if t >= st and not S.done[st] then
			S.done[st] = true
			local ok, err = pcall(function() census("t=" .. st) end)
			if not ok then qa.event("FIRE census error " .. tostring(err)) end
		end
	end
	-- godmode
	for id, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then v.health = 1 end end
	-- teleport next to the fire and look at it, then screenshots
	if t >= 100 and not S.tp then
		S.tp = true
		for id, v in pairs(db.mp_actors or {}) do
			if v ~= nil and v:alive() then
				local tx, ty, tz = FIRE.x + (tonumber(qa.cfg.sx) or 3.0), FIRE.y + 0.5, FIRE.z + (tonumber(qa.cfg.sz) or 7.0)
				local ok, err = pcall(function() v:set_actor_position(vector():set(tx, ty, tz)) end)
				qa.event("FIRE teleport " .. tostring(ok) .. " " .. tostring(err))
				pcall(function() v:set_actor_direction(-math.atan2(FIRE.x - tx, FIRE.z - tz)) end)
				S.tp_t = t
			end
		end
	end
	if S.tp_t ~= nil then
		for i, dt in ipairs({ 6, 12 }) do
			if t >= S.tp_t + dt and not S.shot[i] then
				S.shot[i] = true
				-- close the lobby / message box overlay of the harness player, then ask the harness for an engine screenshot
				pcall(function()
					for _ = 1, 4 do
						local r = level.main_input_receiver()
						if r ~= nil then level.start_stop_menu(r, true) end
					end
				end)
				pcall(function()
					local f = io.open(getFS():update_path("$logs$", "qa_cmd.txt"), "a")
					if f then f:write("screenshot", string.char(10)); f:close() end
				end)
				qa.event("FIRE screenshot " .. i)
			end
		end
	end
	if t >= FINAL and not S.fin then
		S.fin = true
		pcall(function() census("t=final") end)
		qa.event("FIRE done")
	end
end
