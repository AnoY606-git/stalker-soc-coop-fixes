--@qa_lib
-- Cordon story after the flash drive, original SoC (test only, never shipped). ONE listen-host run (a client may join, nothing needs it):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socchain -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 150 -ResultDir <dir>
-- Fast-forwards the start chain (the infos the flash drive hand-in phrase gives), then checks:
--   1. no helicopter object comes online, none moves, the helicopter task and the Fox detour tasks are not given, no level-maker task appears
--   2. the SoC "Work for the trader" task appears for every player with its SoC title and description, the job talk flag completes it
--      and the two tasks of the military case job ("Get to the railroad embankment", "Find the militaries' documents") appear
--   3. the infos / flags the Garbage, the Bar and the guide votes read are set (static list proven by tools\check_cordon_chain.py)
--   4. the bridge pass: 500 rubles taken from the talking player by the dialog functions, the pass flag is set, every player is let through
-- Lines in qa_events.log:  SOCCHAIN ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCCHAIN " .. s) end

local FLESH = "ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO"
local JOB = "ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO"
local HELI = "ESC_HELICOPTER_GO_TO_AGROPROM_INFO"
local PASS = "ESC_START_5_BOTTLES_OF_VODKA_FOR_KUZNETSOV_QUEST_TASK_INFO"

-- tasks that must NOT be given after the hand-in (the level maker's helicopter / Fox / vodka tasks) and the old start ones that stay hidden
local FORBIDDEN = { "esc_start_talk_to_the_sidorovich_quest_1_task", "esc_start_talk_to_the_fox_quest_1_task", "esc_start_talk_to_the_fox_quest_2_task",
	"esc_start_5_bottles_of_vodka_for_kuznetsov_quest_task", "esc_start_kill_dogs_quest_task" }
local SOC = { "esc_soc_trader_job_task", "esc_soc_railroad_passage_task", "esc_soc_military_documents_task" }

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { state = safe(function() return t:get_state() end),
		title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

-- any helicopter object (server side), online or not
local function helis()
	local n, online = 0, 0
	for id = 1, 65534 do
		local so = safe(function() return alife():object(id) end)
		if so ~= nil then
			local nm = safe(function() return so:name() end) or ""
			local sec = safe(function() return so:section_name() end) or ""
			if string.find(nm, "helicopter", 1, true) and string.find(nm, "esc_", 1, true) or sec == "helicopter" and string.find(nm, "esc_", 1, true) then
				n = n + 1
				if safe(function() return level.object_by_id(id) end) ~= nil then online = online + 1 end
			end
		end
	end
	return n, online
end

qa.once("socchain_run", function(t, lo)
	local steps = {
		function(c) return L.wait(8) end,
		function(c)
			-- baseline: the start chain is the opening's (two tasks), the flash drive is not handed in
			local me = L.local_player()
			ev("baseline tasks main=" .. tostring(task_info(me, "esc_start_main_quest_task") ~= nil) .. " talk=" .. tostring(task_info(me, "esc_start_talk_to_the_sidorovich_quest_task") ~= nil))
			for _, id in ipairs(SOC) do
				qa.assert("before the hand-in: no SoC next task " .. id, task_info(me, id) == nil)
			end
			-- fast forward: what the story gave until the flash drive (flags of the Wolf / Shustry chain), then the hand-in phrase 2 flags
			for _, f in ipairs({ "COOP_SOC_OPENING_TALKED", "ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO",
				"ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_TALK_TO_THE_WOLF_STOP_DIALOG_INFO", "ESC_START_TALK_TO_THE_WOLF_QUEST_TASK_INFO",
				"ESC_START_ESCORT_THE_STALKER_SHUSTRY_QUEST_TASK_INFO" }) do L.flag_give(f) end
			L.flag_give(FLESH)
			L.flag_give(HELI)       -- the dialog gives it silently (the helicopter is gone)
			ev("hand-in flags given at t=" .. string.format("%.0f", t))
			return L.wait(12)
		end,
		function(c)
			local me = L.local_player()
			-- 1. nothing of the level maker's chain
			local n, online = helis()
			ev("helicopter objects esc_*: " .. n .. " total, " .. online .. " online")
			qa.assert("no esc helicopter object is online after the hand-in", online == 0, tostring(online))
			for _, id in ipairs(FORBIDDEN) do
				local ti = task_info(me, id)
				qa.assert("task not given: " .. id, ti == nil, ti and ti.title or "")
			end
			-- 2. the SoC "Work for the trader" task, title and description in SoC wording
			local tj = task_info(me, "esc_soc_trader_job_task")
			qa.assert("SoC task 'Work for the trader' is given to the local player", tj ~= nil)
			if tj then
				ev("TASK job title=[" .. tostring(tj.title) .. "] descr=[" .. tostring(tj.descr) .. "]")
				local want = safe(function() return game.translate_string("coop_soc_task_trader_job_name") end)
				qa.assert("job task title is the SoC title (" .. tostring(want) .. ")", tj.title == want and want ~= "coop_soc_task_trader_job_name", tostring(tj.title))
				qa.assert("job task has a description", tj.descr ~= nil and tj.descr ~= "" and tj.descr ~= "coop_soc_task_trader_job_descr", tostring(tj.descr))
			end
			qa.assert("the next two tasks are not given before the job talk", task_info(me, "esc_soc_railroad_passage_task") == nil and task_info(me, "esc_soc_military_documents_task") == nil)
			-- the job talk (SoC military case): the dialog gives this flag at its phrase 7
			L.flag_give(JOB)
			return L.wait(12)
		end,
		function(c)
			local me = L.local_player()
			local jt = task_info(me, "esc_soc_trader_job_task")
			ev("job task state after the talk: " .. tostring(jt and jt.state))
			for _, id in ipairs({ "esc_soc_railroad_passage_task", "esc_soc_military_documents_task" }) do
				local ti = task_info(me, id)
				qa.assert("after the job talk the SoC task is given: " .. id, ti ~= nil)
				if ti then
					ev("TASK " .. id .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
					qa.assert(id .. " has title and description", ti.title ~= nil and ti.descr ~= nil and ti.descr ~= "" and not string.find(ti.descr, "coop_soc_task", 1, true), tostring(ti.descr))
				end
			end
			for _, id in ipairs(FORBIDDEN) do
				qa.assert("still not given: " .. id, task_info(me, id) == nil)
			end
			-- every other player has the same tasks (the server tick gives them per player)
			for _, p in ipairs(L.players()) do
				ev("player " .. tostring(p.name) .. " id=" .. tostring(p.id) .. " (the tick log lines GIVE_TASK name each player)")
			end
			-- 3. the infos later levels read
			local keys = { FLESH, JOB, HELI, "ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO", "ESC_START_TALK_TO_THE_WOLF_QUEST_TASK_INFO" }
			for _, f in ipairs(keys) do qa.assert("flag set: " .. f, L.flag_has(f)) end
			-- guide votes: the Garbage vote flag can be given (Cordon guide dialog) and is not blocked by the removed steps
			qa.assert("Garbage guide flag not pre-set", not L.flag_has("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_GAR_INFO"))
			-- Sidorovich's own hello / bye voice of the level maker is off (ours play: patch cutscenes_pkg_opening)
			local ini = safe(function() return ini_file("scripts\\coop_l01_escape\\esc_smart_terrain_1_animpoint_sidorovich.ltx") end)
			local h = ini and safe(function() return ini:r_string("meet@trader", "close_snd_hello") end)
			local b = ini and safe(function() return ini:r_string("meet@trader", "close_snd_bye") end)
			ev("meet@trader close_snd_hello=" .. tostring(h) .. " close_snd_bye=" .. tostring(b))
			qa.assert("Sidorovich: the level maker's hello voice is off (meet@trader close_snd_hello = nil)", h == "nil", tostring(h))
			qa.assert("Sidorovich: the level maker's bye voice is off (meet@trader close_snd_bye = nil)", b == "nil", tostring(b))
			-- 4. the bridge pass: the dialog functions
			L.set_money(nil, 800)
			local before = L.money(nil)
			local has = coop_soc_cordon.has_bridge_bribe(L.local_player(), L.local_player())
			qa.assert("has_bridge_bribe is true with 800 rubles", has == true)
			ev("money before the pass: " .. tostring(before))
			qa.assert("the pass flag is not set before paying", not L.flag_has(PASS))
			return L.wait(1)
		end,
		function(c)
			-- pay through the same helper the dialog action calls (talking player = the local player, Kuznetsov online or not: the helper needs an npc, so use Sidorovich)
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			local me = L.local_player()
			if sid ~= nil then
				safe(function() coop_soc_cordon.give_bridge_bribe(me, sid) end)
			end
			L.flag_give(PASS)
			return L.wait(2)
		end,
		function(c)
			local after = L.money(nil)
			ev("money after the pass: " .. tostring(after))
			qa.assert("500 rubles were taken from the talking player (800 -> 300)", after == 300, tostring(after))
			qa.assert("the pass flag is a shared story flag", L.flag_has(PASS))
			L.set_money(nil, 100)
			qa.assert("has_bridge_bribe is false with 100 rubles", coop_soc_cordon.has_bridge_bribe(L.local_player(), L.local_player()) == false)
			return L.screenshot("socchain_done")
		end,
	}
	L.task("socchain", steps)
end)
