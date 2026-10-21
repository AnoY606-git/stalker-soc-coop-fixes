--@qa_lib
-- Cordon opening test (test only): spawn place, facing, Sidorovich online, tasks + descriptions, talk window with the SoC start phrase.
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("OPEN " .. s) end

local function sid_obj()
	return safe(function()
		for id = 1, 65534 do
			local o = level.object_by_id(id)
			if o ~= nil and string.find(o:name(), "esc_smart_terrain_1_trader_sidorovich", 1, true) then return o end
		end
	end)
end

local function report(tag)
	local lo = L.local_player()
	if lo == nil then ev(tag .. " no local player") return end
	local sid = sid_obj()
	local p = lo:position()
	local d = lo:direction()
	local line = string.format("%s pos=%.1f,%.1f,%.1f dir=%.2f,%.2f lobby=%s", tag, p.x, p.y, p.z, d.x, d.z, tostring(safe(game.IsLobbyStage)))
	if sid ~= nil then
		local sp = sid:position()
		local dx, dz = sp.x - p.x, sp.z - p.z
		local len = math.sqrt(dx * dx + dz * dz)
		local dot = (dx * d.x + dz * d.z) / math.max(len, 0.001) / math.max(math.sqrt(d.x * d.x + d.z * d.z), 0.001)
		line = line .. string.format(" sidor_dist=%.2f facing_dot=%.2f sidor_visual=%s", len, dot, tostring(safe(function() return sid:get_visual_name() end)))
	else
		line = line .. " sidor=not online"
	end
	ev(line)
end

local function flagline(tag)
	local names = { "COOP_SOC_OPENING_TALKED", "ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO", "ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_TALK_TO_THE_WOLF_STOP_DIALOG_INFO" }
	local out = {}
	for _, n in ipairs(names) do out[#out + 1] = n .. "=" .. tostring(safe(story_flags.has_flag, n)) end
	local lo = L.local_player()
	local tk = {}
	for _, id in ipairs({ "esc_start_main_quest_task", "esc_start_talk_to_the_sidorovich_quest_task", "esc_start_find_stalker_shustry_quest_task", "esc_start_talk_to_the_wolf_quest_task" }) do
		local t = lo and safe(function() return lo:get_task(id, true) end)
		tk[#tk + 1] = id .. ":" .. (t ~= nil and ("yes state=" .. tostring(safe(function() return t:get_state() end))) or "no")
	end
	ev(tag .. " FLAGS " .. table.concat(out, " ") .. " TASKS " .. table.concat(tk, " | "))
end

qa.once("open_run", function(t, lo)
	L.task("open", {
		function(c) return L.wait(8) end,
		function(c) report("T+8s"); flagline("before"); return L.screenshot("w2_spawn") end,
		function(c) return L.open_talk("esc_smart_terrain_1_trader_sidorovich", { shot = "w2_talk1" }) end,
		function(c, ok, why, shot) ev("open_talk ok=" .. tostring(ok) .. " " .. tostring(why)); ev("talk_ready"); return L.wait(5) end,
		function(c) return L.screenshot("w2_talk_after_key1") end,
		function(c) return L.wait(6) end,
		function(c) flagline("mid"); return L.screenshot("w2_talk_after_key2") end,
		function(c) return L.wait(6) end,
		function(c) return L.screenshot("w2_talk_after_key3") end,
		function(c) return L.wait(6) end,
		function(c) return L.screenshot("w2_talk_after_key4") end,
		function(c) return L.wait(4) end,
		function(c)
			local talking = safe(function() return L.local_player():is_talking() end)
			ev("after dialog is_talking=" .. tostring(talking))
			qa.assert("opening dialog ends by itself (talk window closed after the last phrase)", talking == false, tostring(talking))
			flagline("after")
			qa.assert("opening dialog sets COOP_SOC_OPENING_TALKED", safe(story_flags.has_flag, "COOP_SOC_OPENING_TALKED") == true)
			qa.assert("opening dialog completes the talk task flag", safe(story_flags.has_flag, "ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO") == true)
			return L.wait(8)
		end,
		function(c) flagline("after+8"); return L.open_talk("esc_smart_terrain_1_trader_sidorovich", { shot = "w2_talk_again" }) end,
		function(c, ok, why) ev("open_talk again ok=" .. tostring(ok)); return L.wait(2) end,
		function(c) L.close_talk(); return L.done(true) end,
	})
end)
-- probe of the Cordon start (test only): where is each player over time, tasks + descriptions, scene flags, Sidorovich state.
-- lines: "PROBE ..." in qa_events.log of every client (role S = dedicated server).
local SHOTS = { [95] = true }
local TASKS = { "esc_start_main_quest_task", "esc_start_talk_to_the_sidorovich_quest_task", "esc_start_find_stalker_shustry_quest_task", "esc_start_talk_to_the_wolf_quest_task" }
local BUNK = { -247.30, -24.96, -133.40 }
local last_flags = ""

local function safe(f, ...)
	local ok, r = pcall(f, ...)
	if ok then return r end
	return nil
end

qa.hooks.probe = function(t, lo)
	t = math.floor(t)
	if t > 130 then return end
	local side = safe(OnServer) and "srv" or "cli"
	if lo ~= nil then
		local p = lo:position()
		local dl = math.sqrt((p.x - 105) ^ 2 + (p.z + 9.8) ^ 2)
		local db_ = math.sqrt((p.x - BUNK[1]) ^ 2 + (p.y - BUNK[2]) ^ 2 + (p.z - BUNK[3]) ^ 2)
		qa.event(string.format("PROBE t=%d %s name=%s sec=%s pos=%.1f,%.1f,%.1f d_lobby=%.1f d_bunker=%.1f hp=%s", t, side, tostring(safe(function() return lo:name() end)), lo:section(), p.x, p.y, p.z, dl, db_, tostring(safe(function() return lo.health end))))
	end
	-- Sidorovich
	local sid = safe(function() for id = 1, 65534 do local o = level.object_by_id(id); if o ~= nil and string.find(o:name(), "esc_smart_terrain_1_trader_sidorovich", 1, true) then return o end end end)
	if t == 5 or t == 20 or t == 40 then
		safe(function()
			if not OnServer() then return end
			for id = 0, 65534 do
				local se = alife():object(id)
				if se ~= nil and (string.find(se:name(), "start_main_quest_task_space_restrictor", 1, true) or string.find(se:name(), "esc_smart_terrain_1_trader_sidorovich", 1, true)) then
					local o = level.object_by_id(id)
					local sec = o and safe(function() return db.storage[id].active_section end)
					qa.event(string.format("PROBE t=%d SE %s id=%d pos=%.1f,%.1f,%.1f online=%s section=%s", t, se:name(), id, se.position.x, se.position.y, se.position.z, tostring(o ~= nil), tostring(sec)))
				end
			end
		end)
	end
	if sid ~= nil and (t % 5 == 0) then
		local sp = sid:position()
		qa.event(string.format("PROBE t=%d %s SIDOR pos=%.1f,%.1f,%.1f vis=%s scheme=%s", t, side, sp.x, sp.y, sp.z, tostring(safe(function() return sid:get_visual_name() end)), tostring(safe(function() return db.storage[sid:id()].active_section end))))
	elseif sid == nil and (t % 10 == 0) then
		qa.event("PROBE t=" .. t .. " " .. side .. " SIDOR not online")
	end
	-- tasks (client has the PDA)
	if lo ~= nil and (t % 5 == 0) then
		for _, id in ipairs(TASKS) do
			local tk = safe(function() return lo:get_task(id, true) end)
			if tk ~= nil then
				qa.event(string.format("PROBE t=%d %s TASK %s state=%s title=[%s] descr=[%s]", t, side, id, tostring(safe(function() return tk:get_state() end)),
					tostring(safe(function() return game.translate_string(tk:get_title()) end)), tostring(safe(function() return game.translate_string(tk:get_description()) end))))
			end
		end
	end
	-- scene flags
	local sf = safe(function() return story_flags.story_flags end)
	if type(sf) == "table" then
		local out = {}
		for k, v in pairs(sf) do
			if v == true and (string.sub(k, 1, 4) == "SCN_" or string.sub(k, 1, 4) == "ESC_") then out[#out + 1] = k end
		end
		table.sort(out)
		local s = table.concat(out, " ")
		if s ~= last_flags then
			last_flags = s
			qa.event("PROBE t=" .. t .. " " .. side .. " FLAGS " .. s)
		end
	end
	if SHOTS[t] and not safe(IsDedicatedServer) then
		pcall(function() get_console():execute("screenshot jpg") end)
		qa.event("PROBE t=" .. t .. " screenshot")
	end
end
