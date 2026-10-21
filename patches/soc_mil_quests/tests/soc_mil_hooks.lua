--@qa_lib
-- Army Warehouses quests of the original SoC (test only, never shipped). ONE listen-host run with one extra client (two players):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socmil -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 260 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix SM
-- (Cordon is enough: the chain is driven by shared story flags and the tick runs on every level; the Military level itself and the real dialog
--  windows need that level online and are covered by tests\mock_test.py, which plays the real dialogs.)
-- The host fast-forwards the chain with the flags the dialogs and the squads give, and EVERY process (host and client each check their own
-- player) asserts:
--   1. Freedom: report to Max -> "Destroy the Duty squad" (one objective) -> "Return to Lukash" -> Barrier job (talk to the commander,
--      help destroy the Monolith squad, talk to the commander for the reward), each with the SoC title and description
--   2. Duty: tower sniper -> "Return to Skull" -> three snipers + Lukash -> "Return to the Duty farmstead and receive my fee"
--   3. the mod-only tasks (eight "kill the Duty", fourth sniper, "go to the Radar") are never given
--   4. server side: coop_soc_mil.who(task) lists EVERY player of db.mp_actors
--   5. payments of the dialog actions (Lukash / Skull 4000 once, Skull fee 8000) go to the talking player only, once
--   6. fallbacks: Cap dead, Lukash dead, Skull dead do not block a step; the Radar task still comes
-- Lines in qa_events.log:  SOCMIL ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCMIL " .. s) end

local FORBIDDEN = { "mil_start_kill_the_duty_1_quest_task", "mil_start_kill_the_duty_2_quest_task", "mil_start_kill_the_duty_3_quest_task",
	"mil_start_kill_the_duty_4_quest_task", "mil_start_kill_the_duty_5_quest_task", "mil_start_kill_the_duty_6_quest_task",
	"mil_start_kill_the_duty_7_quest_task", "mil_start_kill_the_duty_8_quest_task", "mil_start_kill_the_snipers_4_quest_task",
	"mil_start_go_to_radar_quest_task" }

local DUTY = { "MIL_SMART_TERRAIN_14_DUTY_SKULL_SQUAD_DEAD", "MIL_SMART_TERRAIN_14_DUTY_2_SQUAD_DEAD", "MIL_SMART_TERRAIN_14_DUTY_3_SQUAD_DEAD",
	"MIL_SMART_TERRAIN_14_DUTY_4_SQUAD_DEAD", "MIL_SMART_TERRAIN_14_DUTY_5_SQUAD_DEAD", "MIL_SMART_TERRAIN_14_DUTY_6_SQUAD_DEAD",
	"MIL_SMART_TERRAIN_14_DUTY_7_SQUAD_DEAD", "MIL_SMART_TERRAIN_14_DUTY_8_SQUAD_DEAD", "MIL_SMART_TERRAIN_14_DUTY_9_SQUAD_DEAD" }

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function tr(id) return safe(function() return game.translate_string(id) end) end

local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_mil.who(id) end) or {}
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
		qa.assert(id .. " description is the SoC objective", ti.descr == tr(descr_id) and ti.descr ~= descr_id, tostring(ti.descr))
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

local function T(id) return "st_" .. string.gsub(id, "_task$", "") end

local function snipers(me)
	for i = 1, 3 do
		expect_task(me, "mil_start_kill_the_snipers_" .. i .. "_quest_task", "st_mil_start_kill_the_snipers_quest_task_name", "st_mil_start_kill_the_snipers_quest_task_descr")
	end
end

qa.once("socmil_run", function(t, lo)
	local steps = {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			for _, id in ipairs({ "mil_start_report_to_max_quest_task", "mil_soc_return_lukash_task", "mil_soc_cap_reward_task", "mil_soc_duty_fee_task" }) do
				qa.assert("before the story: not given " .. id, task_info(me, id) == nil)
			end
			-- Freedom: Lukash gave the Duty job
			L.flag_give("MIL_SMART_TERRAIN_3_FREEDOM_LUKASH_HELP_FREEDOM_STOP_DIALOG_INFO")
			qa.assert("Lukash state: wait (sent to Max)", coop_soc_mil.lukash_state() == "wait", tostring(coop_soc_mil.lukash_state()))
			qa.assert("Max state: job", coop_soc_mil.max_state() == "job", tostring(coop_soc_mil.max_state()))
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_start_report_to_max_quest_task", "st_mil_start_report_to_max_quest_task_name", "st_mil_start_report_to_max_quest_task_descr")
			L.flag_give("MIL_SMART_TERRAIN_15_FREEDOM_MAX_HELP_FREEDOM_STOP_DIALOG_INFO")
			qa.assert("Max state: busy", coop_soc_mil.max_state() == "busy", tostring(coop_soc_mil.max_state()))
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_start_kill_skull_quest_task", "st_mil_start_kill_skull_quest_task_name", "st_mil_start_kill_skull_quest_task_descr")
			-- eight of nine squads dead: no DD yet
			for i = 1, 8 do L.flag_give(DUTY[i]) end
			return L.wait(4)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("eight squads dead: the group is not dead yet", not L.flag_has("MIL_SOC_DUTY_DEAD"))
			qa.assert("eight squads dead: no 'Return to Lukash' yet", task_info(me, "mil_soc_return_lukash_task") == nil)
			L.flag_give(DUTY[9])
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("the whole Duty group dead: MIL_SOC_DUTY_DEAD", L.flag_has("MIL_SOC_DUTY_DEAD"))
			expect_task(me, "mil_soc_return_lukash_task", "st_mil_soc_return_lukash_name", "st_mil_soc_return_lukash_descr")
			qa.assert("Lukash state: report", coop_soc_mil.lukash_state() == "report", tostring(coop_soc_mil.lukash_state()))
			-- Lukash's report talk (phrase 3002 gives DONE, 7004 gives the Barrier job)
			L.flag_give("MIL_SOC_LUKASH_JOB_DONE")
			L.flag_give("MIL_SOC_BLOCKPOST_ACCEPTED")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_start_talk_to_the_cap_quest_task", "st_mil_start_talk_to_the_cap_quest_task_name", "st_mil_start_talk_to_the_cap_quest_task_descr")
			qa.assert("Lukash state: capwait", coop_soc_mil.lukash_state() == "capwait", tostring(coop_soc_mil.lukash_state()))
			L.flag_give("MIL_SMART_TERRAIN_12_1_FREEDOM_CAP_PROTECT_THE_BARRIER_DIALOG_INFO")      -- Cap's phrase 1004
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_start_protect_the_barrier_quest_task", "st_mil_start_protect_the_barrier_quest_task_name", "st_mil_start_protect_the_barrier_quest_task_descr")
			L.flag_give("MIL_SMART_TERRAIN_17_MONOLITH_1_SQUAD_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_cap_reward_task", "st_mil_soc_cap_reward_name", "st_mil_soc_cap_reward_descr")
			qa.assert("Cap state: reward", coop_soc_mil.cap_state() == "reward", tostring(coop_soc_mil.cap_state()))
			qa.assert("Lukash state: paid", coop_soc_mil.lukash_state() == "paid", tostring(coop_soc_mil.lukash_state()))
			-- the payment actions of the dialogs, with Sidorovich as the stand-in listener
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			qa.assert("a stand-in NPC for the dialog actions is online", sid ~= nil)
			L.set_money(nil, 1000)
			if sid ~= nil then
				safe(function() coop_soc_mil.pay_member(me, sid) end)
				safe(function() coop_soc_mil.pay_member(me, sid) end)
			end
			return L.wait(4)
		end,
		function(c)
			local m = L.money(nil)
			ev("money after Lukash: " .. tostring(m))
			qa.assert("Lukash paid 4000 once to this player (1000 -> 5000)", m == 5000, tostring(m))
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			local me = L.local_player()
			if sid ~= nil then safe(function() coop_soc_mil.pay_sniper(me, sid) end) end
			return L.wait(3)
		end,
		function(c)
			local m = L.money(nil)
			qa.assert("the SoC payment 1 is shared by Skull and Lukash: no second 4000", m == 5000, tostring(m))
			local me = L.local_player()
			-- Duty route (the Freedom report flag is taken away again: the sniper task of the Duty line fails on it, the two lines exclude each other in play)
			safe(function() story_flags.disable_flag("MIL_SMART_TERRAIN_15_FREEDOM_MAX_HELP_FREEDOM_STOP_DIALOG_INFO") end)
			L.flag_give("MIL_SMART_TERRAIN_18_DUTY_SKULL_1_STOP_DIALOG_INFO")
			L.flag_give("MIL_START_KILL_THE_SNIPER_ON_THE_TOWER_QUEST_TASK_INFO")
			qa.assert("Skull state: job", coop_soc_mil.skull_state() == "job", tostring(coop_soc_mil.skull_state()))
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_start_kill_the_sniper_on_the_tower_quest_task", "st_mil_start_kill_the_sniper_on_the_tower_quest_task_name",
				"st_mil_start_kill_the_sniper_on_the_tower_quest_task_descr")
			L.flag_give("MIL_SMART_TERRAIN_8_FREEDOM_1_SQUAD_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_start_talk_to_skull_about_the_assault_quest_task", "st_mil_start_talk_to_skull_about_the_assault_quest_task_name",
				"st_mil_start_talk_to_skull_about_the_assault_quest_task_descr")
			-- Skull's offer: "Gotcha." gives the assault flags
			L.flag_give("MIL_SMART_TERRAIN_18_DUTY_SKULL_TALK_TO_SKULL_ABOUT_THE_ASSAULT_STOP_DIALOG_INFO")
			L.flag_give("MIL_START_TAKE_KEY_POSITIONS_QUEST_TASK_INFO")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			snipers(me)
			expect_task(me, "mil_start_kill_lukash_quest_task", "st_mil_start_kill_lukash_quest_task_name", "st_mil_start_kill_lukash_quest_task_descr")
			qa.assert("Skull state: assault", coop_soc_mil.skull_state() == "assault", tostring(coop_soc_mil.skull_state()))
			L.flag_give("MIL_SMART_TERRAIN_16_FREEDOM_1_SQUAD_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_duty_fee_task", "st_mil_soc_duty_fee_name", "st_mil_soc_duty_fee_descr")
			qa.assert("Skull state: after", coop_soc_mil.skull_state() == "after", tostring(coop_soc_mil.skull_state()))
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			L.set_money(nil, 1000)
			if sid ~= nil then
				safe(function() coop_soc_mil.pay_fee(me, sid) end)
				safe(function() coop_soc_mil.pay_fee(me, sid) end)
			end
			-- no mod-only task anywhere
			for _, id in ipairs(FORBIDDEN) do
				qa.assert("mod-only task is never given: " .. id, task_info(me, id) == nil)
			end
			return L.wait(4)
		end,
		function(c)
			local m = L.money(nil)
			qa.assert("the fee is 8000 once (1000 -> 9000)", m == 9000, tostring(m))
			L.flag_give("MIL_SOC_DUTY_FEE")
			qa.assert("Skull state: done", coop_soc_mil.skull_state() == "done", tostring(coop_soc_mil.skull_state()))
			-- the Barkeep sent the party to the Radar: the Radar task still comes although the Military step is gone
			L.flag_give("MIL_START_GO_TO_RADAR_QUEST_TASK_INFO")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("Radar task still given", task_info(me, "rad_start_go_to_radar_quest_task") ~= nil)
			return L.screenshot("socmil_done")
		end,
	}
	L.task("socmil", steps)
end)
