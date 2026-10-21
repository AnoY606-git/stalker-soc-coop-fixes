--@qa_lib
-- Agroprom and Agroprom underground quest chain, original SoC order (test only, never shipped). Listen host + one client; the hook runs in every
-- process, so every client asserts its OWN task list and the server role asserts that the tick served every player.
--   Agroprom surface:      run_coop.ps1 -Map coop_l03_agroprom -Mode listen -Clients 1 -Owner agrsoc -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 150 -ResultDir <dir>
--   Agroprom underground:  the same with -Map coop_l03_agroprom_underground -Owner agrsocu (the hook picks its part by the level name)
--   then:  python tools\stalker_xrmpe\qa_verdict.py <dir>
-- Surface part (flags are fast-forwarded the way the restrictors / squads / Mole would set them):
--   1. nothing of the chain before the arrival; arrival flag -> "Get information about Strelok" and "Help the stalkers" for every player, SoC titles
--   2. the call of Mole (camera flight flag) -> "Save Mole" for every player; Mole waits at the well -> the first task shows objective 2 text
--   3. first soldier squad dead -> "Help the stalkers" is over; MOLE DIES before the talk (squad death flag) -> the route flag is given by the
--      fallback, "Save Mole" is over (failed), the first task is over and "Find Strelok's group's stash" (go down) is given to every player
--   4. the military documents case in an inventory sets the documents flag (the Cordon task follows it)
-- Underground part: stash task for every player with its SoC title, stash found (player at the box) -> objective 2 text, the flash drive in an
--   inventory -> flag, objective 3 text, "Find out what happened to Ghost" for every player; surface flag -> stash task over
-- Lines in qa_events.log:  AGRSOC ...   (the tick logs  SOCAGR GIVE_TASK <task> player=<id>  for each player)
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("AGRSOC " .. s) end

local MOLE_TALK = "AGR_SMART_TERRAIN_7_STALKER_MOLE_TALK_TO_THE_STALKER_MOLE_STOP_DIALOG_INFO"
local MAIN, HSTK, HKROT, DOWN = "agr_start_follow_the_stalker_mole_quest_task", "agr_soc_help_stalkers_task",
	"agr_start_save_the_stalker_mole_quest_task", "agr_start_go_to_the_agroprom_underground_quest_task"
local STASH, GHOST = "agru_start_find_the_shooter_hiding_place_task", "agr_soc_find_ghost_task"
local RETIRED = { "agr_start_talk_to_the_stalker_mole_quest_task", "agr_start_break_into_a_military_base_quest_task",
	"agr_start_the_destination_is_a_bar_quest_task", "agru_start_return_to_the_surface_task" }

local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { state = safe(function() return t:get_state() end),
		title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

-- a task is "over" when it is gone from the in-progress list or its state is not in progress (1)
local function over(lo, id)
	local ti = task_info(lo, id)
	return ti == nil or (ti.state ~= nil and ti.state ~= 1)   -- get_state() is nil in this build (snapshot shows "present"): in progress = present in get_task(id, true), closed = gone
end

local function served(id, want)
	if not OnServer() then return end
	local n = safe(function() return coop_scn_agroprom_soc.served(id) end) or -1
	qa.assert("server tick served every player with " .. id .. " (" .. tostring(n) .. " of " .. tostring(want) .. ")", n == want, tostring(n))
end

local function has_title(me, id, title_id)
	local ti = task_info(me, id)
	qa.assert("task given to the local player: " .. id, ti ~= nil)
	if ti then
		local want = tr(title_id)
		ev("TASK " .. id .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
		qa.assert(id .. " title is the SoC title (" .. tostring(want) .. ")", ti.title == want and want ~= title_id, tostring(ti.title))
		qa.assert(id .. " has a description", ti.descr ~= nil and ti.descr ~= "" and not string.find(ti.descr, "coop_soc_", 1, true), tostring(ti.descr))
	end
	return ti
end

local function surface()
	return {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			for _, id in ipairs({ MAIN, HSTK, HKROT, DOWN, STASH, GHOST }) do
				qa.assert("before the arrival no chain task: " .. id, task_info(me, id) == nil)
			end
			L.flag_give("AGR_STALKER_HELP_1_INFO")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			local npl = #L.players()
			ev("players=" .. npl)
			local m = has_title(me, MAIN, "st_agr_start_follow_the_stalker_mole_quest_task_name")
			if m then
				local want1 = tr("st_agr_start_follow_the_stalker_mole_quest_task_descr")
				qa.assert("first task shows objective 1 (Meet Mole's group): " .. tostring(want1), m.descr == want1, tostring(m.descr))
			end
			has_title(me, HSTK, "coop_soc_agr_help_stalkers_name")
			qa.assert("Save Mole is not given before the call", task_info(me, HKROT) == nil)
			served(MAIN, npl)
			served(HSTK, npl)
			L.flag_give("AGR_THE_ORDER_TO_KILL_STALKER_SPACE_RESTRICTOR_INFO")      -- the call of Mole (camera flight)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			local npl = #L.players()
			has_title(me, HKROT, "st_agr_start_save_the_stalker_mole_quest_task_name")
			served(HKROT, npl)
			L.flag_give("AGR_START_FOLLOW_THE_STALKER_MOLE_QUEST_TASK_THE_AND_INFO")   -- Mole waits at the well
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			local m = task_info(me, MAIN)
			local want2 = tr("st_agr_start_talk_to_the_stalker_mole_quest_task_descr")
			qa.assert("first task shows objective 2 (Get info from Mole): " .. tostring(want2), m ~= nil and m.descr == want2, m and tostring(m.descr) or "task gone")
			L.flag_give("AGR_SMART_TERRAIN_5_MILITARY_1_SQUAD_DEAD")
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("first soldier squad dead: 'Help the stalkers' is over", over(me, HSTK))
			qa.assert("Save Mole is still on (second squad alive)", not over(me, HKROT))
			-- a real kill when Mole is online; the squad death flag does the rest (the walker logic makes Mole invulnerable, so the flag is what the squad gives)
			local mole = safe(function() return L.find_online("agr_smart_terrain_7_stalker_mole") end)
			ev("Mole online: " .. tostring(mole ~= nil))
			qa.assert("route flag not set before Mole dies", not L.flag_has(MOLE_TALK))
			L.flag_give("AGR_SMART_TERRAIN_4_STALKER_MOLE_SQUAD_DEAD")                 -- Mole dies before the talk
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			local npl = #L.players()
			qa.assert("FALLBACK: Mole dead -> the stash route flag is given (no soft lock)", L.flag_has(MOLE_TALK))
			qa.assert("Mole dead: Save Mole is over (failed)", over(me, HKROT))
			qa.assert("Mole dead: the first task is over (completed by the route flag)", over(me, MAIN))
			has_title(me, DOWN, "st_agr_start_go_to_the_agroprom_underground_quest_task_name")
			served(DOWN, npl)
			for _, id in ipairs(RETIRED) do
				qa.assert("retired task never given: " .. id, task_info(me, id) == nil)
			end
			-- 4. the documents case
			L.give_item(nil, "agr_safe_container_1", 1)
			return L.wait(6)
		end,
		function(c)
			qa.assert("the case with the documents sets the flag the Cordon task follows", L.flag_has("AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"))
			return L.screenshot("agrsoc_surface")
		end,
		function(c) ev("surface part done") return L.done() end,
	}
end

local function underground()
	return {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			local npl = #L.players()
			ev("players=" .. npl)
			local s = has_title(me, STASH, "st_agru_start_find_the_shooter_hiding_place_task_name")
			if s then
				local w1 = tr("st_agru_start_find_the_shooter_hiding_place_task_descr")
				qa.assert("stash task shows objective 1 (Find the stash): " .. tostring(w1), s.descr == w1, tostring(s.descr))
			end
			served(STASH, npl)
			qa.assert("no Ghost task before the flash drive", task_info(me, GHOST) == nil)
			for _, id in ipairs(RETIRED) do
				qa.assert("retired task never given: " .. id, task_info(me, id) == nil)
			end
			return L.teleport(nil, { -69.8, -5.2, -62.5 })
		end,
		function(c, ok, how)
			ev("teleport to the stash: " .. tostring(ok) .. " " .. tostring(how))
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("a player at the stash box: AGRU_SOC_STASH_FOUND", L.flag_has("AGRU_SOC_STASH_FOUND"))
			local s = task_info(me, STASH)
			local w2 = tr("coop_soc_agru_flash_descr")
			qa.assert("stash task shows objective 2 (Find information about Strelok in the stash): " .. tostring(w2), s ~= nil and s.descr == w2, s and tostring(s.descr) or "task gone")
			qa.assert("flash drive flag not set yet", not L.flag_has("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO"))
			L.give_item(nil, "dev_flash_agru", 1)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			local npl = #L.players()
			qa.assert("flash drive in the inventory: flag set", L.flag_has("AGRU_START_FIND_THE_SHOOTER_HIDING_PLACE_TASK_INFO"))
			local s = task_info(me, STASH)
			local w3 = tr("st_agru_start_return_to_the_surface_task_descr")
			qa.assert("stash task shows objective 3 (the way out): " .. tostring(w3), s ~= nil and s.descr == w3, s and tostring(s.descr) or "task gone")
			has_title(me, GHOST, "coop_soc_agr_ghost_name")
			served(GHOST, npl)
			L.flag_give("AGRU_START_RETURN_TO_THE_SURFACE_TASK_END_INFO")      -- back on the surface (the surface restrictor sets it)
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("back on the surface: the stash task is over", over(me, STASH))
			qa.assert("the Ghost task goes on (Yantar)", not over(me, GHOST))
			return L.screenshot("agrsoc_underground")
		end,
		function(c) ev("underground part done") return L.done() end,
	}
end

qa.once("agrsoc_run", function(t, lo)
	local lvl = L.level_name()
	ev("start level=" .. tostring(lvl) .. " lang=" .. tostring(L.language()))
	if lvl == "coop_l03_agroprom" then
		L.task("agroprom surface", surface())
	elseif lvl == "coop_l03_agroprom_underground" then
		L.task("agroprom underground", underground())
	else
		ev("not an Agroprom level, nothing to do")
	end
end)
