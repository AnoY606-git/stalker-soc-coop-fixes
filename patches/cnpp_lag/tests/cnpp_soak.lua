-- Hook "cnpp_soak": travel Cordon -> Sarcophagus (guide flag + vote), stand near the three "no gravity" corpses and log a METRIC line
-- every 10 s on the server and on each client (qa_events.log): frame time (min/avg/max, frames over 50/100 ms), Lua KB, online objects,
-- alife objects (server), hit_obj calls (server), corpse positions.
-- Run: run_coop.ps1 -Map coop_l01_escape -Cfg no_respawn=1 -Hooks cnpp_soak.lua -ExtraDir <stage>\gamedata -SoakSeconds 600
local CORPSES = { "sar_no_gravity_stalker_monolith_1_1", "sar_no_gravity_stalker_monolith_1_2", "sar_no_gravity_stalker_zombied_2_gasballoon_1" }
local S = { phase = "wait", hits = 0, hits_ng = 0, wrapped = false, fr = nil, last_m = 0, tp_at = nil, arrive = nil, vote_at = nil }

local function frame_tick()
	local now = time_global()
	local f = S.fr
	if f == nil then S.fr = { last = now, n = 0, sum = 0, max = 0, min = 1e9, o50 = 0, o100 = 0 } return false end
	local dt = now - f.last
	f.last = now
	f.n = f.n + 1
	f.sum = f.sum + dt
	if dt > f.max then f.max = dt end
	if dt < f.min then f.min = dt end
	if dt > 50 then f.o50 = f.o50 + 1 end
	if dt > 100 then f.o100 = f.o100 + 1 end
	return false
end

local function wrap_hits()
	if S.wrapped then return end
	S.wrapped = true
	local ok, err = pcall(function()
		local orig = xr_effects.hit_obj
		xr_effects.hit_obj = function(actor, npc, p)
			S.hits = S.hits + 1
			if p and p[1] and string.find(tostring(p[1]), "sar_no_gravity", 1, true) then S.hits_ng = S.hits_ng + 1 end
			return orig(actor, npc, p)
		end
	end)
	qa.event("METRIC wrap hit_obj " .. (ok and "ok" or tostring(err)))
end

local function counts(server)
	local online, alife_n = 0, 0
	for i = 1, 65534 do
		if level.object_by_id(i) ~= nil then online = online + 1 end
	end
	if server and alife() ~= nil then
		for i = 1, 65534 do
			if alife():object(i) ~= nil then alife_n = alife_n + 1 end
		end
	end
	return online, alife_n
end

local function corpse_info(server)
	local out = {}
	for _, nm in ipairs(CORPSES) do
		local so = nil
		if server and alife() ~= nil then pcall(function() so = alife():object(nm) end) end
		local lo = nil
		if so ~= nil then pcall(function() lo = level.object_by_id(so.id) end) end
		if so ~= nil then
			local p = so.position
			out[#out + 1] = string.format("%s=%s@%.1f,%.1f,%.1f", string.sub(nm, 17), lo and "on" or "off", p.x, p.y, p.z)
		end
	end
	return table.concat(out, " ")
end

local function metric(role, server)
	local f = S.fr
	if f == nil or f.n == 0 then return end
	local online, alife_n = counts(server)
	local lvl = tostring(level.name())
	qa.event(string.format("METRIC role=%s lvl=%s t=%.0f frames=%d avg_ms=%.1f min=%d max=%d o50=%d o100=%d luaKB=%.0f online=%d alife=%d hits=%d hits_ng=%d | %s",
		role, lvl, time_global() / 1000, f.n, f.sum / f.n, f.min, f.max, f.o50, f.o100, collectgarbage("count"), online, alife_n, S.hits, S.hits_ng, corpse_info(server)))
	S.fr = { last = time_global(), n = 0, sum = 0, max = 0, min = 1e9, o50 = 0, o100 = 0 }
end

qa.hooks.cnpp_soak = function(t, lo)
	if not S.tick_added then
		S.tick_added = true
		pcall(function() level.add_call(frame_tick, function() end) end)
	end
	local server = OnServer()
	local role = tostring(qa.cfg.role)
	local lvl = level.name()
	if server then wrap_hits() end
	if server and lvl == "coop_l01_escape" and S.phase ~= "voted" then
		local alive = 0
		for id, v in pairs(db.mp_actors) do if v ~= nil and v:alive() then alive = alive + 1 end end
		if alive >= (tonumber(qa.cfg.clients or "2") or 2) then
			if S.phase == "wait" then
				S.vote_at = time_global()
				S.phase = "flag"
				story_flags.give_flag("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_SAR_INFO")
				qa.event("METRIC travel: flag given")
			elseif S.phase == "flag" and time_global() - S.vote_at > 4000 then
				for id, v in pairs(db.mp_actors) do if v ~= nil and v:alive() then coop_map_vote.on_yes(id) end end
				S.phase = "voted"
				qa.event("METRIC travel: voted yes")
			end
		end
	end
	if lvl == "coop_l11_sarcofag" then
		if S.arrive == nil then S.arrive = time_global() end
		if server and S.tp_at == nil and time_global() - S.arrive > 15000 then
			S.tp_at = time_global()
			local so = nil
			pcall(function() so = alife():object(CORPSES[1]) end)
			if so == nil then
				qa.event("METRIC teleport: corpse object not found")
			else
				local p = so.position
				for id, v in pairs(db.mp_actors) do
					if v ~= nil and v:alive() then
						local ok, err = pcall(function() v:set_actor_position(vector():set(p.x + 2, p.y + 0.5, p.z)) end)
						qa.event("METRIC teleport actor " .. id .. " to corpse " .. string.format("%.1f,%.1f,%.1f", p.x, p.y, p.z) .. " " .. (ok and "ok" or tostring(err)))
					end
				end
			end
		end
		-- god mode (server): the Sarcophagus is hostile
		if server then for id, v in pairs(db.mp_actors) do if v ~= nil and v:alive() then v.health = 1 end end end
	end
	if time_global() - S.last_m >= 10000 then
		S.last_m = time_global()
		local ok, err = pcall(metric, role, server)
		if not ok then qa.event("METRIC error " .. tostring(err)) end
	end
end
