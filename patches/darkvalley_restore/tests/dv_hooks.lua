-- Dark Valley restore hooks (test only). Appended after qa_harness.lua. Server asserts land in the dedicated server's qa_assert.log.
if not _G.__dv_boot then
	_G.__dv_boot = true
	pcall(function() coop_scenes.install() end)   -- the Scene Director (cutscenes_core) loads coop_scn_*.script, incl. coop_scn_valley_restore
end

local function sim_objects()
	local out = {}
	for id = 0, 65534 do
		local ok, o = pcall(function() return alife():object(id) end)
		if ok and o ~= nil then out[#out + 1] = o end
	end
	return out
end

local function dist2(a, b)
	local dx, dz = a.x - b.x, a.z - b.z
	return math.sqrt(dx * dx + dz * dz)
end

-- ===== server =====
qa.once("dv_server", function(t, lo)
	if not OnServer() then return end
	local lname = level.name()
	qa.event("dv_server on level " .. tostring(lname))
	if lname ~= "coop_l04_darkvalley" then return end

	qa.eventually("DV door val_door_trader released", function()
		local d = alife():object("val_door_trader")
		local st = tostring(coop_scn_valley_restore and coop_scn_valley_restore.status())
		return d == nil and string.find(st, "door_found=true") ~= nil, "door object " .. tostring(d) .. " | " .. st
	end, 120)

	qa.eventually("DV entrance box has the SoC stash items", function()
		local box = alife():object("val_equipment_box_01_case_0005")
		if box == nil then return false, "box missing" end
		local n, per = 0, {}
		for _, o in ipairs(sim_objects()) do
			if o.parent_id == box.id then n = n + 1; per[o:section_name()] = (per[o:section_name()] or 0) + 1 end
		end
		local s = ""
		for k, v in pairs(per) do s = s .. k .. "=" .. v .. " " end
		return n >= 8, "children " .. n .. " : " .. s .. " at " .. string.format("%.1f %.1f %.1f", box.position.x, box.position.y, box.position.z)
	end, 120)

	qa.eventually("DV X18 entrance bandit squad exists", function()
		local board = sim_board.get_sim_board()
		local smart = board.smarts_by_names["val_smart_terrain_17"]
		if smart == nil then return false, "smart 17 missing" end
		local sq, members = 0, 0
		local info = ""
		for id, sqd in pairs(board.smarts[smart.id].squads) do
			info = info .. tostring(sqd:section_name()) .. "(" .. tostring(sqd.squad_npc and 0 or 0) .. ") "
			if sqd:section_name() == "val_smart_terrain_17_bandit_1_squad" then
				sq = sq + 1
				for k in sqd:squad_members() do members = members + 1 end
			end
		end
		return sq >= 1 and members >= 5, "squads here: " .. info .. " bandit squads " .. sq .. " members " .. members
	end, 150)

	-- the three post-X18 military squads must still fit next to the bandits (job slot safety): create them and watch for a crash
	qa.eventually("DV military squads can join bandits at terrain 17", function()
		if not qa.dv_mil then
			qa.dv_mil = true
			for _, id in ipairs({ "val_smart_terrain_17_military_1_squad", "val_smart_terrain_17_military_2_squad", "val_smart_terrain_17_military_3_squad" }) do
				local ok, e = pcall(xr_effects.create_squad, nil, nil, { id, "val_smart_terrain_17" })
				qa.event("create_squad " .. id .. " " .. tostring(ok) .. " " .. tostring(e))
			end
			qa.dv_mil_t = time_global()
		end
		return time_global() - qa.dv_mil_t > 25000, "waited"
	end, 80)
end)

-- ===== client: gauss price, transition object, screenshot at the entrance =====
qa.once("dv_client", function(t, lo)
	if OnServer() or lo == nil then return end
	if level.name() ~= "coop_l04_darkvalley" then return end
	local m = lo:money()
	local r1 = dialogs_val_restore.if_actor_has_money_800(nil, nil)
	qa.assert("gauss precondition matches money>=800", r1 == (m >= 800), "money " .. m .. " fn " .. tostring(r1))
	local s = game.translate_string("val_smart_terrain_15_stalker_scammer_start_dialog_0")
	qa.assert("gauss offer text says eight hundred / 800", (string.find(s, "eight hundred") ~= nil) or (string.find(s, "800") ~= nil), s)
end)


-- news recorder (client): which tips reach the local player
if not _G.__dv_tips then
	_G.__dv_tips = {}
	local ok = pcall(function()
		local orig = news_manager.send_tip
		news_manager.send_tip = function(actor, news_id, timeout, sender, showtime, sender_id)
			_G.__dv_tips[#_G.__dv_tips + 1] = tostring(news_id) .. "|" .. tostring(sender)
			return orig(actor, news_id, timeout, sender, showtime, sender_id)
		end
	end)
	qa_tip_hook_ok = ok
end

local function has_tip(id)
	for _, v in ipairs(_G.__dv_tips) do if string.find(v, id, 1, true) then return true, v end end
	return false
end

-- ===== server: transition object exists =====
qa.once("dv_server2", function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l04_darkvalley" then return end
	qa.eventually("DV level changer val_esc_level_changer exists at the south gate", function()
		local c = alife():object("val_esc_level_changer")
		if c == nil then return false, "missing" end
		local p = c.position
		return math.abs(p.x + 44.6) < 1 and math.abs(p.z + 548.8) < 1, string.format("clsid %s pos %.1f %.1f %.1f story %s", tostring(c:clsid()), p.x, p.y, p.z, tostring(c.m_story_id))
	end, 60)
	qa.eventually("DV story object val_esc_level_changer registered", function()
		local id = get_story_object_id("val_esc_level_changer")
		return id ~= nil and id ~= 65535, tostring(id)
	end, 60)
end)

-- ===== raid chain: run the REAL condlist of the restrictor (its ltx line) on the client; the harness actor is not on the DV level for ALife (gv of Cordon),
-- so the restrictor object itself never goes online in this harness.
qa.once("dv_raid_cl", function(t, lo)
	if OnServer() or lo == nil then return end
	if level.name() ~= "coop_l04_darkvalley" then return end
	local ini = ini_file([[scripts\coop_l04_darkvalley\space_restrictors\x18_start_get_out_of_the_lab_quest_task_space_restrictor.ltx]])
	local sec = "sr_idle@x18_start_get_out_of_the_lab_quest_task_end"
	qa.assert("restrictor ltx has the end section", ini:section_exist(sec), sec)
	qa.event("sections: logic=" .. tostring(ini:section_exist("logic")) .. " idle=" .. tostring(ini:section_exist("sr_idle@x18_start_get_out_of_the_lab_quest_task_idle")) .. " nil=" .. tostring(ini:section_exist("sr_idle@nil")))
	if not ini:section_exist(sec) then return end
	local line = ini:r_string(sec, "on_actor_inside")
	qa.event("condlist line: " .. tostring(line))
	local cl = xr_logic.parse_condlist(nil, sec, "on_actor_inside", line)
	local res = xr_logic.pick_section_from_condlist(lo, nil, cl)
	qa.event("condlist result section: " .. tostring(res))
	qa.eventually("DV raid: trader tip reached the player", function()
		local ok2, v = has_tip("st_val_monolith_trader_pda1")
		return ok2, tostring(v) .. " all=" .. table.concat(_G.__dv_tips, ",")
	end, 30)
	qa.eventually("DV raid: VAL_RAID_START flag", function() return story_flags.has_flag("VAL_RAID_START"), "" end, 30)
	qa.eventually("DV raid: X18_START_GET_OUT flag", function() return story_flags.has_flag("X18_START_GET_OUT_OF_THE_LAB_QUEST_TASK_INFO"), "" end, 30)
	qa.eventually("DV raid: task get-out-via-south-gate given", function()
		local tk = lo:get_task("val_start_get_out_via_south_gate_quest_task", true)
		return tk ~= nil, "task object " .. type(tk)
	end, 30)
	qa.eventually("DV raid: Barman document task still given", function()
		local tk = lo:get_task("val_start_take_the_documents_to_the_barmen_quest_task", true)
		return tk ~= nil, "task object " .. type(tk)
	end, 30)
	-- the Cordon follow-up task is created by the first one's completion condlist
	qa.eventually("DV raid: south-gate task target is the new level changer", function()
		local tk = lo:get_task("val_start_get_out_via_south_gate_quest_task", true)
		if tk == nil then return false, "no task" end
		return true, "task present, target story id " .. tostring(tk:get_id())
	end, 30)
	pcall(function() get_console():execute("screenshot") end)
end)
