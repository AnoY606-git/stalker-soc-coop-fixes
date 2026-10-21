--@qa_lib
-- TEST ONLY (never shipped): run_coop.ps1 -Hooks for the safe-zone storage box markers of patches/stash_markers.
-- Listen host (-Mode listen, host is a player) or dedicated + client. Prints every spot and counts them per level.
--   Cordon direct :  run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 0 -Hooks <this file> ...
--   Garbage (Duty checkpoint) / Bar / Yantar / Army Warehouses through the party vote (starts on Cordon, travels, the check runs again on arrival):
--                    add  -Cfg safe_travel=bar   (or yan, mil, gar)
-- Log lines (qa_events.log): SAFEBOX <level> <name> id=<id> pos=x,y,z hint=<text> server_spot=<n>   and   SAFEBOX_COUNT ...
-- Asserts: the server found exactly the boxes the data lists for this level, each has a server spot, the object position equals the
-- data position, the spot is still there 20 s later (never removed, never duplicated), and every client (a listen host counts as one)
-- sees the same spots.
local L = qa_lib
local TYPE = "safe_box_location"
local EXPECT_POS_TOL = 0.6

local function spot_n(id)
	local ok, r = pcall(level.map_has_object_spot, id, TYPE)
	if not ok or r == nil or r == false then return 0 end
	if r == true then return 1 end
	return tonumber(r) or 0
end

local function published_ids()
	local ids = {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true then
			local id = string.match(k, "^QA_SBOX_(%d+)$")
			if id then ids[#ids + 1] = tonumber(id) end
		end
	end
	table.sort(ids)
	return ids
end

local function check_level()
	local lvl = level.name()
	local server = OnServer()
	local role = tostring(qa.cfg.role)
	local expected = stash_markers.safe_expected(lvl)
	qa.event("SAFEBOX_PLAN level=" .. lvl .. " role=" .. role .. " server=" .. tostring(server) .. " expected=" .. expected)

	if server then
		local seen_boxes = nil
		qa.eventually(lvl .. ": server has a spot on every safe box (" .. expected .. ")", function()
			local b = stash_markers.safe_boxes()
			local withspot = 0
			for _, x in ipairs(b) do if x.spot then withspot = withspot + 1 end end
			if #b == expected and withspot == expected then seen_boxes = b return true, "boxes=" .. #b .. " spots=" .. withspot end
			return false, "boxes=" .. #b .. " spots=" .. withspot .. " expected=" .. expected
		end, 90)
		-- publish ids for the clients, print every box
		qa.eventually(lvl .. ": box list printed, positions match the data", function()
			if not seen_boxes then return false, "waiting" end
			local bad = {}
			for _, x in ipairs(seen_boxes) do
				local se = alife():object(x.id)
				local px, py, pz = 0, 0, 0
				if se then px, py, pz = se.position.x, se.position.y, se.position.z end
				local d = math.sqrt((px - x.x) ^ 2 + (py - x.y) ^ 2 + (pz - x.z) ^ 2)
				if d > EXPECT_POS_TOL then bad[#bad + 1] = x.name .. " off by " .. string.format("%.1f", d) end
				local hint = game.translate_string("safe_box_hint_" .. x.key)
				qa.event(string.format("SAFEBOX %s %s id=%d pos=%.1f,%.1f,%.1f key=%s hint=%s server_spot=%d",
					lvl, x.name, x.id, px, py, pz, x.key, string.gsub(hint, "\n", " / "), spot_n(x.id)))
				story_flags.give_flag("QA_SBOX_" .. x.id)
			end
			qa.event("SAFEBOX_COUNT level=" .. lvl .. " boxes=" .. #seen_boxes .. " expected=" .. expected)
			return #bad == 0, #bad == 0 and "ok" or table.concat(bad, "; ")
		end, 30)
		-- never removed / duplicated: 20 s later every spot is still there and the count is exactly 1
		local t0 = nil
		qa.eventually(lvl .. ": spots still present once, 20 s later", function()
			if not seen_boxes then return false, "waiting" end
			t0 = t0 or time_global()
			if time_global() - t0 < 20000 then return false, "waiting 20 s" end
			local bad = {}
			for _, x in ipairs(seen_boxes) do
				local n = spot_n(x.id)
				if n ~= 1 then bad[#bad + 1] = x.name .. " n=" .. n end
			end
			return #bad == 0, #bad == 0 and "all 1" or table.concat(bad, "; ")
		end, 90)
	end

	-- every client (a listen host is one): the same spots
	qa.eventually(lvl .. ": client " .. role .. " sees all " .. expected .. " spots", function()
		local ids = published_ids()
		if #ids < expected then return false, "published ids " .. #ids .. "/" .. expected end
		local ok_n, miss = 0, {}
		for _, id in ipairs(ids) do
			if spot_n(id) >= 1 then ok_n = ok_n + 1 else miss[#miss + 1] = id end
		end
		if ok_n == #ids then
			qa.event("SAFEBOX_CLIENT level=" .. lvl .. " role=" .. role .. " sees " .. ok_n .. "/" .. #ids)
			return true, ok_n .. " spots"
		end
		return false, ok_n .. "/" .. #ids .. " missing " .. table.concat(miss, ",")
	end, 120)
end

qa.once("safe_box_markers", function(t, lo)
	if _G.safe_box_hook_ran then return end
	_G.safe_box_hook_ran = true
	qa.assert("safe_box_data loaded", safe_box_data ~= nil and #safe_box_data.boxes == 8, tostring(safe_box_data and #safe_box_data.boxes))
	check_level()

	-- optional travel (server / listen host, starts on Cordon): -Cfg safe_travel=bar|yan|mil
	local dest = qa.cfg.safe_travel
	if OnServer() and dest ~= nil and dest ~= "" and level.name() == "coop_l01_escape" then
		L.task("safe_box_travel", {
			function() return L.wait(45) end,  -- let the Cordon checks finish first (20 s stability window)
			function() return L.travel(dest, { timeout = 200, fallback = true }) end,
			function(c, ok, why) qa.assert("travel to " .. tostring(dest), ok == true, tostring(why)) end,
		})
	end
end)
