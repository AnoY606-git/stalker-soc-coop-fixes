-- X18 restore hooks (test only). Appended after qa_harness.lua.
if not _G.__dv_boot then
	_G.__dv_boot = true
	pcall(function() coop_scenes.install() end)
end

local function sim_objects()
	local out = {}
	for id = 0, 65534 do
		local ok, o = pcall(function() return alife():object(id) end)
		if ok and o ~= nil then out[#out + 1] = o end
	end
	return out
end

-- ===== server =====
qa.once("x18_server", function(t, lo)
	if not OnServer() then return end
	local lname = level.name()
	qa.event("x18_server on level " .. tostring(lname))
	if lname ~= "coop_l04_x18" then return end

	qa.eventually("X18 snork squad at terrain 4_m (2 snorks)", function()
		local board = sim_board.get_sim_board()
		local smart = board.smarts_by_names["x18_smart_terrain_4_m"]
		if smart == nil then return false, "smart 4_m missing" end
		local info, snorks, polters = "", 0, 0
		for id, sqd in pairs(board.smarts[smart.id].squads) do
			info = info .. tostring(sqd:section_name()) .. " "
			for k in sqd:squad_members() do
				local s = k.object:section_name()
				info = info .. "[" .. s .. "] "
				if string.find(s, "snork") then snorks = snorks + 1 end
				if string.find(s, "poltergeist") then polters = polters + 1 end
			end
		end
		return snorks >= 2 and polters == 0, "squads: " .. info .. " snorks " .. snorks .. " polters " .. polters
	end, 150)

	qa.eventually("X18 other poltergeist terrains keep their squads (1_m, 2_m, 3_m)", function()
		local board = sim_board.get_sim_board()
		local n, info = 0, ""
		for _, nm in ipairs({ "x18_smart_terrain_1_m", "x18_smart_terrain_2_m", "x18_smart_terrain_3_m" }) do
			local smart = board.smarts_by_names[nm]
			if smart ~= nil then
				for id, sqd in pairs(board.smarts[smart.id].squads) do n = n + 1; info = info .. nm .. ":" .. tostring(sqd:section_name()) .. " " end
			end
		end
		return n >= 3, info
	end, 150)

	-- poltergeist corpse: create one next to the player, kill it, it must stay in the world (stock: released in death_callback)
	qa.pg = { stage = 0 }
	qa.eventually("X18 poltergeist leaves a corpse after death", function()
		local P = qa.pg
		if P.stage == 0 then
			local actor
			if type(db.mp_actors) == "table" then for id, v in pairs(db.mp_actors) do actor = v break end end
			if actor == nil then return false, "no actor yet" end
			local ok, e = pcall(function()
				local ap = actor:position()
				local pos = vector():set(ap.x + 4, ap.y, ap.z)
				local se = alife():create("m_poltergeist_normal_tele", pos, actor:level_vertex_id(), actor:game_vertex_id())
				P.id = se.id
			end)
			qa.event("poltergeist create " .. tostring(ok) .. " " .. tostring(e) .. " id " .. tostring(P.id))
			if not ok then return false, "create failed " .. tostring(e) end
			P.stage = 1
			P.t = time_global()
			return false, "created id " .. tostring(P.id)
		elseif P.stage == 1 then
			local o = level.object_by_id(P.id)
			if o ~= nil and o:alive() then
				local ok, e = pcall(function() o:kill(o) end)
				qa.event("poltergeist kill " .. tostring(ok) .. " " .. tostring(e))
				P.stage = 2
				P.t = time_global()
				return false, "killed"
			end
			return false, "waiting online, online=" .. tostring(o ~= nil)
		elseif P.stage == 2 then
			if time_global() - P.t < 8000 then return false, "waiting after death" end
			local se = alife():object(P.id)
			local o = level.object_by_id(P.id)
			local alive = nil
			if o ~= nil then alive = o:alive() end
			return (se ~= nil and o ~= nil and not alive), "se=" .. tostring(se ~= nil) .. " online=" .. tostring(o ~= nil) .. " alive=" .. tostring(alive)
		end
	end, 100)
end)

-- ===== client: ambient weather =====
qa.once("x18_client", function(t, lo)
	if OnServer() or lo == nil then return end
	if level.name() ~= "coop_l04_x18" then return end
	local w = tostring(level.get_weather())
	qa.assert("X18 weather is x18_ambient", string.find(w, "x18_ambient") ~= nil, "weather " .. w)
	local ini = ini_file("environment\\weathers\\x18_ambient.ltx")
	local ok, a = pcall(function() return ini:r_string("00:00:00", "ambient") end)
	qa.assert("x18_ambient.ltx ambient = ambient_env_x18", ok and a == "ambient_env_x18", tostring(a))
	local amb = ini_file("environment\\ambients.ltx")
	local ok2, ch = pcall(function() return amb:r_string("ambient_env_x18", "sound_channels") end)
	qa.assert("ambient_env_x18 uses the SoC x18 sound channel", ok2 and ch == "ambient_env_x18_shoc_snd", tostring(ch))
end)
