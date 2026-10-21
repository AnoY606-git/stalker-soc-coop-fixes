--@qa_lib
-- The Guide and the Doctor of the original SoC (test only, never shipped). ONE listen-host run with one extra client (two players), Cordon start,
-- then party-vote travel to the Agroprom underground (the Doctor's hiding place):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socdoc -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 300 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir>
-- Every process (host and client each check their own player) asserts:
--   Cordon:  1. Ghost's documents flagged: the Guide topic is open; the REAL dialog window opens with the Guide (host only)
--            2. the Guide's last phrase gives ESC_FIND_DOCTOR_START (flagged like the dialog does): "Meet with Doctor" for EVERY player with the
--               SoC title / description, "Meet the Guide" of the Yantar chain done (YAN_SOC_GUIDE_MET)
--            3. party-vote travel to the Agroprom underground
--   Underground:
--            4. the server created the Doctor once (story id soc_cit_doctor, alive, profile soc_cit_doctor), he is ONLINE next to the SoC spot and
--               stands in his logic scheme (not walking away), invulnerable
--            5. the party near the hiding place sets ESC_FIND_DOCTOR_DONE; the REAL dialog window opens with the Doctor (host only); the first-meeting state
--            6. the talk flags (CIT_JAIL_DOCTOR_PRYP_TASK, CIT_DOCTOR_MEET_CONCLUSION_INFO) flagged like phrase 4 does: "Secret stash at Pripyat" for every
--               player, the greeting state changes, no second Doctor, the SoC voice files exist
--            7. the decoder flag closes the chain: no new task
-- Lines in qa_events.log:  SOCDOC ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCDOC " .. s) end

local DOC_POS = { x = -69.7555, y = -6.8732, z = -70.4957 }
local KNOCK = { x = -75.4297, y = -6.8732, z = -74.6515 }

local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_doctor.who(id) end) or {}
	local set = {}
	for _, pid in ipairs(got) do set[pid] = true end
	local n, miss = 0, {}
	for pid, a in pairs(db.mp_actors) do
		n = n + 1
		if not set[pid] then miss[#miss + 1] = tostring(pid) end
	end
	return (#miss == 0 and n > 0), "players=" .. n .. " missing=" .. table.concat(miss, ",")
end

local function expect_task(me, id, title_id, descr_id)
	local ti = task_info(me, id)
	qa.assert("task given to this player: " .. id, ti ~= nil)
	if ti then
		ev("TASK " .. id .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
		qa.assert(id .. " title is the SoC title", ti.title == tr(title_id) and ti.title ~= title_id, tostring(ti.title))
		qa.assert(id .. " description is [" .. descr_id .. "]", ti.descr == tr(descr_id) and ti.descr ~= descr_id, tostring(ti.descr))
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

local function doctor_ids()
	local ids = {}
	for i = 1, 65534 do
		local o = safe(function() return alife():object(i) end)
		if o ~= nil and safe(function() return o:section_name() end) == "soc_cit_doctor" then ids[#ids + 1] = i end
	end
	return ids
end

local function all_to(p)
	for _, pl in ipairs(L.players()) do
		safe(function() return L.teleport(pl.id, L.vec(p.x, p.y + 0.3, p.z)) end)
	end
end

-- ----------------------------------------------------------------------------------------------------------------------------- Cordon
local function cordon_part()
	L.task("socdoc_cordon", {
		function(c) return L.wait(12) end,
		function(c)
			qa.assert("no Doctor task before the Guide spoke", task_info(L.local_player(), "soc_doc_meet_task") == nil)
			qa.assert("the Guide topic is closed before Ghost's documents", coop_soc_doctor.st_g_open() == false)
			L.flag_give("X16_GHOST_DOCS_TAKEN")
			return L.wait(3)
		end,
		function(c)
			qa.assert("the Guide topic is open with Ghost's documents", coop_soc_doctor.st_g_open() == true)
			local guide = safe(function() return L.find_online("esc_smart_terrain_1_stalker_guide") end)
			qa.assert("the Guide is online", guide ~= nil)
			-- the real dialog window: the host only (two players opening the same NPC at once would only test the harness)
			if guide ~= nil and L.on_server() then return L.open_talk(guide, { shot = "socdoc_guide" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with the Guide: " .. tostring(talking))
				qa.assert("the dialog window opens with the Guide", talking == true)
				L.close_talk()
			end
			L.flag_give("ESC_FIND_DOCTOR_START")                        -- phrase 3 of soc_doc_guide_dialog
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "soc_doc_meet_task", "coop_soc_doc_meet_name", "coop_soc_doc_meet_descr")
			qa.assert("'Meet the Guide' of the Yantar chain is done (YAN_SOC_GUIDE_MET)", L.flag_has("YAN_SOC_GUIDE_MET"))
			qa.assert("the Guide topic is gone once he has spoken", coop_soc_doctor.st_g_open() == false)
			qa.assert("no Doctor on Cordon", #doctor_ids() == 0)
			return L.screenshot("socdoc_meet_task")
		end,
		function(c)
			return L.travel("agru", { fallback = true, timeout = 170 })
		end,
		function(c, ok, why) qa.assert("travel to the underground (this VM only continues on failure)", ok == true, tostring(why)) end,
	})
end

-- ----------------------------------------------------------------------------------------------------------------------------- underground
local function underground_part()
	L.task("socdoc_ug", {
		function(c) return L.wait(14) end,
		function(c)
			local me = L.local_player()
			if L.on_server() then
				local ids = doctor_ids()
				qa.assert("exactly one Doctor entity exists (" .. #ids .. ")", #ids == 1)
				local sid = safe(function() return get_story_object_id("soc_cit_doctor") end)
				qa.assert("the Doctor has the story id soc_cit_doctor", sid ~= nil and sid == ids[1], tostring(sid))
				local se = sid and safe(function() return alife():object(sid) end)
				qa.assert("the Doctor is alive", se ~= nil and safe(function() return se:alive() end) == true)
				if se ~= nil then
					local p = se.position
					ev(string.format("Doctor entity at %.2f %.2f %.2f", p.x, p.y, p.z))
					qa.assert("the Doctor stands at the SoC spot", math.abs(p.x - DOC_POS.x) < 1.5 and math.abs(p.z - DOC_POS.z) < 1.5)
				end
			end
			expect_task(me, "soc_doc_meet_task", "coop_soc_doc_meet_name", "coop_soc_doc_meet_descr")
			qa.assert("not met yet far from the hiding place", not L.flag_has("ESC_FIND_DOCTOR_DONE"))
			qa.assert("the Doctor's greeting is the first-meeting state", coop_soc_doctor.st_h_first() == true)
			all_to({ x = KNOCK.x + 2, y = KNOCK.y, z = KNOCK.z + 2 })
			return L.wait(12)
		end,
		function(c)
			qa.assert("the party near the hiding place: ESC_FIND_DOCTOR_DONE", L.flag_has("ESC_FIND_DOCTOR_DONE"))
			all_to({ x = DOC_POS.x + 1.5, y = DOC_POS.y, z = DOC_POS.z + 1.5 })
			return L.wait(10)
		end,
		function(c)
			local doc = safe(function() return L.find_online("soc_cit_doctor") end)
			qa.assert("the Doctor is online next to the party", doc ~= nil)
			if doc ~= nil then
				local id = doc:id()
				local st = safe(function() return db.storage[id] end)
				local scheme = st and st.active_scheme
				ev("Doctor online id=" .. tostring(id) .. " active_scheme=" .. tostring(scheme))
				qa.assert("the Doctor runs his logic (active scheme set)", scheme ~= nil, tostring(scheme))
				local pos = doc:position()
				qa.assert("he stayed at his spot", math.abs(pos.x - DOC_POS.x) < 3 and math.abs(pos.z - DOC_POS.z) < 3, string.format("%.1f %.1f", pos.x, pos.z))
				qa.assert("he is alive and invulnerable (alive)", doc:alive() == true)
			end
			if doc ~= nil and L.on_server() then return L.open_talk(doc, { shot = "socdoc_doctor" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with the Doctor: " .. tostring(talking))
				qa.assert("the dialog window opens with the Doctor", talking == true)
				L.close_talk()
			end
			qa.assert("no stash task before the talk", task_info(L.local_player(), "soc_doc_stash_task") == nil)
			L.flag_give("CIT_JAIL_DOCTOR_PRYP_TASK")                    -- phrase 4 of soc_doc_main_dialog
			L.flag_give("CIT_DOCTOR_MEET_CONCLUSION_INFO")
			return L.wait(10)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "soc_doc_stash_task", "coop_soc_doc_stash_name", "coop_soc_doc_stash_descr")
			qa.assert("the greeting is the second state", coop_soc_doctor.st_h_after() == true and coop_soc_doctor.st_d_open() == false)
			qa.assert("still exactly one Doctor", not L.on_server() or #doctor_ids() == 1)
			for _, id in ipairs(coop_soc_doctor.VOICE_D) do
				local path = "characters_voice\\dialogs\\eng\\" .. (id == "h11" and "cit_doctor_hello_dialog_11" or ("cit_doctor_main_dialog_" .. id))
				local f = getFS():exist("$game_sounds$", path .. ".ogg")
				qa.assert("English recording exists for the Doctor phrase " .. id, f ~= nil and f ~= false, path)
			end
			L.flag_give("PRI_MONOLITH_DECODER_GOT")                     -- soc_aes_quests: the decoder is taken
			return L.wait(6)
		end,
		function(c)
			qa.assert("the decoder closes the chain (SOC_DOC_CLOSED)", L.flag_has("SOC_DOC_CLOSED"))
			return L.screenshot("socdoc_done")
		end,
	})
end

qa.once("socdoc_run", function(t, lo)
	local lvl = L.level_name()
	ev("hook runs on " .. tostring(lvl))
	if lvl == "coop_l01_escape" then
		cordon_part()
	elseif lvl == "coop_l03_agroprom_underground" then
		L.travel_arrived()
		underground_part()
	end
end)
