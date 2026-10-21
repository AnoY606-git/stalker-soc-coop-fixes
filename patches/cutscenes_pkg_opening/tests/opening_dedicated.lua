-- dedicated server + 2 clients: where does each client spawn, does each client get the start tasks (with text), does the server survive
local function safe_(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
qa.once("ded_asserts", function(t, lo)
	if OnServer() then return end
	local function has_task(id)
		local l = qa.local_object()
		return l ~= nil and safe_(function() return l:get_task(id, true) end) ~= nil
	end
	qa.eventually("client has task esc_start_main_quest_task", function() return has_task("esc_start_main_quest_task"), "role " .. tostring(qa.cfg.role) end, 40)
	qa.eventually("client has task esc_start_talk_to_the_sidorovich_quest_task", function() return has_task("esc_start_talk_to_the_sidorovich_quest_task"), "role " .. tostring(qa.cfg.role) end, 40)
	qa.eventually("client spawned in the bunker", function()
		local l = qa.local_object()
		if l == nil then return false end
		local p = l:position()
		local d = math.sqrt((p.x + 247.3) ^ 2 + (p.z + 133.4) ^ 2)
		return d < 6, string.format("pos %.1f,%.1f,%.1f dist %.1f", p.x, p.y, p.z, d)
	end, 40)
end)
-- probe of the Cordon start (test only): where is each player over time, tasks + descriptions, scene flags, Sidorovich state.
-- lines: "PROBE ..." in qa_events.log of every client (role S = dedicated server).
local SHOTS = { [25] = true, [50] = true }
local TASKS = { "esc_start_main_quest_task", "esc_start_talk_to_the_sidorovich_quest_task", "esc_start_find_stalker_shustry_quest_task" }
local BUNK = { -247.30, -24.96, -133.40 }
local last_flags = ""

local function safe(f, ...)
	local ok, r = pcall(f, ...)
	if ok then return r end
	return nil
end

qa.hooks.probe = function(t, lo)
	t = math.floor(t)
	if t > 80 then return end
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
