-- Whole-level stalker census (test only, never shipped): every stalker/trader on Cordon with alive flag, smart terrain, job, scheme and position.
-- NEAR summary: living stalkers within 25 m (x,z) of the technician house (-219.1, -165.2); change cx/cz/radius in this file.
-- Run (listen mode): run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Hooks all_stalkers.lua -ExtraDir <stage>\gamedata -SoakSeconds 200
-- Lines go to qa_events.log: "ALL t=<s> ...".
local SAMPLES = { 60, 150, 270, 390 }  -- seconds after spawn
local S = { done = {} }

local function census(tag)
	local sim = alife()
	local info_by_id, smart_by_id = {}, {}
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil and se.npc_info ~= nil and se.job_data ~= nil then
			for nid, info in pairs(se.npc_info) do
				local sec = "?"
				pcall(function()
					if info.job_id ~= nil and info.job_id >= 0 and se.job_data[info.job_id] ~= nil then sec = se.job_data[info.job_id].section end
				end)
				info_by_id[nid] = sec
				smart_by_id[nid] = se:name()
			end
		end
	end
	local cx, cz, rad = tonumber(qa.cfg.cx) or -219.1, tonumber(qa.cfg.cz) or -165.2, tonumber(qa.cfg.radius) or 30
	local n, near = 0, 0
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil then
			local isst = false
			pcall(function() isst = (se:clsid() == clsid.script_stalker or se:clsid() == clsid.script_trader) end)
			if isst then
				local ok, lname = pcall(function() return sim:level_name(game_graph():vertex(se.m_game_vertex_id):level_id()) end)
				if ok and lname == "coop_l01_escape" then
					local lo = level.object_by_id(id)
					local pos = se.position
					if lo ~= nil then pos = lo:position() end
					local alive = true
					pcall(function() alive = se:alive() end)
					local sch = "-"
					if lo ~= nil then pcall(function() local st = db.storage[id]; if st ~= nil then sch = tostring(st.active_section) end end) end
					n = n + 1
					local vis = "?"
					if lo ~= nil then pcall(function() vis = tostring(lo:get_visual_name()) end) end
					local d = 0
					if cx ~= nil and cz ~= nil then
						d = math.sqrt((pos.x - cx) ^ 2 + (pos.z - cz) ^ 2)
						if d <= rad and alive then near = near + 1 end
					end
					qa.event(string.format("ALL %s %-34s %-24s %s %-8s smart=%-22s job=%-42s scheme=%-40s pos=%.1f,%.1f,%.1f d=%.1f vis=%s", tag, se:name(), se:section_name(), alive and "alive" or "DEAD ", lo and "online" or "offline", tostring(smart_by_id[id]), tostring(info_by_id[id]), sch, pos.x, pos.y, pos.z, d, vis))
				end
			end
		end
	end
	qa.event(string.format("ALL %s total=%d near(%s,%s r=%s)=%d", tag, n, tostring(cx), tostring(cz), tostring(rad), near))
end

qa.hooks.all_stalkers = function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l01_escape" then return end
	for _, st in ipairs(SAMPLES) do
		if t >= st and not S.done[st] then
			S.done[st] = true
			local ok, err = pcall(function() census("t=" .. st) end)
			if not ok then qa.event("ALL census error " .. tostring(err)) end
		end
	end
	for id, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then v.health = 1 end end
end
