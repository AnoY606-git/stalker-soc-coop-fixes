-- TEST ONLY (never shipped): run_coop.ps1 hooks for patches/stash_markers. Appended after qa_harness.lua.
-- Server client (role A, OnServer) drives; both clients assert the map spot.
local SID = "esc_secret_bridge_vagon"

local function box_flag_id()
	for k, v in pairs(story_flags.story_flags) do
		if v == true then
			local id = string.match(k, "^QA_STASH_BOX_(%d+)$")
			if id then return tonumber(id) end
		end
	end
	return nil
end

local function spot(id)
	local ok, r = pcall(level.map_has_object_spot, id, "treasure")
	return ok and r ~= nil and r ~= false and r ~= 0
end

qa.once("stash_markers", function(t, lo)
	if _G.stash_hook_ran then return end
	_G.stash_hook_ran = true
	local server = OnServer()
	if server then
		qa.assert("stash data loaded", stash_markers_data ~= nil and #stash_markers_data.stashes == 213, tostring(stash_markers_data and #stash_markers_data.stashes))
		qa.assert("treasure_manager override active", stash_markers.is_stash(SID), "is_stash")
		qa.eventually("server registered the stash box with items", function()
			local n = stash_markers.item_count(SID)
			return n ~= nil and n > 0, "items=" .. tostring(n)
		end, 40)
		qa.eventually("motivator use_callback wrapped", function() return stash_markers.hooked(), "hooked" end, 40)
		-- phase 1: give
		qa.eventually("give sets state given", function()
			if stash_markers.state(SID) == "unknown" then stash_markers.give(SID) end
			return stash_markers.state(SID) == "given", stash_markers.state(SID)
		end, 60)
		qa.eventually("server has the map spot", function()
			local b = stash_markers.box_of(SID)
			if b and not story_flags.has_flag("QA_STASH_BOX_" .. b) then story_flags.give_flag("QA_STASH_BOX_" .. b) end
			return stash_markers.spot_present(SID), "box=" .. tostring(b)
		end, 60)
	end
	-- every client: spot visible (B learns the box id from a flag)
	local seen_at = nil
	qa.eventually("client " .. tostring(qa.cfg.role) .. " sees the map spot", function()
		local b = box_flag_id()
		if not b then return false, "no box id yet" end
		if spot(b) then seen_at = seen_at or time_global() return true, "box " .. b end
		return false, "no spot for box " .. b
	end, 90)
	-- phase 2 (server): once both clients had time to see it, loot it
	if server then
		local started = time_global()
		qa.eventually("loot empties the box and marks it looted", function()
			if time_global() - started < 25000 then return false, "waiting for clients" end
			if stash_markers.state(SID) == "given" then
				if not qa._looted then qa._looted = stash_markers.loot(SID) end
			end
			return stash_markers.state(SID) == "looted", "state=" .. stash_markers.state(SID) .. " released=" .. tostring(qa._looted)
		end, 120)
		qa.eventually("server spot removed after loot", function()
			return stash_markers.state(SID) == "looted" and not stash_markers.spot_present(SID), "present=" .. tostring(stash_markers.spot_present(SID))
		end, 60)
		-- corpse roll on live stalkers (forced roll)
		qa.eventually("corpse search can give a stash", function()
			for id, s in pairs(db.storage) do
				local o = s.object
				if o and o.character_community and o:clsid() == clsid.script_stalker then
					local ok, r = pcall(stash_markers.on_corpse_use, o, nil, 100)
					if ok and r then return true, "gave " .. tostring(r) .. " via npc " .. tostring(o:name()) end
				end
			end
			return false, "no stalker gave one"
		end, 60)
	end
	qa.eventually("client " .. tostring(qa.cfg.role) .. " map spot removed after loot", function()
		local b = box_flag_id()
		if not b then return false, "no box id" end
		return story_flags.has_flag("STASH_D_" .. string.upper(SID)) and not spot(b), "D=" .. tostring(story_flags.has_flag("STASH_D_" .. string.upper(SID))) .. " spot=" .. tostring(spot(b))
	end, 150)
end)
