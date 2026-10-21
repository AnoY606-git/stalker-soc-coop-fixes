--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): Garbage quests in the original SoC order (patch garbage_soc_quests). ONE listen-host run, one joined client,
-- starting on Cordon, the party travels to the Garbage by the guide vote (qa_lib.travel, about 70 s).
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner garsoc -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix GS
-- The HOST drives the story (flags that the dialogs / restrictors would give), every machine (host AND client) asserts that ITS OWN player
-- got each task with the SoC title and the right description. Lines: qa_events.log "GS ..." ; asserts "GS ...".
--   Cordon  : Fox's flag -> "Meet with Seriy" (Fox's briefing text), nothing else, the level maker's "help the Gray" step never
--   Garbage : arrival -> "Respond to the call for help" (Bes) + "Meet with Seriy" now with the objective text; Bes answers -> raid task;
--             ambush dead -> "Talk to Bes"; Seriy's dialog flag -> the Agroprom task; Duty: a player stays at the checkpoint -> kill task; boars dead + one kill ->
--             "Talk with the Duty commander", the report helper pays the talking player once; Bes and the commander can be talked to
--             (is_talk_enabled); Seriy / Bes / the commander dead (GARSOC_FORCE_DEAD): the flags are given, the gate opens; no soft lock
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("GS " .. s) end
local function norm(s) return (string.gsub(tostring(s or ""), "%s+", " ")) end

local T = {
	GRAY = "gar_start_talk_to_gray_quest_task", A = "gar_start_help_the_gray_to_fight_off_the_bandits_quest_task",
	AGR = "gar_start_go_to_the_agroprom_quest_task",
	T1 = "gar_start_talk_to_devil_quest_task", T2 = "gar_start_help_to_repel_the_bandits_attack_quest_task", T3 = "gar_start_talk_to_devil_1_quest_task",
	K1 = "gar_start_help_fight_off_the_mutants_quest_task", K2 = "gar_soc_duty_report_task",
}
local FOX = "ESC_SMART_TERRAIN_6_STALKER_FOX_INFO_MILITARY_STOP_DIALOG_INFO"

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { state = safe(function() return t:get_state() end),
		title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function tr(id) return safe(function() return game.translate_string(id) end) end

-- assert that the local player has the task with the given title / description string ids
local function assert_task(lo, key, title_id, descr_id, label)
	local ti = task_info(lo, T[key])
	qa.assert("GS " .. label .. ": task " .. T[key] .. " is given to this player", ti ~= nil)
	if ti then
		ev("TASK " .. T[key] .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
		if title_id then qa.assert("GS " .. label .. ": title is " .. title_id, norm(ti.title) == norm(tr(title_id)) and tr(title_id) ~= title_id, tostring(ti.title)) end
		if descr_id then qa.assert("GS " .. label .. ": description is " .. descr_id, norm(ti.descr) == norm(tr(descr_id)) and tr(descr_id) ~= descr_id, tostring(ti.descr)) end
	end
	return ti
end

local function has_task(key)
	return function() return task_info(L.local_player(), T[key]) ~= nil end
end

local function given_everywhere(key, label)
	-- the server tick's own table: every player that is alive and ready has been given the task
	for _, p in ipairs(L.players()) do
		qa.assert("GS " .. label .. ": the tick gave " .. T[key] .. " to player " .. tostring(p.name), safe(function() return coop_scn_garbage_soc.given_to(T[key], p.id) end) == true)
	end
end

-- the Garbage name ids of the descriptions (soc_task_texts)
local D = {
	GRAY_BRIEF = "st_gar_start_help_the_gray_to_fight_off_the_bandits_quest_task_descr", GRAY_OBJ = "st_gar_start_talk_to_gray_quest_task_descr",
	GRAY_TITLE = "st_gar_start_talk_to_gray_quest_task_name",
	T1T = "st_gar_start_talk_to_devil_quest_task_name", T1D = "st_gar_start_talk_to_devil_quest_task_descr",
	T2T = "st_gar_start_help_to_repel_the_bandits_attack_quest_task_name", T3T = "st_gar_start_talk_to_devil_1_quest_task_name",
	AGRT = "st_gar_start_go_to_the_agroprom_quest_task_name", AGRD = "st_gar_start_go_to_the_agroprom_quest_task_descr",
	K1T = "st_gar_start_help_fight_off_the_mutants_quest_task_name", K2D = "st_gar_soc_duty_report_task_descr",
}

-------------------------------------------------------------------------------------------------------
-- host: drives the story
-------------------------------------------------------------------------------------------------------
local function host_run()
	local stage = L.state_get("gs_stage", 0)
	if stage == 0 then
		L.state_set("gs_stage", 1)
		L.god(true)
		L.task("gs_cordon", {
			function() return L.wait(8) end,
			function()
				local me = L.local_player()
				qa.assert("GS cordon: the level is Cordon", L.level_name() == "coop_l01_escape", tostring(L.level_name()))
				for _, k in ipairs({ "GRAY", "A", "AGR", "T1", "T2", "T3", "K1", "K2" }) do
					qa.assert("GS cordon baseline: no task " .. T[k], task_info(me, T[k]) == nil)
				end
				L.flag_give(FOX)                       -- Fox's dialog, last phrase
				ev("Fox flag given")
				return L.wait_for(has_task("GRAY"), 25)
			end,
			function(c, got)
				local me = L.local_player()
				qa.assert("GS cordon: 'Meet with Seriy' arrived after Fox's flag", got == true)
				assert_task(me, "GRAY", D.GRAY_TITLE, D.GRAY_BRIEF, "cordon")
				given_everywhere("GRAY", "cordon")
				qa.assert("GS cordon: the level maker's step 'help the Gray' is not given", task_info(me, T.A) == nil)
				for _, k in ipairs({ "T1", "T2", "T3", "K1", "K2", "AGR" }) do
					qa.assert("GS cordon: no Garbage task yet: " .. T[k], task_info(me, T[k]) == nil)
				end
				return L.screenshot("garsoc_cordon")
			end,
			function() return L.travel("garbage", { timeout = 220, fallback = true }) end,
			function(c, ok, why) qa.assert("GS route to the Garbage through the guide vote", ok == true, tostring(why)) end,
		})
		return
	end

	-- stage 1: the Garbage VM
	local arrived, level, secs = L.travel_arrived()
	qa.assert("GS arrived on the Garbage", arrived and level == "coop_l02_garbage", string.format("%s after %s s", tostring(level), tostring(secs)))
	L.god(true)
	L.task("gs_garbage", {
		function() return L.wait(25) end,
		function()
			local me = L.local_player()
			ev("status after the arrival: " .. tostring(safe(coop_scn_garbage_soc.status)))
			-- arrival: Bes's task, Seriy's task with the objective text
			qa.assert("GS arrival: flag GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO is set", L.flag_has("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO"))
			assert_task(me, "T1", D.T1T, D.T1D, "arrival")
			given_everywhere("T1", "arrival")
			assert_task(me, "GRAY", D.GRAY_TITLE, D.GRAY_OBJ, "arrival")
			qa.assert("GS arrival: the level maker's step 'help the Gray' is still not given", task_info(me, T.A) == nil)
			qa.assert("GS arrival: no later task yet", task_info(me, T.T2) == nil and task_info(me, T.AGR) == nil and task_info(me, T.K1) == nil)
			-- Bes can be talked to from the arrival (his logic waits for the arrival, not for the Yurik steps)
			local bes = safe(function() return L.find_online("gar_smart_terrain_4_stalker_devil") end)
			ev("Bes online=" .. tostring(bes ~= nil))
			if bes ~= nil then
				qa.assert("GS arrival: Bes accepts a talk (is_talk_enabled)", safe(function() return bes:is_talk_enabled() end) == true, tostring(safe(function() return bes:is_talk_enabled() end)))
			end
			return L.wait(10)                  -- the joined client needs time to see the task in progress
		end,
		function()
			-- Bes answers (his dialog gives this flag), then the raid task goes to every player
			L.flag_give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO")
			return L.wait_for(has_task("T2"), 20)
		end,
		function(c, got)
			local me = L.local_player()
			qa.assert("GS Bes answered: 'Repel the bandit raid' arrived", got == true)
			assert_task(me, "T2", D.T2T, nil, "bes")
			given_everywhere("T2", "bes")
			return L.wait(10)
		end,
		function()
			L.flag_give("GAR_SMART_TERRAIN_3_BANDIT_1_SQUAD_DEAD")
			L.flag_give("GAR_SMART_TERRAIN_3_BANDIT_2_SQUAD_DEAD")
			return L.wait_for(has_task("T3"), 20)
		end,
		function(c, got)
			local me = L.local_player()
			qa.assert("GS ambush dead: 'Talk to Bes' arrived", got == true)
			assert_task(me, "T3", D.T3T, nil, "bes done")
			given_everywhere("T3", "bes done")
			qa.assert("GS before Seriy's talk: no Agroprom task", task_info(me, T.AGR) == nil)
			return L.wait(10)
		end,
		function()
			-- the last phrases of the dialogs pay (SoC: Bes 2000, Seriy 2500) to the talking player through these helpers
			L.set_money(nil, 100)
			coop_scn_garbage_soc.pay_bes(L.local_player(), nil)
			coop_scn_garbage_soc.pay_seriy(L.local_player(), nil)
			L.flag_give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO")
			-- Seriy's dialog is over (its last phrase gives this flag): the Agroprom task
			L.flag_give("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO")
			return L.wait_for(function() return has_task("AGR")() and L.money(nil) ~= 100 end, 20)
		end,
		function(c, got)
			local me = L.local_player()
			qa.assert("GS Seriy's dialog flag: the Agroprom task arrived", got == true)
			assert_task(me, "AGR", D.AGRT, D.AGRD, "seriy")
			local m = L.money(nil)
			ev("money after Bes and Seriy: " .. tostring(m))
			qa.assert("GS Bes (2000) and Seriy (2500) paid the talking player once each, no tm reward on top", m == 4600, tostring(m))
			given_everywhere("AGR", "seriy")
			-- Duty checkpoint: the favor is offered before the wave; the squads are marked as spawned (no real boars); a player who stays near the
			-- checkpoint starts the wave by the server fallback (or the zone logic) and the kill task goes to every player
			qa.assert("GS favor is offered before the wave", coop_scn_garbage_soc.favor_open(me, nil) == true)
			qa.assert("GS the wave has not started far from the checkpoint", not L.flag_has("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
			L.flag_give("GAR_SMART_TERRAIN_8_M_BOAR_SQUAD_INFO")
			return L.teleport(nil, { 38, 0.5, 228 })
		end,
		function(c, ok)
			return L.wait(14)
		end,
		function()
			local me = L.local_player()
			local pr = safe(function() return L.find_online("gar_smart_terrain_8_duty_prapor") end)
			ev("commander online=" .. tostring(pr ~= nil))
			qa.assert("GS checkpoint: the Duty commander is online", pr ~= nil)
			if pr ~= nil then
				qa.assert("GS checkpoint: the commander accepts a talk (his walker is not no_meet)", safe(function() return pr:is_talk_enabled() end) == true, tostring(safe(function() return pr:is_talk_enabled() end)))
			end
			qa.assert("GS a player stayed at the checkpoint: the wave flag is set", L.flag_has("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
			return L.wait_for(has_task("K1"), 20)
		end,
		function(c, got)
			local me = L.local_player()
			qa.assert("GS wave started: the kill task arrived", got == true)
			assert_task(me, "K1", D.K1T, nil, "duty")
			given_everywhere("K1", "duty")
			qa.assert("GS the favor is no longer offered once the wave started", coop_scn_garbage_soc.favor_open(me, nil) == false)
			qa.assert("GS before the wave is over: no commander task", task_info(me, T.K2) == nil)
			return L.wait(10)
		end,
		function()
			for i = 1, 4 do L.flag_give("GAR_SMART_TERRAIN_8_M_BOAR_" .. i .. "_SQUAD_DEAD") end
			return L.wait(4)
		end,
		function()
			local me = L.local_player()
			qa.assert("GS wave over, nobody killed a boar: still no commander task", task_info(me, T.K2) == nil)
			L.flag_give("GAR_DUTY_BOAR_KILLED_1")                             -- a player's kill (patch garbage_duty counts them)
			return L.wait_for(has_task("K2"), 20)
		end,
		function(c, got)
			local me = L.local_player()
			qa.assert("GS a player killed a boar: 'Talk with the Duty commander' arrived", got == true)
			assert_task(me, "K2", D.K1T, D.K2D, "report")
			given_everywhere("K2", "report")
			local pr = safe(function() return L.find_online("gar_smart_terrain_8_duty_prapor") end)
			L.set_money(nil, 100)
			qa.assert("GS report is offered to the talking player", coop_scn_garbage_soc.report_open(me, pr) == true)
			coop_scn_garbage_soc.report_pay(me, pr)
			return L.wait(3)
		end,
		function()
			local me = L.local_player()
			local m = L.money(nil)
			ev("money after the report: " .. tostring(m))
			qa.assert("GS the reward (1500) went to the talking player", m == 1600, tostring(m))
			qa.assert("GS the shared report flag is set", L.flag_has("GAR_SOC_DUTY_REPORT_INFO"))
			qa.assert("GS report is not offered a second time", coop_scn_garbage_soc.report_open(me, nil) == false)
			-- no soft lock: the characters die (test switch), the flags their dialogs would give are given
			L.flag_clear("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO")
			L.flag_clear("GAR_SOC_DUTY_REPORT_INFO")
			L.flag_clear("GAR_FREE_PASS")
			_G.GARSOC_FORCE_DEAD = { gar_smart_terrain_2_stalker_gray = true, gar_smart_terrain_4_stalker_devil = true, gar_smart_terrain_8_duty_prapor = true }
			return L.wait(6)
		end,
		function()
			qa.assert("GS Seriy dead: his talk flag is given again", L.flag_has("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO"))
			qa.assert("GS Bes dead: his flags are set", L.flag_has("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO") and L.flag_has("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO"))
			qa.assert("GS the commander dead: the report flag and the pass (gate) are given", L.flag_has("GAR_SOC_DUTY_REPORT_INFO") and L.flag_has("GAR_FREE_PASS"))
			_G.GARSOC_FORCE_DEAD = nil
			ev("final status: " .. tostring(safe(coop_scn_garbage_soc.status)))
			return L.screenshot("garsoc_done")
		end,
	})
end

-------------------------------------------------------------------------------------------------------
-- joined client: waits for each task of the chain to reach its own player
-------------------------------------------------------------------------------------------------------
local function client_run()
	local stage = L.state_get("gs_cstage", 0)
	if stage == 0 then
		L.state_set("gs_cstage", 1)
		L.task("gs_client_cordon", {
			function() return L.wait_for(has_task("GRAY"), 150) end,
			function(c, got)
				qa.assert("GSC cordon: 'Meet with Seriy' reached the joined client", got == true)
				assert_task(L.local_player(), "GRAY", D.GRAY_TITLE, D.GRAY_BRIEF, "client cordon")
			end,
		})
		return
	end
	local keys = { { "T1", D.T1T }, { "T2", D.T2T }, { "T3", D.T3T }, { "AGR", D.AGRT }, { "K1", D.K1T }, { "K2", D.K1T } }
	local steps = { function() return L.wait_for(has_task("GRAY"), 90) end }
	steps[#steps + 1] = function(c, got)
		qa.assert("GSC arrival: the joined client still has 'Meet with Seriy'", got == true)
		assert_task(L.local_player(), "GRAY", D.GRAY_TITLE, D.GRAY_OBJ, "client arrival")
	end
	for _, kt in ipairs(keys) do
		steps[#steps + 1] = function() return L.wait_for(has_task(kt[1]), 150) end
		steps[#steps + 1] = function(c, got)
			qa.assert("GSC the joined client got " .. T[kt[1]], got == true)
			if got then assert_task(L.local_player(), kt[1], kt[2], nil, "client") end
		end
	end
	L.task("gs_client_garbage", steps)
end

qa.once("garsoc_run", function(t, lo)
	if _G.__garsoc_started then return end        -- appended to three scripts that can load at different times: start once
	_G.__garsoc_started = true
	if L.is_dedicated() then return end
	if L.on_server() then host_run() else client_run() end
end)
