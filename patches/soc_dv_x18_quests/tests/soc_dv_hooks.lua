--@qa_lib
-- Dark Valley / X18 / Barkeep chain of the original SoC (test only, never shipped). ONE listen-host run with one extra client (two players):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socdv -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 200 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir>
-- (Cordon is enough: the chain is driven by shared story flags, the tick runs on every level. The position zones of the bandit base and the
--  real Barkeep dialog window need Dark Valley / the Bar online and are covered by the Lua mock test, tests\mock_test.py.)
-- Fast-forwards the chain with the flags the story gives, then asserts on EVERY process (host and client each check their own player):
--   1. the SoC tasks appear in order with SoC titles and descriptions: sneak into the base, Borov's key (a dead Borov ends it, no soft-lock),
--      get out, find the entrance, "Find the documents" (lab entered), "Bring the documents to the Barkeep", the Yantar line
--   2. server side: coop_soc_dv.who(task) lists EVERY player of db.mp_actors (late joiners are covered by the per-player table, see the mock test)
--   3. the mod-only tasks (SOS, fake Gauss, document 1..3, poltergeist, exit, Sidorovich documents) are never given
--   4. the code door tasks (discover the code -> open the door using the code), the Bullet / Serega tasks and a dead Serega
--   5. the Barkeep dialog functions: states, hand-in of the three documents (taken, 10000 paid, flag set), the voice file exists in English,
--      is silent in Russian; the documents do NOT go to Sidorovich (his dialog is gone)
-- Lines in qa_events.log:  SOCDV ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCDV " .. s) end

local JOB = "ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO"
local AGR = "BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO"
local GO = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO"
local DONE = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO"

local FORBIDDEN = { "val_start_go_to_the_sos_signal_1_quest_task", "val_start_go_to_the_sos_signal_2_quest_task", "val_start_fake_gauss_1_quest_task",
	"val_start_fake_gauss_2_quest_task", "val_start_show_documents_to_sidorovich_quest_task", "x18_start_go_to_x18_doc_1_task",
	"x18_start_go_to_x18_doc_2_task", "x18_start_go_to_x18_doc_3_task", "x18_start_kill_the_flame_poltergeist_quest_task",
	"x18_start_get_out_of_the_lab_quest_task", "bar_start_sneak_into_the_x_18_lab_quest_task",
	"x18_start_find_the_password_x18_codedoor_1_task", "x18_start_find_the_password_x18_codedoor_2_task" }

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function tr(id) return safe(function() return game.translate_string(id) end) end

-- the player ids that got the task from the server tick, and every id of db.mp_actors
local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_dv.who(id) end) or {}
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
			qa.assert(id .. " description is the SoC objective", ti.descr == tr(descr_id) and ti.descr ~= descr_id, tostring(ti.descr))
		end
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

qa.once("socdv_run", function(t, lo)
	local steps = {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			for _, id in ipairs({ "val_soc_darklab_1_task", "val_soc_prisoner_task", "x18_soc_codedoor_1_code_task" }) do
				qa.assert("before the story: not given " .. id, task_info(me, id) == nil)
			end
			-- Sidorovich's job (Cordon chain) -> the Barkeep asks for the Agroprom documents; the hand-in flag; the Barkeep job accepted
			L.flag_give(JOB)
			qa.assert("Barkeep state after Sidorovich's job: agroprom", coop_soc_bar.state() == "agroprom", tostring(coop_soc_bar.state()))
			L.flag_give(AGR)
			qa.assert("Barkeep state after the hand-in: offer", coop_soc_bar.state() == "offer", tostring(coop_soc_bar.state()))
			L.flag_give(GO)
			qa.assert("Barkeep state after accepting the job: wait", coop_soc_bar.state() == "wait", tostring(coop_soc_bar.state()))
			return L.wait(10)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "val_soc_darklab_1_task", "st_soc_darklab_name", "st_soc_darklab_1_descr")
			qa.assert("old autosave flag of the Borov logic set", L.flag_has("BAR_START_SNEAK_INTO_THE_X_18_LAB_QUEST_TASK_INFO"))
			-- Borov killed by somebody before anyone entered the base: the key objective is over, nothing waits on the corpse
			L.flag_give("VAL_SMART_TERRAIN_12_BANDIT_1_SQUAD_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("Borov dead: VAL_ACTOR_HAS_BOROV_KEY (no soft-lock)", L.flag_has("VAL_ACTOR_HAS_BOROV_KEY"))
			qa.assert("Borov dead: VAL_ACTOR_ON_BANDITS_BASE (monotonic chain)", L.flag_has("VAL_ACTOR_ON_BANDITS_BASE"))
			expect_task(me, "val_soc_darklab_3_task", "st_soc_darklab_name", "st_soc_darklab_3_descr")
			L.flag_give("VAL_ACTOR_LEAVE_BANDITS_BASE")     -- the zone itself needs Dark Valley online (mock test)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "val_soc_darklab_4_task", "st_soc_darklab_name", "st_soc_darklab_4_descr")
			-- entering the lab (set by the lab restrictor in X18)
			L.flag_give("VAL_START_SNEAK_INTO_THE_X_18_LAB_1_QUEST_TASK_INFO")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("lab entered: VAL_X18_DOOR_OPEN and DAR_RUN_QUEST", L.flag_has("VAL_X18_DOOR_OPEN") and L.flag_has("DAR_RUN_QUEST"))
			expect_task(me, "val_start_sneak_into_the_x_18_lab_1_quest_task", "st_val_start_sneak_into_the_x_18_lab_1_quest_task_name",
				"st_val_start_sneak_into_the_x_18_lab_1_quest_task_descr")
			-- code doors
			L.flag_give("DAR_DOOR1_CLOSED")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "x18_soc_codedoor_1_code_task", "st_x18_start_find_the_password_x18_codedoor_1_task_name", "st_x18_start_find_the_password_x18_codedoor_1_task_descr")
			-- the party finds document 1 (the code): the second objective of the door
			L.give_item(nil, "dev_document_1_x18", 1)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("document 1 held: X18_START_GO_TO_X18_DOC_1_TASK_INFO (server)", not L.on_server() or L.flag_has("X18_START_GO_TO_X18_DOC_1_TASK_INFO"))
			expect_task(me, "x18_soc_codedoor_1_open_task", "st_soc_codedoor_1_open_name", "st_soc_codedoor_1_open_descr")
			L.give_item(nil, "dev_document_2_x18", 1)
			L.give_item(nil, "dev_document_3_x18", 1)
			-- Bullet and Serega
			L.flag_give("VAL_ESCORT_TASK_START")
			L.flag_give("VAL_SMART_TERRAIN_19_SPAWN_SQUAD_SPACE_RESTRICTOR_INFO")
			L.flag_give("VAL_SMART_TERRAIN_19_BANDIT_1_SQUAD_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("three documents held: BAR_DARKLAB_DOCUMENT_GAIN", not L.on_server() or L.flag_has("BAR_DARKLAB_DOCUMENT_GAIN"))
			expect_task(me, "val_start_take_the_documents_to_the_barmen_quest_task", "st_val_start_take_the_documents_to_the_barmen_quest_task_name",
				"st_val_start_take_the_documents_to_the_barmen_quest_task_descr")
			expect_task(me, "val_soc_prisoner_task", "st_soc_prisoner_name", "st_soc_prisoner_descr")
			qa.assert("Barkeep state: docs (asks for the X18 documents)", coop_soc_bar.state() == "docs", tostring(coop_soc_bar.state()))
			-- Serega dies: the prisoner task fails by flag, nothing else waits on him
			L.flag_give("VAL_SMART_TERRAIN_20_DUTY_1_SQUAD_DEAD")
			-- no mod-only task anywhere
			for _, id in ipairs(FORBIDDEN) do
				qa.assert("mod-only task is never given: " .. id, task_info(me, id) == nil)
			end
			return L.wait(2)
		end,
		function(c)
			-- the Barkeep hand-in of the three documents (the dialog actions), with Sidorovich as the stand-in listener (the Barkeep is not online on Cordon)
			local me = L.local_player()
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			qa.assert("a stand-in NPC for the dialog actions is online", sid ~= nil)
			local pre = safe(function()
				return dialogs_coop_l05_bar.if_actor_has_dev_document_1_x18(me, sid) and dialogs_coop_l05_bar.if_actor_has_dev_document_2_x18(me, sid)
					and dialogs_coop_l05_bar.if_actor_has_dev_document_3_x18(me, sid) end)
			qa.assert("phrase 172 precondition: the player holds the three documents", pre == true)
			L.set_money(nil, 1000)
			if sid ~= nil then
				safe(function() coop_soc_bar.take_x18_docs(me, sid) end)
				safe(function() coop_soc_bar.reward_x18(me, sid) end)
			end
			L.flag_give(DONE)       -- phrase 172 gives it with the actions
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			local m = L.money(nil)
			ev("money after the hand-in: " .. tostring(m))
			qa.assert("hand-in paid 10000 (1000 -> 11000)", m == 11000, tostring(m))
			for i = 1, 3 do
				local n = L.count_item(nil, "dev_document_" .. i .. "_x18")
				qa.assert("document " .. i .. " left the player (went to the NPC)", n == 0, tostring(n))
			end
			qa.assert("Barkeep state afterwards: offers the X16 job", coop_soc_bar.state() == "x16offer", tostring(coop_soc_bar.state()))
			qa.assert("the Yantar line starts with the X16 job (dialog, patch bar_soc_quests), not here", task_info(me, "bar_start_go_to_yantar_quest_task") == nil)
			qa.assert("val_come_to_trader is not offered once the documents are at the Barkeep", task_info(me, "val_start_get_out_via_south_gate_quest_task") == nil)
			-- voice
			local lang = safe(function() return coop_soc_opening.voice_lang() end) or "?"
			ev("voice language of this player: " .. tostring(lang))
			for _, id in ipairs(coop_soc_bar.VOICE_IDS) do
				local path = "characters_voice\\dialogs\\eng\\bar_bar_barmen_start_" .. id
				qa.assert("English recording exists for phrase " .. id, getFS():exist("$game_sounds$", path .. ".ogg") ~= nil and getFS():exist("$game_sounds$", path .. ".ogg") ~= false, path)   -- exist() returns a file object, not a boolean
				local p = coop_soc_bar.voice_path(id)
				if lang == "eng" then
					qa.assert("voice_language eng: phrase " .. id .. " plays the English file", p == path, tostring(p))
				elseif lang == "rus" then
					qa.assert("voice_language rus: phrase " .. id .. " plays the Russian file", p == "characters_voice\\dialogs\\bar_bar_barmen_start_" .. id, tostring(p))
				end
			end
			qa.assert("a phrase without a recording is silent", coop_soc_bar.voice_path("211") == nil)
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			if sid ~= nil then
				coop_soc_bar.say_221(sid, me)
				ev("say_221 played: " .. tostring(coop_soc_bar.played))
				if lang == "eng" and not safe(OnClient) then
					ev("say_221: this VM is the server role (OnClient() false), say() only plays on the client role: play assert skipped")
				elseif lang == "eng" then
					qa.assert("say_221 hands the English file to the sound engine", coop_soc_bar.played == "characters_voice\\dialogs\\eng\\bar_bar_barmen_start_221", tostring(coop_soc_bar.played))
				end
			end
			return L.screenshot("socdv_done")
		end,
	}
	L.task("socdv", steps)
end)
