--@qa_lib
-- The snitch Pavlik and the Bulldog 6 order of the original SoC (patch soc_mil_courier). Test only, never shipped. NOT RUN (the offline task did not
-- start the game): the commands below are for the coordinator. ONE listen-host run with one extra client (two players) per DEST:
--   DEST = "cordon" (default): everything that the shared flags drive, on Cordon: the nine task steps with their SoC titles and descriptions, given to
--                    EVERY player by the server tick, the Lukash states, the payment / suit actions (Sidorovich is the stand-in listener).
--   DEST = "mil":    the party travels to the Army Warehouses by the guide vote; there the server creates the Chef and the Bulldog 6, Pavlik after the
--                    job flag, the agent Ara and three bodyguards after the call; a player is teleported to the farmstead (the 45 m zone), the cues play.
-- run_coop takes ONE -Cfg only, so make a copy of this file with the other DEST value for the second run (-Owner socmilc / socmilcm):
--   powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socmilc `
--     -ExtraDir <stage>\gamedata -Hooks <repo>\patches\soc_mil_courier\tests\soc_milc_hooks.lua -Cfg no_respawn=1 -SoakSeconds 300 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix SC
-- (<stage> = python -I build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage, after apply_shared.py)
-- Lines in qa_events.log:  SOCMILC ...
local DEST = "cordon"   -- "cordon" | "mil"

local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCMILC " .. s) end
local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_milc.who(id) end) or {}
	local set = {}
	for _, pid in ipairs(got) do set[pid] = true end
	local n, miss = 0, {}
	for pid, a in pairs(db.mp_actors) do
		n = n + 1
		if not set[pid] then miss[#miss + 1] = tostring(pid) end
	end
	return (#miss == 0 and n > 0), "players=" .. n .. " missing=" .. table.concat(miss, ",")
end

local function T(id) return "st_" .. string.gsub(id, "_task$", "") end

-- the task is given to this player with the SoC title and objective text (the first step of a job also carries the SoC description)
local function expect_task(me, id, first)
	local ti = task_info(me, id)
	qa.assert("task given to this player: " .. id, ti ~= nil)
	if ti then
		ev("TASK " .. id .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
		qa.assert(id .. " title is the SoC title", ti.title == tr(T(id) .. "_name") and ti.title ~= T(id) .. "_name", tostring(ti.title))
		qa.assert(id .. " description is the SoC objective", ti.descr == tr(T(id) .. "_descr") and ti.descr ~= T(id) .. "_descr", tostring(ti.descr))
	end
	local ok, info = everyone_got(id)
	qa.assert("server tick gave " .. id .. " to every player (" .. tostring(info) .. ")", ok)
end

local function not_given(me, id)
	qa.assert("not given yet: " .. id, task_info(me, id) == nil)
end

local FLAGS = {
	LK = "MIL_SMART_TERRAIN_3_FREEDOM_LUKASH_HELP_FREEDOM_STOP_DIALOG_INFO", DONE = "MIL_SOC_LUKASH_JOB_DONE",
}

-------------------------------------------------------------------------------------------------------
-- DEST cordon
-------------------------------------------------------------------------------------------------------
local function cordon_steps()
	return {
		function(c) return L.wait(8) end,
		function(c)
			local me = L.local_player()
			for i = 1, 5 do not_given(me, "mil_soc_courier_" .. i .. "_task") end
			for i = 1, 4 do not_given(me, "mil_soc_rg6_" .. i .. "_task") end
			qa.assert("Lukash state before the report: new", coop_soc_milc.lukash_state() == "new" or coop_soc_milc.lukash_state() == "default",
				tostring(coop_soc_milc.lukash_state()))
			-- Lukash: the Duty job done and reported, the snitch job taken (phrases 3002 / 1501)
			L.flag_give(FLAGS.LK)
			L.flag_give(FLAGS.DONE)
			qa.assert("Lukash state: the snitch job is offered (coffer)", coop_soc_milc.lukash_state() == "coffer", tostring(coop_soc_milc.lukash_state()))
			L.flag_give("MIL_SOC_COURIER_START")
			qa.assert("Lukash state: job running (cwait)", coop_soc_milc.lukash_state() == "cwait", tostring(coop_soc_milc.lukash_state()))
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_courier_1_task")
			L.flag_give("MIL_SOC_COURIER_KHUTOR")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_courier_2_task")
			L.flag_give("MIL_SOC_COURIER_IN_KHUTOR")
			L.flag_give("MIL_SOC_COURIER_CALL")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_courier_3_task")
			-- step 4 needs the agent to exist (the marker): not on Cordon, so it must NOT be given here
			not_given(me, "mil_soc_courier_4_task")
			L.flag_give("MIL_SOC_COURIER_DEAD")
			L.flag_give("MIL_SOC_ARA_DEAD")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_courier_5_task")
			qa.assert("Lukash state: pay (cpay)", coop_soc_milc.lukash_state() == "cpay", tostring(coop_soc_milc.lukash_state()))
			-- the payment action of phrase 5001, with Sidorovich as the stand-in listener: 7000 once for this player
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			qa.assert("a stand-in NPC for the dialog actions is online", sid ~= nil)
			L.set_money(nil, 1000)
			if sid ~= nil then
				safe(function() coop_soc_milc.pay_courier(me, sid) end)
				safe(function() coop_soc_milc.pay_courier(me, sid) end)
			end
			return L.wait(4)
		end,
		function(c)
			local m = L.money(nil)
			ev("money after Lukash: " .. tostring(m))
			qa.assert("Lukash paid 7000 once to this player (1000 -> 8000)", m == 8000, tostring(m))
			qa.assert("after the payment: the Barrier offer (offer / capwait)", coop_soc_milc.lukash_state() ~= "cpay", tostring(coop_soc_milc.lukash_state()))
			L.flag_give("MIL_SOC_COURIER_DONE")
			-- Bulldog 6: Voronin gave the order (phrase 1111)
			for i = 1, 4 do not_given(L.local_player(), "mil_soc_rg6_" .. i .. "_task") end
			L.flag_give("MIL_SOC_RG6_START")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_rg6_1_task")
			L.flag_give("MIL_SOC_RG6_COOK_MET")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_rg6_2_task")
			L.flag_give("MIL_SOC_RG6_ASK")                  -- the third question of the drunk Chef
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			expect_task(me, "mil_soc_rg6_3_task")
			not_given(me, "mil_soc_rg6_4_task")
			-- a player holds the weapon: the server tick sees it (any_has)
			L.give_item(nil, "wpn_rg-6", 1)
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("the Bulldog 6 in the bag sets MIL_SOC_RG6_GOT", L.flag_has("MIL_SOC_RG6_GOT"))
			expect_task(me, "mil_soc_rg6_4_task")
			-- Voronin's hand-in actions (Sidorovich as the stand-in): the weapon goes, the suit comes, once
			local sid = safe(function() return L.find_online("esc_smart_terrain_1_trader_sidorovich") end)
			if sid ~= nil then
				safe(function() coop_soc_milc.take_rg6(me, sid) end)
				safe(function() coop_soc_milc.give_suit(me, sid) end)
				safe(function() coop_soc_milc.give_suit(me, sid) end)
			end
			L.flag_give("MIL_SOC_RG6_DONE")
			return L.wait(6)
		end,
		function(c)
			qa.assert("the weapon was taken", L.count_item(nil, "wpn_rg-6") == 0, tostring(L.count_item(nil, "wpn_rg-6")))
			qa.assert("one scientific suit of Duty arrived", L.count_item(nil, "dolg_scientific_outfit") == 1, tostring(L.count_item(nil, "dolg_scientific_outfit")))
			return L.screenshot("socmilc_cordon")
		end,
	}
end

-------------------------------------------------------------------------------------------------------
-- DEST mil
-------------------------------------------------------------------------------------------------------
local function story_pos(story)
	local id = safe(function() return get_story_object_id(story) end)
	if id == nil then return nil end
	local se = safe(function() return alife():object(id) end)
	if se == nil then return nil end
	return se, id
end

local function mil_steps()
	return {
		function(c) return L.wait(10) end,
		function(c)
			qa.assert("on the Army Warehouses", L.level_name() == "coop_l07_military", tostring(L.level_name()))
			-- the Chef and the Bulldog 6 are created once when the party is on the level (SoC: always there)
			return L.wait_for(function() return story_pos("mil_soc_cook") ~= nil and story_pos("mil_soc_rg6") ~= nil end, 40)
		end,
		function(c, ok)
			qa.assert("the Chef and the Bulldog 6 exist", ok == true)
			local se = story_pos("mil_soc_cook")
			if se then
				ev(string.format("COOK alive=%s pos=%.1f %.1f %.1f", tostring(se:alive()), se.position.x, se.position.y, se.position.z))
				qa.assert("the Chef sits at the SoC table", math.abs(se.position.x + 76.6) < 3 and math.abs(se.position.z - 27.9) < 3)
			end
			local rg = story_pos("mil_soc_rg6")
			if rg then qa.assert("the Bulldog 6 lies in the village basement", math.abs(rg.position.y + 27.47) < 1 and math.abs(rg.position.x + 274.55) < 1) end
			L.flag_give(FLAGS.LK)
			L.flag_give(FLAGS.DONE)
			L.flag_give("MIL_SOC_COURIER_START")
			return L.wait_for(function() return story_pos("mil_soc_pavlik") ~= nil end, 30)
		end,
		function(c, ok)
			qa.assert("Pavlik is created after the job flag", ok == true)
			local se = story_pos("mil_soc_pavlik")
			if se then
				ev(string.format("PAVLIK alive=%s pos=%.1f %.1f %.1f", tostring(se:alive()), se.position.x, se.position.y, se.position.z))
				qa.assert("Pavlik waits at the SoC wait point", math.abs(se.position.x + 178.6) < 3 and math.abs(se.position.z - 352.7) < 3)
			end
			expect_task(L.local_player(), "mil_soc_courier_1_task")
			-- a player in the 45 m farmstead zone, farther than 12 m from Pavlik
			return L.teleport(nil, { -179.9, -16.0, 330.0 })
		end,
		function(c) return L.wait_for(function() return L.flag_has("MIL_SOC_COURIER_KHUTOR") end, 20) end,
		function(c, ok)
			qa.assert("the player at the farmstead: MIL_SOC_COURIER_KHUTOR (no failure)", ok == true and not L.flag_has("MIL_SOC_COURIER_FAILED"))
			-- Pavlik walks to the meeting point and calls (flag after 45 s at the latest + 8.8 s of voice)
			return L.wait_for(function() return L.flag_has("MIL_SOC_COURIER_CALL") end, 90)
		end,
		function(c, ok)
			qa.assert("Pavlik called his agent (MIL_SOC_COURIER_CALL)", ok == true)
			qa.assert("the call cue flag is set (every client plays it in its voice language)", L.flag_has("MIL_SOC_CUE_CALL"))
			local se = story_pos("mil_soc_pavlik")
			if se then ev(string.format("PAVLIK at the call pos=%.1f %.1f %.1f", se.position.x, se.position.y, se.position.z)) end
			return L.wait_for(function() return story_pos("mil_soc_ara") ~= nil and story_pos("mil_soc_ara_guard_3") ~= nil end, 30)
		end,
		function(c, ok)
			qa.assert("Ara and three bodyguards were created", ok == true)
			expect_task(L.local_player(), "mil_soc_courier_3_task")
			expect_task(L.local_player(), "mil_soc_courier_4_task")
			return L.wait_for(function() return L.flag_has("MIL_SOC_ARA_ARRIVE") end, 120)
		end,
		function(c, ok)
			local se = story_pos("mil_soc_ara")
			if se then ev(string.format("ARA alive=%s pos=%.1f %.1f %.1f", tostring(se:alive()), se.position.x, se.position.y, se.position.z)) end
			qa.assert("Ara reached the meeting point (flag by distance or timeout)", ok == true)
			qa.assert("the meeting cue flag (or the ambush) is set", L.flag_has("MIL_SOC_CUE_MEET") or L.flag_has("MIL_SOC_CUE_AMBUSH"))
			return L.screenshot("socmilc_meeting")
		end,
		function(c) return L.wait_for(function() return L.flag_has("MIL_SOC_ARA_END") end, 30) end,
		function(c, ok)
			qa.assert("the talk of Pavlik and Ara ended (MIL_SOC_ARA_END)", ok == true)
			-- the two kills (the dialog of Lukash is covered by the mock test)
			local _, pid = story_pos("mil_soc_pavlik")
			if pid then L.kill(pid, L.local_player()) end
			return L.wait(6)
		end,
		function(c)
			qa.assert("Pavlik dead: MIL_SOC_COURIER_DEAD without a failure", L.flag_has("MIL_SOC_COURIER_DEAD") and not L.flag_has("MIL_SOC_COURIER_FAILED"))
			local _, aid = story_pos("mil_soc_ara")
			if aid then L.kill(aid, L.local_player()) end
			return L.wait(6)
		end,
		function(c)
			qa.assert("Ara dead: MIL_SOC_ARA_DEAD", L.flag_has("MIL_SOC_ARA_DEAD"))
			expect_task(L.local_player(), "mil_soc_courier_5_task")
			qa.assert("Lukash state: pay (cpay)", coop_soc_milc.lukash_state() == "cpay", tostring(coop_soc_milc.lukash_state()))
			return L.screenshot("socmilc_done")
		end,
	}
end

-------------------------------------------------------------------------------------------------------
-- run
-------------------------------------------------------------------------------------------------------
local function host_run()
	local stage = L.state_get("sc_stage", 0)
	if DEST == "mil" and stage == 0 then
		L.state_set("sc_stage", 1)
		L.god(true)
		L.task("sc_cordon", {
			function() return L.wait(8) end,
			function() return L.travel("mil", { timeout = 240, fallback = true }) end,
			function(cc, ok, why) qa.assert("route to the Army Warehouses through the guide vote", ok == true, tostring(why)) end,
		})
		return
	end
	if DEST == "mil" then
		local arrived, level, secs = L.travel_arrived()
		qa.assert("arrived on the Army Warehouses", arrived and level == "coop_l07_military", string.format("%s after %s s", tostring(level), tostring(secs)))
		L.god(true)
		L.task("sc_mil", mil_steps())
		return
	end
	L.god(true)
	L.task("sc_cordon", cordon_steps())
end

local function client_run()
	-- the joined client asserts its own tasks (the server tick gave them to it)
	local ids = DEST == "mil" and { "mil_soc_courier_1_task" } or { "mil_soc_courier_1_task", "mil_soc_rg6_1_task" }
	local steps = {}
	for _, id in ipairs(ids) do
		steps[#steps + 1] = function() return L.wait_for(function() return task_info(L.local_player(), id) ~= nil end, 120) end
		steps[#steps + 1] = function(cc, got)
			qa.assert("SCC the joined client got " .. id, got == true)
			if got then
				local ti = task_info(L.local_player(), id)
				qa.assert("SCC " .. id .. " title is the SoC title", ti.title == tr(T(id) .. "_name"), tostring(ti.title))
			end
		end
	end
	L.task("sc_client", steps)
end

qa.once("sc_run", function(t, lo)
	if _G.__sc_started then return end
	_G.__sc_started = true
	if L.is_dedicated() then return end
	if L.on_server() then host_run() else client_run() end
end)
