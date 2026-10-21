--@qa_lib
-- Bar / Rostok quest chain of the original SoC (test only, never shipped). ONE listen-host run with one extra client (two players):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner barsoc -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 200 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir>
-- (Cordon is enough: the chain is driven by shared story flags and the tick runs on every level. The Bar, Rostok and the NPCs themselves are not online
--  there; the dialog actions run with Sidorovich as the stand-in listener, the real dialog windows are covered by the Lua mock test, tests\mock_test.py.)
-- Fast-forwards the chain with the flags the story gives, then asserts on EVERY process (host and client each check their own player):
--   1. the X16 documents job: ONE task, its description follows the objectives (talk to the scientists / find the X16 documents / bring them to the Barkeep),
--      the hand-in functions take lab_x16_documents and the flag ends the task; the Barkeep states
--   2. the Brain Scorcher job: one task from the Barkeep flags, over when the party is on the Radar level
--   3. the hunter's rifle: find it, return it (4000 paid, rifle taken); a rifle in an inventory sets the flag
--   4. Kruglov: get through, talk, lead to Yantar, talk (every step to every player), the mod-only tasks are never given
--   5. server side: coop_soc_barros.who(task) lists EVERY player; the three new English Barkeep recordings exist, are silent with voice_language rus
-- Lines in qa_events.log:  SOCBARROS ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCBARROS " .. s) end

local DONE18 = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO"
local GO_MIL = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_MILITARY_STOP_DIALOG_INFO"
local HACCEPT = "BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_STOP_DIALOG_INFO"
local HDONE = "BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_IDLE_STOP_DIALOG_INFO"
local X16 = "bar_start_go_to_yantar_quest_task"
local RADAR = "bar_start_go_to_military_quest_task"
local HFIND, HRET = "bar_start_find_the_family_gun_quest_task", "bar_soc_hunter_return_task"
local KHELP, KTALK, KESC, KBRING = "ros_start_help_kruglov_quest_task", "ros_soc_kruglov_talk_task", "ros_start_escort_kruglov_to_yantar_quest_task",
	"ros_soc_kruglov_bring_task"
local FORBIDDEN = { "ros_start_go_to_yantar_quest_task", "bar_start_the_meeting_place_cannot_be_changed_1_quest_task",
	"bar_start_the_meeting_place_cannot_be_changed_2_quest_task", "bar_start_the_meeting_place_cannot_be_changed_3_quest_task",
	"mil_start_go_to_radar_quest_task" }

local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

-- in progress = present in get_task(id, true); closed = gone (get_state() is nil in this build)
local function over(lo, id) return task_info(lo, id) == nil end

local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_barros.who(id) end) or {}
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
			qa.assert(id .. " description is the SoC objective (" .. descr_id .. ")", ti.descr == tr(descr_id) and ti.descr ~= descr_id, tostring(ti.descr))
		end
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

qa.once("barsoc_run", function(t, lo)
	local steps = {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			for _, id in ipairs({ X16, RADAR, HFIND, HRET, KHELP, KTALK, KESC, KBRING }) do
				qa.assert("before the story: not given " .. id, task_info(me, id) == nil)
			end
			-- X18 documents handed in: the Barkeep offers the X16 job, nothing is given yet; accepting the job gives the ONE task
			L.flag_give(DONE18)
			qa.assert("Barkeep after the X18 hand-in: offers the X16 job", coop_soc_bar.state() == "x16offer", tostring(coop_soc_bar.state()))
			L.flag_give("BAR_X16_DOCUMENTS_START")
			qa.assert("Barkeep after accepting: waits", coop_soc_bar.state() == "x16wait", tostring(coop_soc_bar.state()))
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, X16, "st_bar_start_go_to_yantar_quest_task_name", "st_bar_start_go_to_yantar_quest_task_descr")
			L.flag_give("YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO")      -- the first talk with Sakharov
			return L.wait(4)
		end,
		function(c)
			local me = L.local_player()
			local ti = task_info(me, X16)
			qa.assert("after the talk with Sakharov: 'Find the X16 documents'", ti ~= nil and ti.descr == tr("coop_soc_x16_look_descr"), ti and tostring(ti.descr) or "gone")
			L.give_item(nil, "lab_x16_documents", 1)                                                       -- Ghost's documents
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("a player holds lab_x16_documents: YAN_X16_DOCUMENTS_GAIN (server)", not L.on_server() or L.flag_has("YAN_X16_DOCUMENTS_GAIN"))
			local ti = task_info(me, X16)
			qa.assert("documents found: 'Bring the documents to the Barkeep'", ti ~= nil and ti.descr == tr("coop_soc_x16_bring_descr"), ti and tostring(ti.descr) or "gone")
			qa.assert("Barkeep asks for the X16 documents", coop_soc_bar.state() == "x16docs", tostring(coop_soc_bar.state()))
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			qa.assert("a stand-in NPC for the dialog actions is online", sid ~= nil)
			qa.assert("phrase 1211 precondition: the player holds the documents", safe(function() return coop_soc_bar.has_x16_docs(me, sid) end) == true)
			if sid ~= nil then safe(function() coop_soc_bar.take_x16_docs(me, sid) end) end
			L.flag_give("BAR_X16_DOCUMENTS_DONE")                                                          -- phrase 1211 gives it with the action
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("the documents left the player (went to the Barkeep)", L.count_item(nil, "lab_x16_documents") == 0, tostring(L.count_item(nil, "lab_x16_documents")))
			qa.assert("the X16 task is over once the Barkeep has the documents", over(me, X16))
			qa.assert("Barkeep offers the Scorcher job", coop_soc_bar.state() == "radaroffer", tostring(coop_soc_bar.state()))
			qa.assert("the Scorcher job is not started by itself", task_info(me, RADAR) == nil)
			L.flag_give("BAR_DEACTIVATE_RADAR_START")                                                      -- phrase 1312 gives both
			L.flag_give(GO_MIL)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, RADAR, "st_bar_start_go_to_military_quest_task_name", "st_bar_start_go_to_military_quest_task_descr")
			qa.assert("Barkeep greets while the job runs", coop_soc_bar.state() == "radar", tostring(coop_soc_bar.state()))
			L.flag_give("BAR_START_GO_TO_MILITARY_QUEST_TASK_INFO")
			L.flag_give("MIL_START_GO_TO_RADAR_QUEST_TASK_INFO")                                          -- the party is on the Radar level
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("the Scorcher task is over on the Radar level (the Radar tasks take over)", over(me, RADAR))
			-- hunter
			L.flag_give(HACCEPT)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, HFIND, "st_bar_start_find_the_family_gun_quest_task_name", "st_bar_start_find_the_family_gun_quest_task_descr")
			qa.assert("hunter greeting: waits for the rifle", coop_soc_hunter.state() == "wait", tostring(coop_soc_hunter.state()))
			L.give_item(nil, "wpn_toz34_m2", 1)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("the rifle in an inventory: BAR_HUNTER_RIFLE_FOUND (server)", not L.on_server() or L.flag_has("BAR_HUNTER_RIFLE_FOUND"))
			qa.assert("'Find the family rifle' is over", over(me, HFIND))
			expect_task(me, HRET, "st_bar_start_find_the_family_gun_quest_task_name", "coop_soc_hunter_return_descr")
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			qa.assert("hunter hand-in precondition: the player holds the rifle", safe(function() return coop_soc_hunter.has_rifle(me, sid) end) == true)
			L.set_money(nil, 1000)
			if sid ~= nil then
				safe(function() coop_soc_hunter.take_rifle(me, sid) end)
				safe(function() coop_soc_hunter.reward(me, sid) end)
			end
			L.flag_give(HDONE)
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			local m = L.money(nil)
			qa.assert("the hunter paid 4000 (1000 -> 5000)", m == 5000, tostring(m))
			qa.assert("the rifle left the player", L.count_item(nil, "wpn_toz34_m2") == 0)
			qa.assert("'Return the rifle' is over", over(me, HRET))
			qa.assert("hunter greeting afterwards: thanks", coop_soc_hunter.state() == "done")
			-- Kruglov
			L.flag_give("ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_END_INFO")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, KHELP, "st_ros_start_help_kruglov_quest_task_name", "st_ros_start_help_kruglov_quest_task_descr")
			L.flag_give("ROS_SMART_TERRAIN_3_KILLER_1_SQUAD_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("'Get through to Kruglov' is over once the Mercs are dead", over(me, KHELP))
			expect_task(me, KTALK, "st_ros_start_help_kruglov_quest_task_name", "coop_soc_kruglov_talk_descr")
			qa.assert("the escort waits until Kruglov is reached", task_info(me, KESC) == nil)
			L.flag_give("BAR_KRUGLOV_FOLLOW_ACTOR")                                                       -- Kruglov speaks and walks off (his logic)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("'Talk to professor Kruglov' is over", over(me, KTALK))
			expect_task(me, KESC, "st_ros_start_escort_kruglov_to_yantar_quest_task_name", "st_ros_start_escort_kruglov_to_yantar_quest_task_descr")
			L.flag_give("YAN_SMART_TERRAIN_1_WALKER_KRUGLOV_GO_TO_SAXAROV_INFO")                          -- the party is on Yantar
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("the escort is over on Yantar", over(me, KESC))
			expect_task(me, KBRING, "st_ros_start_escort_kruglov_to_yantar_quest_task_name", "coop_soc_kruglov_bring_descr")
			L.flag_give("YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO")           -- the first talk with Kruglov on Yantar
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("'Talk to Kruglov' is over after the talk", over(me, KBRING))
			for _, id in ipairs(FORBIDDEN) do
				qa.assert("mod-only / hidden task is never given: " .. id, task_info(me, id) == nil)
			end
			-- voice of the three new Barkeep recordings
			local lang = safe(function() return coop_soc_opening.voice_lang() end) or "?"
			ev("voice language of this player: " .. tostring(lang))
			for _, id in ipairs({ "121", "13121", "1314" }) do
				local path = "characters_voice\\dialogs\\eng\\bar_bar_barmen_start_" .. id
				qa.assert("English recording exists for phrase " .. id, getFS():exist("$game_sounds$", path .. ".ogg") == true, path)
				local p = coop_soc_bar.voice_path(id)
				if lang == "eng" then
					qa.assert("voice_language eng: phrase " .. id .. " plays the English file", p == path, tostring(p))
				elseif lang == "rus" then
					qa.assert("voice_language rus: phrase " .. id .. " plays the Russian file", p == "characters_voice\\dialogs\\bar_bar_barmen_start_" .. id, tostring(p))
				end
			end
			qa.assert("a phrase without a recording is silent", coop_soc_bar.voice_path("1316") == nil)
			return L.screenshot("barsoc_done")
		end,
	}
	L.task("barsoc", steps)
end)
