--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): "Operation Monolith" on CNPP-1 (patch soc_aes_military). NOT RUN yet (offline work); the mock test
-- (tests\mock_test.py, 70 checks) proves the logic, this hook drives the same steps in the real game.
-- ONE listen-host run, one joined client, starting on Cordon, the party travels by the guide vote (qa_lib.travel, about 70 s).
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner aesmil -DbFile <out>\zzz.db -Hooks <this file> -Cfg no_respawn=1 -SoakSeconds 300 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix AESM
-- The HOST drives the story (players teleported into the SoC zones: the soldier spot, the gate, the Monolith fortifications, the sarcophagus), every machine
-- (host AND client) asserts that ITS OWN player got the task with the SoC title and the right description for each step, that the radio played, and the host
-- asserts the server side (flags, map spots, the army squads that carry the markers). Lines: qa_events.log "AESM ..." ; asserts "AESM ...".
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local TASK = "aes_military_task"
local CNPP = "coop_l11_stancia_1"

local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("AESM " .. s) end
local function norm(s) return (string.gsub(tostring(s or ""), "%s+", " ")) end
local function tr(id) return safe(function() return game.translate_string(id) end) end

local P = {
	body = { 915.0, -0.1, -217.0 },     -- SoC soldier with the plan (aes_stalker_0000)
	gate = { 859.3, -0.5, -42.9 },      -- SoC aes_space_restrictor_gate
	mono1 = { 700.0, 0.5, -60.0 },      -- past the first fortification (x <= 726)
	mono2 = { 600.0, 0.5, -100.0 },     -- past the second fortification (x <= 631)
	sarc = { 387.6, 0.5, -0.9 },        -- SoC aes_found_sarcofag
}

local function task_info(lo)
	local t = lo and safe(function() return lo:get_task(TASK, true) end)
	if t == nil then return nil end
	return { state = safe(function() return t:get_state() end),
		title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function has_task() return task_info(L.local_player()) ~= nil end

local function assert_descr(label, id)
	local ti = task_info(L.local_player())
	qa.assert("AESM " .. label .. ": task is given to this player", ti ~= nil)
	if ti == nil then return end
	ev("TASK state=" .. tostring(ti.state) .. " title=[" .. tostring(ti.title) .. "]")
	qa.assert("AESM " .. label .. ": title is Operation Monolith (SoC)", norm(ti.title) == norm(tr("st_aes_military_name")) and tr("st_aes_military_name") ~= "st_aes_military_name", tostring(ti.title))
	qa.assert("AESM " .. label .. ": description is " .. id, norm(ti.descr) == norm(tr(id)) and tr(id) ~= id, tostring(ti.descr))
end

local function descr_is(id) return function()
	local ti = task_info(L.local_player())
	return ti ~= nil and norm(ti.descr) == norm(tr(id))
end end

-- teleport every player (one after the other) into a point
local function into(pt)
	local steps = { function() return L.wait(2) end }
	for i = 1, 4 do
		steps[#steps + 1] = function()
			local pl = L.players()[i]
			if pl == nil then return end
			return L.teleport(pl.id, { pt[1] + 0.3 * (i - 1), pt[2], pt[3] })
		end
	end
	steps[#steps + 1] = function() return L.wait(5) end
	return steps
end

local function concat(...)
	local out = {}
	for _, t in ipairs({ ... }) do for _, f in ipairs(t) do out[#out + 1] = f end end
	return out
end

local function spots()
	return safe(function() return coop_soc_aes_military.spot_ids() end) or {}
end

local function host_steps()
	return concat({
		function() return L.wait(20) end,
		function()
			ev("status after the arrival: " .. tostring(safe(coop_soc_aes_military.status)))
			qa.assert("AESM arrival: no task before the plan", not has_task())
			qa.assert("AESM arrival: the plan is not found yet", L.flag_has("SOC_AESM_PLAN") == false or L.flag_has("SOC_AESM_PLAN") == nil)
			qa.assert("AESM arrival: the radio played the first SoC line", (safe(function() return coop_soc_aes_military.played_n end) or 0) >= 1,
				tostring(safe(function() return coop_soc_aes_military.played end)))
		end,
	}, into(P.body), {
		function() return L.wait_for(has_task, 25) end,
		function(c, got)
			qa.assert("AESM plan: the task arrived at the soldier spot", got == true)
			assert_descr("plan", "st_aes_military_1_descr")
			for _, p in ipairs(L.players()) do
				qa.assert("AESM plan: the tick gave the task to player " .. tostring(p.name), safe(function() return coop_soc_aes_military.given_to(p.id) end) == true)
			end
			local sp = spots()
			local keys = {}
			for k, v in pairs(sp) do keys[#keys + 1] = k end
			table.sort(keys)
			ev("markers: " .. table.concat(keys, ","))
			qa.assert("AESM plan: gate marker", sp.gate ~= nil)
			qa.assert("AESM plan: Monolith 1 marker", sp.mono1 ~= nil)
			qa.assert("AESM plan: sarcophagus marker", sp.sarc ~= nil)
			-- the squads of the smart terrains 5 and 9 are online near the soldier spot: Yastreb, Pustelga, Sokol, Grif
			local n = 0
			for _, k in ipairs({ "yastreb", "pustelga", "sokol", "grif" }) do if sp[k] ~= nil then n = n + 1 end end
			qa.assert("AESM plan: at least two of the nearby army groups carry a marker", n >= 2, tostring(n))
			ev("host client news and radio: played_n=" .. tostring(safe(function() return coop_soc_aes_military.played_n end)))
		end,
	}, into(P.gate), {
		function() return L.wait_for(descr_is("st_aes_military_2_descr"), 20) end,
		function(c, got)
			qa.assert("AESM gate: the description follows to 'Destroy the Monolith 1 fortifications'", got == true)
			qa.assert("AESM gate: the gate marker is gone", spots().gate == nil)
		end,
	}, into(P.mono1), {
		function() return L.wait_for(descr_is("st_aes_military_3_descr"), 20) end,
		function(c, got)
			qa.assert("AESM Monolith 1: description 'Destroy the Monolith 2 fortifications'", got == true)
			qa.assert("AESM Monolith 1: the marker is gone", spots().mono1 == nil)
		end,
	}, into(P.mono2), {
		function() return L.wait_for(descr_is("st_aes_military_4_descr"), 20) end,
		function(c, got)
			qa.assert("AESM Monolith 2: description 'Break through to the sarcophagus'", got == true)
			qa.assert("AESM Monolith 2: the marker is gone", spots().mono2 == nil)
			ev("radio so far: played_n=" .. tostring(safe(function() return coop_soc_aes_military.played_n end)) .. " last=" .. tostring(safe(function() return coop_soc_aes_military.played end)))
			qa.assert("AESM road: the radio played more than the first line", (safe(function() return coop_soc_aes_military.played_n end) or 0) >= 2)
		end,
	}, into(P.sarc), {
		function() return L.wait_for(function()
			local ti = task_info(L.local_player())
			local done = rawget(_G, "task") and task.completed
			return ti ~= nil and done ~= nil and ti.state == done
		end, 25) end,
		function(c, got)
			qa.assert("AESM sarcophagus: the task is completed (SoC aes_found_sarcofag)", got == true, tostring((task_info(L.local_player()) or {}).state))
			qa.assert("AESM sarcophagus: all markers are gone", next(spots()) == nil)
			ev("final status: " .. tostring(safe(coop_soc_aes_military.status)))
			return L.screenshot("aesm_done")
		end,
	})
end

local function host_run()
	local stage = L.state_get("aesm_stage", 0)
	if stage == 0 then
		L.state_set("aesm_stage", 1)
		L.god(true)
		L.task("aesm_cordon", {
			function() return L.wait(8) end,
			function()
				qa.assert("AESM cordon: the level is Cordon", L.level_name() == "coop_l01_escape", tostring(L.level_name()))
				qa.assert("AESM cordon baseline: no task " .. TASK, not has_task())
			end,
			function() return L.travel("aes_1", { timeout = 240, fallback = true }) end,
			function(cc, ok, why) qa.assert("AESM route to CNPP-1 through the guide vote", ok == true, tostring(why)) end,
		})
		return
	end
	local arrived, level, secs = L.travel_arrived()
	qa.assert("AESM arrived on CNPP-1", arrived and level == CNPP, string.format("%s after %s s", tostring(level), tostring(secs)))
	L.god(true)
	L.task("aesm_run", host_steps())
end

local function client_run()
	local stage = L.state_get("aesm_cstage", 0)
	if stage == 0 then
		L.state_set("aesm_cstage", 1)
		return
	end
	L.task("aesm_client", {
		function() return L.wait_for(has_task, 200) end,
		function(cc, got)
			qa.assert("AESMC the joined client got the task", got == true)
			if got then assert_descr("client", "st_aes_military_1_descr") end
			qa.assert("AESMC the client heard a SoC radio line", (safe(function() return coop_soc_aes_military.played_n end) or 0) >= 1,
				tostring(safe(function() return coop_soc_aes_military.played end)))
		end,
		function() return L.wait_for(descr_is("st_aes_military_4_descr"), 120) end,
		function(cc, got) qa.assert("AESMC the client's description followed the party to the last step", got == true) end,
	})
end

qa.once("aesm_run", function(t, lo)
	if _G.__aesm_started then return end
	_G.__aesm_started = true
	if L.is_dedicated() then return end
	if L.on_server() then host_run() else client_run() end
end)
