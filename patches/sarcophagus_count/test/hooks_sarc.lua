-- sarcophagus_count proof v2: travel Cordon -> Sarcophagus, then a 150 ms state machine (the harness server crashes ~7 s after the level loads, assign_RP)
local st = { travel = 0, tstage = 0 }
local S = { step = 0, done = {} }
local function ev(m) qa.event("[SC] " .. tostring(m)) end

local function members_of(sq) local n = 0 for k in sq:squad_members() do n = n + 1 end return n end

local function world(scan)
	local r = { members = 0, squads = 0, pre = 0, decoders = {} }
	local board = sim_board.get_sim_board()
	for id, sq in pairs(board.squads) do
		if sq.player_id == "monolith" then r.squads = r.squads + 1; r.members = r.members + members_of(sq) end
		local s = tostring(sq.settings_id)
		if string.find(s, "preacher", 1, true) or string.find(s, "fanatic", 1, true) then r.pre = r.pre + 1 end
	end
	for i = 0, (scan and 65534 or -1) do
		local o = alife():object(i)
		if o ~= nil then
			local sn = o:section_name()
			if string.find(sn, "preacher", 1, true) or string.find(sn, "fanatic", 1, true) then r.pre = r.pre + 1 end
			if sn == "dev_decoder" then table.insert(r.decoders, o) end
		end
	end
	return r
end

local function first_actor()
	for id, v in pairs(db.mp_actors or {}) do if v ~= nil then return id, v end end
end

local function machine()
	local ok, err = pcall(function()
		if not OnServer() or level.name() ~= "coop_l11_sarcofag" then return end
		local now = time_global()
		S.t0 = S.t0 or now
		local dt = (now - S.t0) / 1000
		if not S.census then
			local r = world(false)
			if r.members >= 22 then r = world(true) end
			if r.members >= 22 and #r.decoders >= 1 then
			S.census = true
			ev(string.format("census t=%.1f squads=%d members=%d pre=%d decoders=%d", dt, r.squads, r.members, r.pre, #r.decoders))
			qa.assert("SC ordinary Monolith before the door in band 20..30 (22 expected)", r.members >= 20 and r.members <= 30, "members=" .. r.members .. " squads=" .. r.squads)
			qa.assert("SC no preacher/fanatic squads or objects", r.pre == 0, "n=" .. r.pre)
			end
		end
		if S.step == 0 then
			if now - (S.lastscan or 0) < 400 then return end
			S.lastscan = now
			local r = world(true)
			if #r.decoders < 1 then return end
			ev(string.format("t=%.1f squads=%d members=%d pre=%d decoders=%d", dt, r.squads, r.members, r.pre, #r.decoders))
			qa.assert("SC level coop_l11_sarcofag loaded", level.name() == "coop_l11_sarcofag")
			qa.assert("SC preacher story id absent", get_story_object_id("sar_smart_terrain_17_monolith_preacher") == nil)
			qa.assert("SC exactly one dev_decoder item in the world", #r.decoders == 1, "n=" .. #r.decoders)
			local p = r.decoders[1].position
			-- a second harness pass after the level load can see the decoder already given to the actor by the first pass
			qa.assert("SC decoder at smart 17 spot", r.decoders[1].parent_id ~= 65535 or math.abs(p.y - 56) < 3 and math.abs(p.x - 23.8) < 10 and math.abs(p.z - 26.6) < 10, string.format("%.1f,%.1f,%.1f parent=%s", p.x, p.y, p.z, tostring(r.decoders[1].parent_id)))
			S.decoder = r.decoders[1]
			-- real arrival gives this task by completing the CNPP-1 task aes_1_start_go_to_sarcofag (not run when teleporting)
			local okt, errt = pcall(function() xr_effects.give_task(nil, nil, {"sar_start_get_to_the_monolith_quest_task"}) end)
			ev("give_task get_to_the_monolith " .. tostring(okt) .. " " .. tostring(errt))
			qa.assert("SC quest marker target resolves (sar_codedoor_left_decoder)", get_story_object_id("sar_codedoor_left_decoder") ~= nil, tostring(get_story_object_id("sar_codedoor_left_decoder")))
			S.step = 1
		elseif S.step == 1 then
			local aid, actor = first_actor()
			if aid == nil then if dt > 6 then qa.assert("SC actor present", false, "none") S.step = 99 end return end
			local d = S.decoder
			local p, lv, gv = d.position, d.m_level_vertex_id, d.m_game_vertex_id
			alife():release(d, true)
			alife():create("dev_decoder", p, lv, gv, aid)
			ev("decoder given to actor " .. tostring(aid))
			S.aid = aid; S.step = 2; S.st = now
		elseif S.step == 2 then
			local aid, actor = first_actor()
			local has = false
			pcall(function() has = xr_conditions.actor_has_item(actor, actor, {"dev_decoder"}) end)
			if has or now - S.st > 1500 then
				qa.assert("SC actor_has_item(dev_decoder) true (door on_use condition)", has == true, tostring(has))
				story_flags.give_flag("SAR_MONOLITH_WISH_SPACE_RESTRICTOR_INFO")
				S.step = 3; S.st = now
			end
		elseif S.step == 3 then
			local has = story_flags.has_flag("PRI_MONOLITH_DECODER_GOT")   -- patch soc_aes_quests: the decoder task is gone, its tick sets the SoC info
			if has or now - S.st > 10000 then
				qa.assert("SC decoder in hand -> PRI_MONOLITH_DECODER_GOT (soc_aes_quests tick), the open-door step follows", has == true, tostring(has))
				S.step = 31; S.st = now
			end
		elseif S.step == 31 then
			-- walk the actor to the door (it must be online to run its logic), then use it exactly like a player: on_use needs the decoder
			local did = get_story_object_id("sar_codedoor_left_decoder")
			local dobj = did and alife():object(did)
			local aid, actor = first_actor()
			local stg = did and db.storage[did]
			if stg ~= nil and stg.ph_door ~= nil and stg.ph_door.door_action ~= nil and actor ~= nil then
				S.did = did
				pcall(function() stg.ph_door.door_action:use_callback(nil, actor) end)
				local sec = tostring(stg.active_section)
				qa.assert("SC door use with decoder switches ph_door@locked_start_open_idle -> ph_door@locked_start_open", sec == "ph_door@locked_start_open", sec)
				qa.assert("SC LOCKED_START_OPEN_INFO set by the door use", story_flags.has_flag("LOCKED_START_OPEN_INFO") == true)
				S.step = 4; S.st = now; S.wave = 1
			elseif now - S.st > 12000 then
				qa.assert("SC door logic online for use", false, "storage=" .. tostring(stg) .. " obj=" .. tostring(dobj))
				S.step = 99
			elseif dobj ~= nil and actor ~= nil and now - (S.lastmove or 0) > 2000 then
				S.lastmove = now
				pcall(function() actor:set_actor_position(vector():set(dobj.position.x, dobj.position.y + 1.0, dobj.position.z)) end)
				ev(string.format("moved actor to the door %.1f %.1f %.1f", dobj.position.x, dobj.position.y, dobj.position.z))
			end
		elseif S.step == 4 then
			local board = sim_board.get_sim_board()
			local sq
			for id, s in pairs(board.squads) do if s.settings_id == "sar_smart_terrain_18_ordinary_monolith_" .. S.wave .. "_squad" then sq = s end end
			if sq ~= nil then
				local ids = {}
				for k in sq:squad_members() do table.insert(ids, k.id) end
				qa.assert("SC door wave " .. S.wave .. " spawned with 2 members", #ids == 2, tostring(#ids))
				-- squad death path of se_stalker:on_death (squad:on_npc_death), the same call a real kill ends in
				for _, id in ipairs(ids) do local o = alife():object(id); if o ~= nil then local okk, errk = pcall(function() sq:on_npc_death(o); alife():release(o, true) end); ev("kill member " .. id .. " " .. tostring(okk) .. " " .. tostring(errk)) end end
				S.flag = "SAR_SMART_TERRAIN_18_ORDINARY_MONOLITH_" .. S.wave .. "_SQUAD_DEAD"
				S.step = 5; S.st = now
			elseif now - S.st > 3000 then qa.assert("SC door wave " .. S.wave .. " spawned", false, "timeout") S.step = 99 end
		elseif S.step == 5 then
			if story_flags.has_flag(S.flag) then
				qa.assert("SC death flag " .. S.flag, true)
				if S.wave == 3 then S.step = 6; S.st = now else S.wave = S.wave + 1; S.step = 4; S.st = now end
			elseif now - S.st > 8000 then qa.assert("SC death flag " .. S.flag, false, "timeout") S.step = 99 end
		elseif S.step == 6 then
			local stg = db.storage[S.did]
			local sec = stg and tostring(stg.active_section)
			local isopen = false
			pcall(function() isopen = stg.ph_door.door_action:is_open() end)
			if (sec == "ph_door@open" and isopen) or now - S.st > 12000 then
				qa.assert("SC door switches to ph_door@open after the 3 waves are dead", sec == "ph_door@open", tostring(sec))
				qa.assert("SC door is open (door_action:is_open)", isopen == true, tostring(isopen))
				S.step = 99
			end
		end
	end)
	if not ok then ev("machine error " .. tostring(err)) end
	return false
end

qa.hooks.sarc2 = function(t, lo)
	local ln = level.name()
	local now = time_global()
	if ln == "coop_l11_sarcofag" then
		if not S.reg then
			S.reg = true
			pcall(function() game.respawn_dead_players = function() end end)
			level.add_call(machine, function() end)
			ev("machine registered")
		end
		return
	end
	-- level changes in xrMPE co-op go through a party vote: keep voting yes while standing in the changer
	if OnServer() and ln == "coop_l11_stancia_1" and st.moved and now - (st.last_vote or 0) > 5000 then
		st.last_vote = now
		for id, v in pairs(db.mp_actors) do pcall(function() coop_map_vote.on_yes(id) end) end
		ev("vote yes sent")
		return
	end
	if OnServer() and ln == "coop_l11_stancia_1" and not st.moved and t > 15 and db.mp_actors ~= nil then
		for id, v in pairs(db.mp_actors) do
			if v ~= nil then
				local ok, err = pcall(function() v:set_actor_position(vector():set(367.85, -1.0, 36.74)) end)
				ev("moved actor into aes_1_level_changer: " .. tostring(ok) .. " " .. tostring(err))
				st.moved = true
			end
		end
		return
	end
	if not OnServer() or ln ~= "coop_l01_escape" then return end
	if st.tstage == 0 and t > 12 and db.mp_actors ~= nil and next(db.mp_actors) ~= nil then
		story_flags.give_flag("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_SAR_INFO")
		st.travel = now; st.tstage = 1; ev("guide flag")
	elseif st.tstage == 1 and now - st.travel > 1500 then
		for id, v in pairs(db.mp_actors) do coop_map_vote.on_yes(id) end
		st.tstage = 2; st.vt = now
	elseif st.tstage == 2 and now - st.vt > 8000 then
		st.tstage = 3
		local ok, err = pcall(function() xr_effects.xrmpe_teleport_actors(nil, nil, {"esc_smart_terrain_1_guide_temp_15_walk", "esc_smart_terrain_1_guide_temp_15_look"}) end)
		ev("teleport " .. tostring(ok) .. " " .. tostring(err))
	end
end
