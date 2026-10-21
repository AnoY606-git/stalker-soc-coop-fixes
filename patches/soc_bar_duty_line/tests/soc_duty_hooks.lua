--@qa_lib
-- Bar Duty / Freedom line of the original SoC (test only, never shipped). ONE listen-host run with one extra client (two players):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socduty -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 300 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix SD
-- Phase A (Cordon, the chain is driven by shared story flags and the tick runs on every level): the host fast-forwards the flags the dialogs
-- give, EVERY process (host and client, each checks its own player) asserts:
--   1. the six tasks with their titles (SoC strings) and the description of the moment (pass -> test -> Bulldog 6 -> oath; veterans; Tyran; Lukash)
--   2. the server tick gave each task to EVERY player (coop_soc_duty.who)
--   3. the dialog states of Voronin / the gate commander / the Barkeep jobs follow the flags
--   4. the spawn sections of the new NPCs and the two PDAs exist in the loaded configs, the characters and their dialogs are registered
--   5. fallbacks: a dead NPC does not block a step (SOCDUTY_FORCE_DEAD)
-- The NPC part (the commander, Ivantsov, Lucky, Tyran online at the SoC positions) is tests\soc_duty_npcs_hooks.lua (travel to the Bar / Wild Territory).
-- Lines in qa_events.log:  SOCDUTY ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCDUTY " .. s) end
local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_duty.who(id) end) or {}
	local set = {}
	for _, pid in ipairs(got) do set[pid] = true end
	local n, miss = 0, {}
	for pid, a in pairs(db.mp_actors) do
		n = n + 1
		if not set[pid] then miss[#miss + 1] = tostring(pid) end
	end
	return (#miss == 0 and n > 0), "players=" .. n .. " missing=" .. table.concat(miss, ",")
end

local function expect_task(me, id, step)
	local ti = task_info(me, id)
	qa.assert("task given to this player: " .. id, ti ~= nil)
	if ti then
		local base = "coop_soc_duty_" .. id
		ev("TASK " .. id .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
		qa.assert(id .. " title is the SoC / patch title", ti.title == tr(base .. "_name") and ti.title ~= base .. "_name", tostring(ti.title))
		if step ~= nil then
			qa.assert(id .. " description of the moment (step " .. step .. ")", ti.descr == tr(base .. "_s" .. step) and ti.descr ~= base .. "_s" .. step, tostring(ti.descr))
		end
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

local function state(fn) return safe(function() return coop_soc_duty[fn]() end) end

qa.once("socduty_run", function(t, lo)
	local steps = {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			-- the configs
			local ini = system_ini()
			for _, sec in ipairs({ "soc_duty_guard_commander", "soc_duty_ivancov", "soc_vet_lucky", "soc_vet_1", "soc_vet_2", "soc_tyran", "soc_merc_1", "soc_merc_2",
				"soc_merc_3", "soc_merc_4", "bar_lucky_pda", "bar_tiran_pda" }) do
				qa.assert("config section exists: " .. sec, safe(function() return ini:section_exist(sec) end) == true)
			end
			qa.assert("Lucky's PDA name", tr("coop_soc_duty_lucky_pda_name") ~= "coop_soc_duty_lucky_pda_name")
			for _, id in ipairs({ "bar_soc_dolg_community_task", "bar_soc_dolg_test_task", "bar_soc_rg6_task", "bar_soc_veterans_task", "bar_soc_ambush_task", "bar_soc_leader_task" }) do
				qa.assert("before the story: not given " .. id, task_info(me, id) == nil)
			end
			-- the gate commander sold the pass
			L.flag_give("BAR_DOLG_BASE_PASS"); L.flag_give("BAR_DOLG_COMMUNITY_START"); L.flag_give("BAR_DOLG_COMMUNITY_LEADER")
			qa.assert("gate state: pass", state("gc_st_pass") == true)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_dolg_community_task", 3)
			L.flag_give("BAR_DOLG_VETERAN_START")                           -- Ivantsov's test accepted
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_dolg_test_task", 1)
			L.flag_give("BAR_ARENA_PSEUDODOG_DEFEATED")
			L.flag_give("BAR_SVOBODA_RG6_START")                            -- Voronin's job
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_dolg_test_task", 0)
			expect_task(me, "bar_soc_rg6_task", (safe(function() return system_ini():section_exist("mil_soc_cook") end) == true) and 0 or 1)   -- soc_mil_courier owns the Bulldog 6 job when it is installed
			qa.assert("Voronin state: hub (no rifle yet)", state("vo_state") == "hub", tostring(state("vo_state")))
			L.flag_give("BAR_DOLG_VETERAN_DONE")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_dolg_community_task", 2)              -- "Prove your loyalty": the reference is there, the rifle is not
			L.flag_give("MIL_SVOBODA_RG6_GAIN"); L.flag_give("BAR_SVOBODA_RG6_DONE")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_dolg_community_task", 0)              -- the oath
			qa.assert("Voronin state: oath", state("vo_state") == "oath", tostring(state("vo_state")))
			L.flag_give("BAR_DOLG_COMMUNITY_LEADER_DONE")
			L.flag_give("BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO")
			qa.assert("Barkeep: veterans job offered", safe(function() return coop_soc_duty.bj_vet_offer() end) == true)
			L.flag_give("BAR_KILL_VETERAN_START")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_veterans_task", 1)
			qa.assert("community task is over", true)
			L.flag_give("BAR_KILL_VETERAN_KILLED")
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			-- the PDA is made by the server (next to a player: Lucky does not exist on Cordon): a PDA item or the flag
			qa.assert("Lucky killed: the PDA is made", L.flag_has("SOC_DUTY_LUCKY_PDA_MADE") or not L.on_server())
			expect_task(me, "bar_soc_veterans_task", 0)
			L.flag_give("BAR_KILL_VETERAN_DONE")
			qa.assert("Barkeep: Tyran job offered", safe(function() return coop_soc_duty.bj_amb_offer() end) == true)
			L.flag_give("BAR_KILL_SVOBODA_AMBUSH_START")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_ambush_task", 1)
			SOCDUTY_FORCE_DEAD = { bar_svoboda_ambush_tiran = true }     -- Tyran dead (any cause)
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("Tyran dead: the flag", L.flag_has("BAR_KILL_SVOBODA_AMBUSH_KILLED") or not L.on_server())
			expect_task(me, "bar_soc_ambush_task", 0)
			SOCDUTY_FORCE_DEAD = nil
			L.flag_give("BAR_KILL_SVOBODA_AMBUSH_DONE")
			return L.wait(4)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("Voronin state: Freedom leader order offered", state("vo_state") == "koffer", tostring(state("vo_state")))
			L.flag_give("BAR_KILL_SVOBODA_LEADER_START")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "bar_soc_leader_task", 1)
			SOCDUTY_FORCE_DEAD = { mil_smart_terrain_3_freedom_lukash = true }
			return L.wait(6)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("Lukash dead: the flag", L.flag_has("MIL_KILL_SVOBODA_LEADER_KILLED") or not L.on_server())
			expect_task(me, "bar_soc_leader_task", 0)
			SOCDUTY_FORCE_DEAD = nil
			qa.assert("Voronin state: kkilled", state("vo_state") == "kkilled", tostring(state("vo_state")))
			L.flag_give("BAR_KILL_SVOBODA_LEADER_DONE")
			return L.wait(4)
		end,
		function(c)
			qa.assert("Voronin state: kdone", state("vo_state") == "kdone", tostring(state("vo_state")))
			return L.screenshot("socduty_done")
		end,
	}
	L.task("socduty", steps)
end)
