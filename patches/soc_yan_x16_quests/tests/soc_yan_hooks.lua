--@qa_lib
-- Yantar / X16 chain of the original SoC (test only, never shipped). ONE listen-host run with one extra client (two players), Cordon start,
-- party-vote travel to Yantar (what the earlier Yantar tests did), then the chain is fast-forwarded with the flags the dialogs and the world give:
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socyan -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 420 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir>
-- The lab part (second run, same hook): add  -Cfg dest=x16  (travel from Cordon straight to the lab level):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socyanx -Cfg dest=x16 -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 300 -ResultDir <dir>
-- Every process (host and client each check their own player) asserts:
--   Yantar:  1. "Help for the scientists" at arrival; Sakharov starts in the offer state; the REAL dialog window opens with Sakharov
--            2. help offered: ONE measurement task whose description follows the flags (talk to Kruglov, escort, results to Sakharov)
--            3. the server gives the device (every process: the party holds one), a player standing in a site for 10 s measures it (3 sites)
--            4. results: helmet + artifact for every player, Vasiliev's corpse and PDA exist, the lab task text, PDA read, lab flags
--            5. levers + exit: the exit task with the tunnel text, then the Sakharov thanks state, no soft-lock when the lab is skipped
--   X16:     the lab tasks (Ghost's documents, the control modules and the mechanism) with their descriptions per lever, Ghost's body and
--            documents, YAN_X16_DOCUMENTS_GAIN for the Barkeep task, "Meet the Guide", the exit task
-- Lines in qa_events.log:  SOCYAN ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCYAN " .. s) end
local DEST = qa.cfg and qa.cfg.dest or "yan"

local OFFERED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO"
local PREP = "YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO"
local REPORTED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO"
local HELMET = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO"
local DONE = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO"
local SITES = { { 108.5, -8.9, -209.3 }, { 144.2, -8.9, -121.8 }, { 177.9, -4.6, -99.5 } }
local SW = { "X16_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO", "X16_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO", "X16_LAB_PRIMARY_SWITCHER_3_DEACTIVATE_INFO",
	"X16_LAB_PRIMARY_SWITCHER_4_DEACTIVATE_INFO" }

local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

-- the player ids that got the task from the server tick, and every id of db.mp_actors
local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_yan.who(id) end) or {}
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
		if descr_id then
			qa.assert(id .. " description is [" .. descr_id .. "]", ti.descr == tr(descr_id) and ti.descr ~= descr_id, tostring(ti.descr))
		end
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

local function descr_is(me, id, descr_id)
	local ti = task_info(me, id)
	qa.assert(id .. " description now [" .. descr_id .. "]", ti ~= nil and ti.descr == tr(descr_id) and ti.descr ~= descr_id, ti and tostring(ti.descr) or "no task")
end

local function not_given(me, id)
	qa.assert("not given: " .. id, task_info(me, id) == nil)
end

-- the party holds the item (server: every player of db.mp_actors; a client: its own player)
local function everyone_holds(section)
	local pl = L.players()
	local n, miss = 0, {}
	for _, p in ipairs(pl) do
		n = n + 1
		if (L.count_item(p.id, section) or 0) < 1 then miss[#miss + 1] = tostring(p.id) end
	end
	return n > 0 and #miss == 0, "players=" .. n .. " missing=" .. table.concat(miss, ",")
end

-- teleport every player to a point (the carrier of the device is not known: the server gives it to the first living player)
local function all_to(pos)
	for _, p in ipairs(L.players()) do
		safe(function() return L.teleport(p.id, pos) end)
	end
end

-- ----------------------------------------------------------------------------------------------------------------------------- Cordon
local function cordon_part()
	L.task("socyan_travel", {
		function(c) return L.wait(8) end,
		function(c) return L.travel(DEST, { fallback = true, timeout = 170 }) end,
		function(c, ok, why) qa.assert("travel to " .. DEST .. " (this VM only continues on failure)", ok == true, tostring(why)) end,
	})
end

-- ----------------------------------------------------------------------------------------------------------------------------- Yantar
local function yantar_part()
	local steps = {
		function(c) return L.wait(12) end,
		function(c)
			local me = L.local_player()
			expect_task(me, "yan_soc_job_task", "coop_soc_yan_job_name", "coop_soc_yan_job_descr")
			qa.assert("ARRIVED flag set by the tick", L.flag_has("ROS_START_GO_TO_YANTAR_QUEST_TASK_INFO"))
			for _, id in ipairs({ "yan_start_talk_to_the_kruglov_quest_task", "yan_start_infiltrate_the_x16_lab_quest_task", "yan_start_go_to_yantar_quest_task",
				"yan_start_take_measurements_1_quest_task", "yan_start_configuring_helmets_quest_task" }) do
				not_given(me, id)
			end
			qa.assert("Sakharov starts in the offer state", coop_soc_yan.sak_state() == "offer", tostring(coop_soc_yan.sak_state()))
			qa.assert("Kruglov starts in the meet state", coop_soc_yan.kru_state() == "meet", tostring(coop_soc_yan.kru_state()))
			local sak = safe(function() return L.find_online("yan_smart_terrain_1_ecolog_saharov") end)
			qa.assert("Sakharov is online", sak ~= nil)
			-- the real dialog window: the host only (two players opening the same NPC at once would only test the harness)
			if sak ~= nil and L.on_server() then return L.open_talk(sak, { shot = "socyan_sakharov_offer" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with Sakharov (offer state): " .. tostring(talking))
				qa.assert("the SoC dialog window opens with Sakharov", talking == true)
				L.close_talk()
			end
		end,
		function(c)
			-- the dialog phrase 21112 / 10141 sets the flag
			L.flag_give(OFFERED)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "yan_start_talk_to_the_kruglov_quest_task", "st_yan_start_talk_to_the_kruglov_quest_task_name", "st_yan_start_talk_to_the_kruglov_quest_task_descr")
			qa.assert("Sakharov waits", coop_soc_yan.sak_state() == "wait", tostring(coop_soc_yan.sak_state()))
			qa.assert("Kruglov talk state", coop_soc_yan.kru_state() == "talk", tostring(coop_soc_yan.kru_state()))
			local kru = safe(function() return L.find_online("yan_smart_terrain_1_ecolog_kruglov") end)
			if kru ~= nil and L.on_server() then return L.open_talk(kru, { shot = "socyan_kruglov_talk" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with Kruglov (escort state): " .. tostring(talking))
				qa.assert("the SoC dialog window opens with Kruglov", talking == true)
				L.close_talk()
			end
			L.flag_give(PREP)               -- phrase 11111 of his dialog
			return L.wait(10)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "yan_start_talk_to_the_kruglov_quest_task", "st_yan_start_take_measurements_1_quest_task_descr")
			if L.on_server() then
				local ok, info = everyone_holds("yan_psi_detector")
				-- the device goes to ONE player (the first living one): at least one holds it
				local n = 0
				for _, p in ipairs(L.players()) do n = n + (L.count_item(p.id, "yan_psi_detector") or 0) end
				qa.assert("the server gave the measuring device to the party (" .. n .. ")", n >= 1, info)
			end
			all_to(SITES[1])
			return L.wait(16)
		end,
		function(c)
			qa.assert("site 1 measured (10 s in the sphere)", not L.on_server() or L.flag_has("YAN_START_TAKE_MEASUREMENTS_1_QUEST_TASK_INFO"))
			all_to(SITES[2])
			return L.wait(16)
		end,
		function(c)
			qa.assert("site 2 measured", not L.on_server() or L.flag_has("YAN_START_TAKE_MEASUREMENTS_2_QUEST_TASK_INFO"))
			all_to(SITES[3])
			return L.wait(40)             -- site 3 is the research stop: cutscenes_pkg_yantar plays its 33 s camera scene there
		end,
		function(c)
			local me = L.local_player()
			qa.assert("site 3 measured", L.flag_has("YAN_START_TAKE_MEASUREMENTS_3_QUEST_TASK_INFO"))
			descr_is(me, "yan_start_talk_to_the_kruglov_quest_task", "st_yan_start_talk_to_the_saharov_quest_task_descr")
			qa.assert("Sakharov: results state", coop_soc_yan.sak_state() == "results", tostring(coop_soc_yan.sak_state()))
			local sak = safe(function() return L.find_online("yan_smart_terrain_1_ecolog_saharov") end)
			if sak ~= nil and L.on_server() then return L.open_talk(sak, { shot = "socyan_sakharov_results" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with Sakharov (results state): " .. tostring(talking))
				qa.assert("the results dialog opens", talking == true)
				L.close_talk()
			end
			-- phrase 31 sets the three flags
			L.flag_give(REPORTED); L.flag_give(HELMET); L.flag_give("YAN_SOC_REWARD_GIVEN")
			return L.wait(10)
		end,
		function(c)
			local me = L.local_player()
			if L.on_server() then
				local ok, info = everyone_holds("dev_psi_protection_helmet")
				qa.assert("the helmet is in every player's bag (" .. tostring(info) .. ")", ok)
				local ok2, info2 = everyone_holds("af_cristall_flower")
				qa.assert("the artifact reward is in every player's bag (" .. tostring(info2) .. ")", ok2)
				local vid = safe(function() return get_story_object_id("yan_vasilyev") end)
				qa.assert("Vasiliev's corpse exists (story id yan_vasilyev)", vid ~= nil, tostring(vid))
				local so = vid and safe(function() return alife():object(vid) end)
				qa.assert("Vasiliev is dead", so ~= nil and safe(function() return so:alive() end) == false)
				local pda = false
				for id = 1, 65534 do
					local o = safe(function() return alife():object(id) end)
					if o ~= nil and safe(function() return o:section_name() end) == "yan_vasilyev_pda" then pda = true break end
				end
				qa.assert("Vasiliev's PDA lies in the swamp", pda)
			end
			expect_task(me, "yan_start_infiltrate_the_x16_lab_quest_task", "st_yan_start_infiltrate_the_x16_lab_quest_task_name", "coop_soc_yan_vasilyev_descr")
			not_given(me, "yan_start_configuring_helmets_quest_task")
			qa.assert("Sakharov: lab state", coop_soc_yan.sak_state() == "lab", tostring(coop_soc_yan.sak_state()))
			L.give_item(nil, "yan_vasilyev_pda", 1)        -- the party picks up Vasiliev's PDA
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("PDA read: VASILYEV_FOUND", not L.on_server() or L.flag_has("YAN_SOC_VASILYEV_FOUND"))
			descr_is(me, "yan_start_infiltrate_the_x16_lab_quest_task", "st_yan_start_infiltrate_the_x16_lab_quest_task_descr")
			-- the lab (the lab level itself is the second run, -Cfg dest=x16): the levers, flagged
			for i = 1, 4 do L.flag_give(SW[i]) end
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("all four levers: Ghost's documents step is closed (no soft-lock)", L.flag_has("X16_GHOST_DOCS_TAKEN") and L.flag_has("YAN_X16_DOCUMENTS_GAIN"))
			qa.assert("all four levers and back on Yantar: the exit flag (no tunnel needed)", L.flag_has("X16_START_GET_OUT_OF_THE_LAB_TASK_INFO"))
			expect_task(me, "x16_start_get_out_of_the_lab_task", "st_x16_start_get_out_of_the_lab_task_name", "st_yan_start_talk_to_the_saharov_x16_lab_quest_task_descr")
			expect_task(me, "yan_soc_guide_task", "coop_soc_yan_guide_name", "coop_soc_yan_guide_descr")
			qa.assert("Sakharov: thanks state", coop_soc_yan.sak_state() == "exit", tostring(coop_soc_yan.sak_state()))
			L.flag_give(DONE)               -- phrase 231
			return L.wait(6)
		end,
		function(c)
			qa.assert("Sakharov: the mod's greeting afterwards", coop_soc_yan.sak_state() == "done", tostring(coop_soc_yan.sak_state()))
			-- the voice files and the per-player language
			local lang = safe(function() return coop_soc_opening.voice_lang() end) or "?"
			ev("voice language of this player: " .. tostring(lang))
			for _, id in ipairs(coop_soc_yan.VOICE_S) do
				local path = "characters_voice\\dialogs\\eng\\yantar_general_ucheniy_talk_start_" .. id
				local f = getFS():exist("$game_sounds$", path .. ".ogg")
				qa.assert("English recording exists for Sakharov phrase " .. id, f ~= nil and f ~= false, path)
				local p = coop_soc_yan.voice_path("s", id)
				if lang == "eng" then qa.assert("voice_language eng: phrase " .. id .. " plays the English file", p == path, tostring(p))
				elseif lang == "rus" then qa.assert("voice_language rus: phrase " .. id .. " plays the Russian file", p == "characters_voice\\dialogs\\yantar_general_ucheniy_talk_start_" .. id, tostring(p)) end
			end
			qa.assert("a phrase without a recording is silent", coop_soc_yan.voice_path("s", "2111") == nil)
			return L.screenshot("socyan_done")
		end,
	}
	L.task("socyan_yantar", steps)
end

-- ----------------------------------------------------------------------------------------------------------------------------- X16 lab
local function x16_part()
	local steps = {
		function(c) return L.wait(14) end,
		function(c)
			local me = L.local_player()
			qa.assert("lab level: the LAB flag and every earlier flag (monotonic chain)", L.flag_has("YAN_YAN_START_INFILTRATE_THE_X16_LAB_QUEST_TASK_INFO")
				and L.flag_has(HELMET) and L.flag_has("YAN_SOC_VASILYEV_FOUND"))
			expect_task(me, "yan_soc_ghost_task", "coop_soc_yan_ghost_name", "coop_soc_yan_ghost_1_descr")
			expect_task(me, "x16_start_find_the_installation_quest_task", "st_x16_start_find_the_installation_quest_task_name", "st_x16_start_find_the_installation_quest_task_descr")
			not_given(me, "yan_soc_job_task")
			not_given(me, "x16_start_turn_off_the_switch_1_task")
			if L.on_server() then
				local ok, info = everyone_holds("dev_psi_protection_helmet")
				qa.assert("every player has a helmet in the lab (" .. tostring(info) .. ")", ok)
				local gid = safe(function() return get_story_object_id("x16_stalker_ghost") end)
				qa.assert("Ghost's body exists (yantar_restore)", gid ~= nil, tostring(gid))
			end
			L.flag_give("X16_START_FIND_THE_INSTALLATION_QUEST_TASK_INFO")      -- the installation zone
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "yan_soc_ghost_task", "coop_soc_yan_ghost_2_descr")
			descr_is(me, "x16_start_find_the_installation_quest_task", "st_x16_start_turn_off_the_switch_1_task_descr")
			L.give_item(nil, "lab_x16_documents", 1)                           -- Ghost's documents
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("documents held: X16_GHOST_DOCS_TAKEN and YAN_X16_DOCUMENTS_GAIN", L.flag_has("X16_GHOST_DOCS_TAKEN") and L.flag_has("YAN_X16_DOCUMENTS_GAIN"))
			expect_task(me, "yan_soc_guide_task", "coop_soc_yan_guide_name", "coop_soc_yan_guide_descr")
			L.flag_give(SW[1])
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "x16_start_find_the_installation_quest_task", "st_x16_start_turn_off_the_switch_2_task_descr")
			L.flag_give(SW[2])
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "x16_start_find_the_installation_quest_task", "st_x16_start_turn_off_the_switch_3_task_descr")
			not_given(me, "x16_start_get_out_of_the_lab_task")
			L.flag_give(SW[3])
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "x16_start_find_the_installation_quest_task", "st_x16_start_turn_off_the_switch_4_task_descr")
			L.flag_give(SW[4])
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "x16_start_get_out_of_the_lab_task", "st_x16_start_get_out_of_the_lab_task_name", "coop_soc_yan_tunnel_descr")
			qa.assert("Sakharov's PDA state follows (exit not reached yet): lab", coop_soc_yan.sak_state() == "lab", tostring(coop_soc_yan.sak_state()))
			L.flag_give("X16_START_GET_OUT_OF_THE_LAB_TASK_INFO")              -- the tunnel exit zone on Yantar
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "x16_start_get_out_of_the_lab_task", "st_yan_start_talk_to_the_saharov_x16_lab_quest_task_descr")
			return L.screenshot("socyan_x16_done")
		end,
	}
	L.task("socyan_x16", steps)
end

qa.once("socyan_run", function(t, lo)
	local lvl = L.level_name()
	ev("hook runs on " .. tostring(lvl) .. " dest=" .. tostring(DEST))
	if lvl == "coop_l01_escape" then
		cordon_part()
	elseif lvl == "coop_l08_yantar" then
		L.travel_arrived()
		yantar_part()
	elseif lvl == "coop_l08_x16" then
		L.travel_arrived()
		x16_part()
	end
end)
