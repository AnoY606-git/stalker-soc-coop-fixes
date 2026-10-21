--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): Radar / X-10 / Pripyat / Sarcophagus / Control Monolith quests in the original SoC order (patch soc_aes_quests).
-- ONE listen-host run per destination, one joined client, starting on Cordon, the party travels by the guide vote (qa_lib.travel, about 70 s).
-- run_coop takes ONE -Cfg only, so the destination is the DEST line below (make a copy of this file with another value per run, see NOTES.md).
--   DEST = "pri": Pripyat   - the decoder lies in the hotel room, the Doctor's stash task, the stalkers (meet / follow / CNPP)
--   DEST = "sar": Sarcophagus - Wish Granter steps, the fallback decoder (the party did not take the stash one), secret lab steps
--   DEST = "con": Control Monolith - infiltrate, solve the secret (one task for six generators), talk to C-Consciousness, hidden steps never given
--   DEST = "x10": X-10 - Brain Scorcher step, then "Reach the power plant"
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner aespri -DbFile <out>\zzz.db -Hooks <this file> -Cfg no_respawn=1 -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix AES
-- The HOST drives the story (the flags that restrictors and dialogs would give, players teleported into the SoC zones), every machine (host AND
-- client) asserts that ITS OWN player got each task with the SoC title and the right description. Lines: qa_events.log "AES ..." ; asserts "AES ...".
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local DEST = "pri"   -- "pri" | "sar" | "con" | "x10"

local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("AES " .. s) end
local function norm(s) return (string.gsub(tostring(s or ""), "%s+", " ")) end
local function tr(id) return safe(function() return game.translate_string(id) end) end

-- key -> { task id, title string id, description string id (nil = do not check) }
local T = {
	X10A = { "x10_start_turn_off_the_radar_quest_task", "st_x10_start_turn_off_the_radar_quest_task_name", "st_x10_start_turn_off_the_radar_quest_task_descr" },
	X10B = { "x10_start_leave_the_bunker_and_go_to_pripyat_quest_task", "st_x10_start_leave_the_bunker_and_go_to_pripyat_quest_task_name", "st_x10_start_leave_the_bunker_and_go_to_pripyat_quest_task_descr" },
	MEET = { "pri_start_meet_a_group_of_stalkers_quest_task", "st_pri_start_meet_a_group_of_stalkers_quest_task_name", "st_pri_start_meet_a_group_of_stalkers_quest_task_descr" },
	CNPP = { "pri_start_go_to_cnpp_quest_task", "st_pri_start_go_to_cnpp_quest_task_name", "st_pri_start_go_to_cnpp_quest_task_descr" },
	S1 = { "pri_soc_stash_1_task", "st_pri_soc_stash_name", "st_pri_soc_stash_1_descr" },
	S2 = { "pri_soc_stash_2_task", "st_pri_soc_stash_name", "st_pri_soc_stash_2_descr" },
	S3 = { "pri_soc_stash_3_task", "st_pri_soc_stash_name", "st_pri_soc_stash_3_descr" },
	W0 = { "sar_start_get_to_the_monolith_quest_task", "st_sar_start_get_to_the_monolith_quest_task_name", "st_sar_start_get_to_the_monolith_quest_task_descr" },
	W1 = { "sar_soc_sneak_in_task", "st_sar_soc_wish_name", "st_sar_soc_sneak_in_descr" },
	W2 = { "sar_soc_find_wish_task", "st_sar_soc_wish_name", "st_sar_soc_find_wish_descr" },
	L1 = { "sar_soc_lab_1_task", "st_sar_soc_lab_name", "st_sar_soc_lab_1_descr" },
	L2 = { "sar_soc_lab_2_task", "st_sar_soc_lab_name", "st_sar_soc_lab_2_descr" },
	L3 = { "sar_start_open_the_door_to_monolith_management_quest_task", "st_sar_start_open_the_door_to_monolith_management_quest_task_name", "st_sar_start_open_the_door_to_monolith_management_quest_task_descr" },
	L4 = { "sar_soc_lab_4_task", "st_sar_soc_lab_name", "st_sar_soc_lab_4_descr" },
	C0 = { "con_start_sneak_into_the_control_room_quest_task", "st_con_start_sneak_into_the_control_room_quest_task_name", "st_con_start_sneak_into_the_control_room_quest_task_descr" },
	C1 = { "con_start_destroy_the_monolith_installation_1_quest_task", "st_con_start_destroy_the_monolith_installation_quest_task_name", "st_con_start_destroy_the_monolith_installation_quest_task_descr" },
	C2 = { "con_start_talk_to_the_representative_awareness_quest_task", "st_con_start_talk_to_the_representative_awareness_quest_task_name", "st_con_start_talk_to_the_representative_awareness_quest_task_descr" },
}
-- never given (mod-only steps)
local HIDDEN = { "sar_start_kill_the_monolith_preacher_quest_task", "sar_start_search_the_preacher_body_and_retrieve_the_decoder_quest_task",
	"con_start_destroy_the_monolith_installation_2_quest_task", "con_start_destroy_the_monolith_installation_3_quest_task",
	"con_start_destroy_the_monolith_installation_4_quest_task", "con_start_destroy_the_monolith_installation_5_quest_task",
	"con_start_destroy_the_monolith_installation_6_quest_task", "con_start_kill_all_representatives_of_awareness_quest_task" }

local ZONE = {                       -- a point inside each SoC zone (patch script boxes)
	room = { 101.0, 4.3, 127.1 }, sneak = { 34.4, 13.5, -16.0 }, bunker = { 27.0, 17.3, 28.7 }, door = { 49.0, 17.2, 27.3 },
}
local DEC_PRI = { 99.65, 4.9, 123.0 }

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { state = safe(function() return t:get_state() end),
		title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function assert_task(lo, key, label)
	local d = T[key]
	local ti = task_info(lo, d[1])
	qa.assert("AES " .. label .. ": task " .. d[1] .. " is given to this player", ti ~= nil)
	if ti then
		ev("TASK " .. d[1] .. " title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
		qa.assert("AES " .. label .. ": title is " .. d[2], norm(ti.title) == norm(tr(d[2])) and tr(d[2]) ~= d[2], tostring(ti.title))
		if d[3] then qa.assert("AES " .. label .. ": description is " .. d[3], norm(ti.descr) == norm(tr(d[3])) and tr(d[3]) ~= d[3], tostring(ti.descr)) end
	end
	return ti
end

local function has_task(key) return function() return task_info(L.local_player(), T[key][1]) ~= nil end end
local function no_task(label, ids)
	local me = L.local_player()
	for _, id in ipairs(ids) do qa.assert("AES " .. label .. ": task " .. id .. " is not given", task_info(me, id) == nil) end
end
local function given_everywhere(key, label)
	for _, p in ipairs(L.players()) do
		qa.assert("AES " .. label .. ": the tick gave " .. T[key][1] .. " to player " .. tostring(p.name), safe(function() return coop_soc_aes.given_to(T[key][1], p.id) end) == true)
	end
end

local function ids_of(keys) local t = {} for _, k in ipairs(keys) do t[#t + 1] = T[k][1] end return t end

-- teleport every player (one after the other) into a point
local function into(pt, label)
	local steps = { function() return L.wait(2) end }
	for i = 1, 4 do
		steps[#steps + 1] = function()
			local pl = L.players()[i]
			if pl == nil then return end
			return L.teleport(pl.id, { pt[1] + 0.3 * (i - 1), pt[2], pt[3] })
		end
	end
	steps[#steps + 1] = function() return L.wait(6) end
	return steps
end

local function concat(...)
	local out = {}
	for _, t in ipairs({ ... }) do for _, f in ipairs(t) do out[#out + 1] = f end end
	return out
end

local CASES = {}

-- ----------------------------------------------------------------------------------------------- Pripyat
CASES.pri = { travel = "pri", level = "coop_l10_pripyat",
	pre = function()   -- Cordon: the Brain Scorcher counts as switched off
		L.flag_give("X10_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO")
		L.flag_give("X10_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO")
	end,
	steps = function()
		return concat({
			function() return L.wait(25) end,
			function()
				ev("status after the arrival: " .. tostring(safe(coop_soc_aes.status)))
				qa.assert("AES pri: the decoder was spawned in the hotel room (server id known)", safe(function() return coop_soc_aes.stash_id end) ~= nil)
				local id = safe(function() return coop_soc_aes.stash_id end)
				local se = id and safe(function() return alife():object(id) end)
				qa.assert("AES pri: the server object exists", se ~= nil)
				if se ~= nil then
					local p = se.position
					ev(string.format("decoder object %s at %.2f %.2f %.2f", tostring(safe(function() return se:section_name() end)), p.x, p.y, p.z))
					qa.assert("AES pri: it is a dev_decoder", safe(function() return se:section_name() end) == "dev_decoder")
					local d = math.sqrt((p.x - DEC_PRI[1]) ^ 2 + (p.z - DEC_PRI[3]) ^ 2)
					qa.assert("AES pri: it lies within 3 m of the SoC position", d < 3.0, tostring(d))
				end
				assert_task(L.local_player(), "S1", "pri arrival")
				given_everywhere("S1", "pri arrival")
				no_task("pri arrival", ids_of({ "MEET", "CNPP", "S2", "S3", "L1" }))
				L.flag_give("PRI_FOLLOWERS_LEADER_PHRASE1_1_INFO")   -- the meeting zone
				return L.wait_for(has_task("MEET"), 20)
			end,
			function(c, got)
				qa.assert("AES pri: 'Meet the group of stalkers' arrived", got == true)
				assert_task(L.local_player(), "MEET", "pri meeting")
				assert_task(L.local_player(), "CNPP", "pri meeting")
				given_everywhere("MEET", "pri meeting")
			end,
		}, into(ZONE.room, "room"), {
			function() return L.wait_for(has_task("S3"), 25) end,
			function(c, got)
				qa.assert("AES pri: the room zone gave 'Look the secret stash over'", got == true)
				qa.assert("AES pri: flags hotel and room", L.flag_has("PRI_ACTOR_IN_HOTEL") and L.flag_has("PRI_ACTOR_IN_HIDING_PLACE"))
				assert_task(L.local_player(), "S3", "pri room")
				local pl = L.players()[1]
				local ids, why = L.give_item(pl, "dev_decoder", 1)
				qa.assert("AES pri: a decoder was put into a player's inventory", ids ~= nil and #ids == 1, tostring(why))
				return L.wait_for(function() return L.flag_has("PRI_MONOLITH_DECODER_GOT") end, 20)
			end,
			function(c, got)
				qa.assert("AES pri: a holder of the decoder sets PRI_MONOLITH_DECODER_GOT", got == true)
				return L.wait_for(has_task("L1"), 20)
			end,
			function(c, got)
				qa.assert("AES pri: 'Secret lab' (enter the secret bunker) was given", got == true)
				assert_task(L.local_player(), "L1", "pri decoder")
				given_everywhere("L1", "pri decoder")
				ev("final status: " .. tostring(safe(coop_soc_aes.status)))
				return L.screenshot("aes_pri_done")
			end,
		})
	end,
	client = { "S1", "MEET", "CNPP", "S3", "L1" },
}

-- ----------------------------------------------------------------------------------------------- Sarcophagus
CASES.sar = { travel = "sar", level = "coop_l11_sarcofag",
	pre = function() end,
	steps = function()
		return concat({
			function() return L.wait(25) end,
			function()
				ev("status after the arrival: " .. tostring(safe(coop_soc_aes.status)))
				assert_task(L.local_player(), "W0", "sar arrival")
				assert_task(L.local_player(), "W1", "sar arrival")
				given_everywhere("W1", "sar arrival")
				no_task("sar arrival", ids_of({ "W2", "L1", "L2", "L3", "L4" }))
				no_task("sar arrival", HIDDEN)
				qa.assert("AES sar arrival: no stash decoder yet, so the restrictor copy was spawned (its stop flag is set)", L.flag_has("SAR_SMART_TERRAIN_17_SPAWN_SQUAD_STOP_INFO"))
			end,
		}, into(ZONE.sneak, "sneak"), {
			function() return L.wait_for(has_task("W2"), 25) end,
			function(c, got)
				qa.assert("AES sar: inside the sarcophagus: 'Find the Wish Granter' arrived", got == true)
				assert_task(L.local_player(), "W2", "sar sneak")
				local ids, why = L.give_item(L.players()[1], "dev_decoder", 1)
				qa.assert("AES sar: the decoder (found on the level) is in a player's inventory", ids ~= nil and #ids == 1, tostring(why))
				return L.wait_for(has_task("L1"), 25)
			end,
			function(c, got)
				qa.assert("AES sar: decoder: 'Enter the secret bunker' arrived", got == true)
				assert_task(L.local_player(), "L1", "sar decoder")
			end,
		}, into(ZONE.bunker, "bunker"), {
			function() return L.wait_for(has_task("L2"), 25) end,
			function(c, got)
				qa.assert("AES sar: bunker: 'Find the hidden door' arrived", got == true)
				assert_task(L.local_player(), "L2", "sar bunker")
			end,
		}, into(ZONE.door, "door"), {
			function() return L.wait_for(has_task("L3"), 25) end,
			function(c, got)
				qa.assert("AES sar: at the door: 'Open it using the decoder' arrived", got == true)
				assert_task(L.local_player(), "L3", "sar door")
				L.flag_give("LOCKED_START_OPEN_INFO")        -- what the door logic gives when the decoder is used
				return L.wait_for(has_task("L4"), 25)
			end,
			function(c, got)
				qa.assert("AES sar: door opened: 'Find out what is behind the door' arrived", got == true)
				assert_task(L.local_player(), "L4", "sar opened")
				given_everywhere("L4", "sar opened")
				L.flag_give("SAR_MONOLITH_WISH_SPACE_RESTRICTOR_INFO")
				return L.wait(5)
			end,
			function()
				no_task("sar end", HIDDEN)
				ev("final status: " .. tostring(safe(coop_soc_aes.status)))
				return L.screenshot("aes_sar_done")
			end,
		})
	end,
	client = { "W0", "W1", "W2", "L1", "L2", "L3", "L4" },
}

-- ----------------------------------------------------------------------------------------------- Control Monolith
CASES.con = { travel = "con", level = "coop_l11_control_monolith",
	pre = function() end,
	steps = function()
		local gens = {}
		for i = 1, 6 do gens[#gens + 1] = "CON_MONOLITH_GENERATOR_" .. i .. "_INFO" end
		return {
			function() return L.wait(25) end,
			function()
				ev("status after the arrival: " .. tostring(safe(coop_soc_aes.status)))
				assert_task(L.local_player(), "C0", "con arrival")
				given_everywhere("C0", "con arrival")
				no_task("con arrival", ids_of({ "C1", "C2" }))
				L.flag_give("CON_LAB_PRIMARY_SWITCHER_DEACTIVATE_INFO")      -- the control room switch
				return L.wait_for(has_task("C1"), 25)
			end,
			function(c, got)
				qa.assert("AES con: control room open: 'Solve the Monolith's secret' arrived", got == true)
				assert_task(L.local_player(), "C1", "con switch")
				for i = 1, 5 do L.flag_give(gens[i]) end
				return L.wait(6)
			end,
			function()
				no_task("con five generators", ids_of({ "C2" }))
				L.flag_give(gens[6])
				return L.wait_for(has_task("C2"), 25)
			end,
			function(c, got)
				qa.assert("AES con: all six generators down: 'Meet whoever is behind the Monolith' arrived", got == true)
				assert_task(L.local_player(), "C2", "con generators")
				given_everywhere("C2", "con generators")
				no_task("con generators", HIDDEN)
				qa.assert("AES con: the freeplay hook of the true ending is still there", safe(function() return type(coop_scn_freeplay.credits_variant) end) == "function")
				ev("final status: " .. tostring(safe(coop_soc_aes.status)))
				return L.screenshot("aes_con_done")
			end,
		}
	end,
	client = { "C0", "C1", "C2" },
}

-- ----------------------------------------------------------------------------------------------- X-10
CASES.x10 = { travel = "x10", level = "coop_l09_x10",
	pre = function() end,
	steps = function()
		return {
			function() return L.wait(25) end,
			function()
				ev("status after the arrival: " .. tostring(safe(coop_soc_aes.status)))
				qa.assert("AES x10: entering X-10 sets the Radar flag (restrictor)", L.flag_has("RAD_START_GO_TO_RADAR_QUEST_TASK_INFO") or L.flag_give("RAD_START_GO_TO_RADAR_QUEST_TASK_INFO"))
				return L.wait_for(has_task("X10A"), 25)
			end,
			function(c, got)
				qa.assert("AES x10: 'Disable the Brain Scorcher' arrived", got == true)
				assert_task(L.local_player(), "X10A", "x10 arrival")
				given_everywhere("X10A", "x10 arrival")
				no_task("x10 arrival", ids_of({ "X10B", "MEET" }))
				L.flag_give("X10_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO")
				L.flag_give("X10_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO")
				return L.wait_for(has_task("X10B"), 25)
			end,
			function(c, got)
				qa.assert("AES x10: Brain Scorcher off: 'Reach the power plant' arrived", got == true)
				assert_task(L.local_player(), "X10B", "x10 switch")
				given_everywhere("X10B", "x10 switch")
				ev("final status: " .. tostring(safe(coop_soc_aes.status)))
				return L.screenshot("aes_x10_done")
			end,
		}
	end,
	client = { "X10A", "X10B" },
}

local function host_run(c)
	local stage = L.state_get("aes_stage", 0)
	if stage == 0 then
		L.state_set("aes_stage", 1)
		L.god(true)
		L.task("aes_cordon", {
			function() return L.wait(8) end,
			function()
				qa.assert("AES cordon: the level is Cordon", L.level_name() == "coop_l01_escape", tostring(L.level_name()))
				for k, d in pairs(T) do qa.assert("AES cordon baseline: no task " .. d[1], task_info(L.local_player(), d[1]) == nil) end
				c.pre()
				return L.screenshot("aes_cordon")
			end,
			function() return L.travel(c.travel, { timeout = 240, fallback = true }) end,
			function(cc, ok, why) qa.assert("AES route to " .. c.level .. " through the guide vote", ok == true, tostring(why)) end,
		})
		return
	end
	local arrived, level, secs = L.travel_arrived()
	qa.assert("AES arrived on " .. c.level, arrived and level == c.level, string.format("%s after %s s", tostring(level), tostring(secs)))
	L.god(true)
	L.task("aes_" .. DEST, c.steps())
end

local function client_run(c)
	local stage = L.state_get("aes_cstage", 0)
	if stage == 0 then
		L.state_set("aes_cstage", 1)
		return
	end
	local steps = {}
	for _, k in ipairs(c.client) do
		steps[#steps + 1] = function() return L.wait_for(has_task(k), 200) end
		steps[#steps + 1] = function(cc, got)
			qa.assert("AESC the joined client got " .. T[k][1], got == true)
			if got then assert_task(L.local_player(), k, "client") end
		end
	end
	L.task("aes_client_" .. DEST, steps)
end

qa.once("aes_run", function(t, lo)
	if _G.__aes_started then return end
	_G.__aes_started = true
	if L.is_dedicated() then return end
	local c = CASES[DEST]
	if c == nil then qa.assert("AES known case", false, tostring(DEST)) return end
	if L.on_server() then host_run(c) else client_run(c) end
end)
