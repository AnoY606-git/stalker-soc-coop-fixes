--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): the fighting helicopters, the army BTR and the helicopter radio of CNPP-1 (patches soc_aes_war + soc_aes_military).
-- NOT RUN yet (offline work); tests\mock_test.py (68 checks) proves the logic of the scripts, this hook drives it in the real game.
-- ONE listen-host run, one joined client, starting on Cordon, the party travels by the guide vote (qa_lib.travel, about 70 s).
--   python build.py <out>\zzz.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner aeswar -DbFile <out>\zzz.db -Hooks <this file> -Cfg no_respawn=1 -SoakSeconds 420 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix AESW
-- Steps (host): arrival (no go flag, helicopters idle) -> the party on the SoC actor_ready line (go flag, at least one of the 8 helicopters leaves its yard) ->
-- the party in the first SoC helicopter zone (a helicopter gets an enemy) -> one helicopter is shot down by script (flag SOC_AESW_DOWN_1, the radio line
-- aes_choper_down_1 plays on the host and on the client) -> the party 400 m from the BTR spot (the BTR is created, comes online, drives, the client sees it).
-- Asserts that can depend on the AI (a Monolith soldier in view of a helicopter) are logged as AESW events, not asserts.
-- Lines: qa_events.log "AESW ..." ; asserts "AESW ...".
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local CNPP = "coop_l11_stancia_1"

local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("AESW " .. s) end

local P = {
	ready = { 926.0, -0.1, -171.0 },       -- SoC actor_ready line
	zone1 = { 782.0, 0.0, -162.0 },        -- SoC aes_actor_heli (helicopters hunt the player here)
	btr = { 800.0, 0.0, -150.0 },          -- 400 m from the BTR spot (412, 0, -128): it is created when a player is within 450 m
	btr_near = { 445.0, 0.0, -140.0 },     -- the BTR starts at (412, 0, -128): near enough to see it drive
}

local function heli_objects()
	local t = {}
	local h = safe(function() return db.heli end) or {}
	for id, o in pairs(h) do
		local nm = safe(function() return o:name() end)
		if type(nm) == "string" and string.sub(nm, 1, 18) == "aes_1_heli_attack_" then t[#t + 1] = o end
	end
	return t
end

-- number of helicopters that are away from the yard (z > -640 means they left it: the yard is at z -665)
local function flying()
	local n = 0
	for _, o in ipairs(heli_objects()) do
		local p = safe(function() return o:position() end)
		if p ~= nil and p.z > -640 then n = n + 1 end
	end
	return n
end

local function into(pt)
	local steps = { function() return L.wait(2) end }
	for i = 1, 4 do
		steps[#steps + 1] = function()
			local pl = L.players()[i]
			if pl == nil then return end
			return L.teleport(pl.id, { pt[1] + 0.3 * (i - 1), pt[2], pt[3] })
		end
	end
	steps[#steps + 1] = function() return L.wait(3) end
	return steps
end

local function concat(...)
	local out = {}
	for _, t in ipairs({ ... }) do for _, f in ipairs(t) do out[#out + 1] = f end end
	return out
end

local function played_down()
	local p = safe(function() return coop_soc_aes_military.played end)
	return type(p) == "string" and string.find(p, "aes_choper_down_1", 1, true) ~= nil
end

local function find_btr_here()
	-- the entity of the BTR on this machine (client or host): scan the object ids for the section
	for i = 1, 20000 do
		local o = safe(function() return level.object_by_id(i) end)
		if o ~= nil and safe(function() return o:section() end) == "soc_aes_btr" then return o end
	end
	return nil
end

local function host_steps()
	local t0 = { x = 0, y = 0, z = 0 }
	local bid = nil
	return concat({
		function() return L.wait(20) end,
		function()
			ev("status after the arrival: " .. tostring(safe(coop_soc_aes_war.status)))
			qa.assert("AESW arrival: no go flag yet", L.flag_has("SOC_AESW_GO") ~= true)
			qa.assert("AESW arrival: no BTR yet (the spot is 500+ m away)", safe(coop_soc_aes_war.btr_object_id) == nil)
			ev("helicopters online on arrival: " .. tostring(#heli_objects()) .. " flying=" .. tostring(flying()))
		end,
	}, into(P.ready), {
		function() return L.wait_for(function() return L.flag_has("SOC_AESW_GO") == true end, 15) end,
		function(c, got) qa.assert("AESW the party on the SoC actor_ready line gives the go flag", got == true) end,
		function() return L.wait_for(function() return flying() >= 1 end, 90) end,
		function(c, got)
			ev("flying after the go: " .. tostring(flying()) .. " of " .. tostring(#heli_objects()) .. " online")
			qa.assert("AESW at least one of the 8 helicopters left the yard", got == true, tostring(flying()))
		end,
	}, into(P.zone1), {
		function() return L.wait_for(function() return (safe(coop_soc_aes_war.armed_count) or 0) >= 1 end, 120) end,
		function(c, got)
			ev("armed helicopters: " .. tostring(safe(coop_soc_aes_war.armed_count)) .. " status " .. tostring(safe(coop_soc_aes_war.status)))
			-- a helicopter only gets an enemy when it is within 350 m of a player and sees a target: log, assert softly
			if got ~= true then ev("WARN no helicopter had an enemy within 120 s (no Monolith soldier / player in view of a helicopter?)") end
			return L.screenshot("aesw_zone1")
		end,
		-- shoot one down by script (the same call bind_heli makes at zero health)
		function()
			local hs = heli_objects()
			qa.assert("AESW a helicopter is online to shoot down", #hs >= 1, tostring(#hs))
			if #hs == 0 then return end
			local o = hs[1]
			ev("shooting down " .. tostring(safe(function() return o:name() end)))
			safe(function() bind_heli.heli_die(o) end)
		end,
		function() return L.wait_for(function() return L.flag_has("SOC_AESW_DOWN_1") == true end, 15) end,
		function(c, got) qa.assert("AESW a helicopter shot down sets SOC_AESW_DOWN_1", got == true) end,
		function() return L.wait_for(played_down, 40) end,
		function(c, got) qa.assert("AESW the host heard aes_choper_down_1 on the radio", got == true, tostring(safe(function() return coop_soc_aes_military.played end))) end,
	}, into(P.btr), {
		function() return L.wait_for(function() return safe(coop_soc_aes_war.btr_object_id) ~= nil end, 30) end,
		function(c, got)
			bid = safe(coop_soc_aes_war.btr_object_id)
			qa.assert("AESW the BTR was created (a player within 450 m of its spot)", got == true and bid ~= nil, tostring(bid))
			qa.assert("AESW BTR_MADE flag set", L.flag_has("SOC_AESW_BTR_MADE") == true)
		end,
	}, into(P.btr_near), {
		function() return L.wait_for(function()
			local st = safe(function() return db.storage[bid] end)
			return st ~= nil and st.object ~= nil
		end, 30) end,
		function(c, got)
			qa.assert("AESW the BTR is online with its binder (db.storage)", got == true)
			local o = safe(function() return db.storage[bid].object end)
			if o ~= nil then
				local p = o:position()
				t0 = { x = p.x, y = p.y, z = p.z }
				ev(string.format("BTR online at %.1f %.1f %.1f section=%s visual=%s", p.x, p.y, p.z, tostring(safe(function() return o:section() end)), tostring(safe(function() return o:get_visual_name() end))))
				qa.assert("AESW the BTR has a car and a gun", safe(function() return o:get_car():HasWeapon() end) == true)
				qa.assert("AESW the logic scheme is ph_car", safe(function() return db.storage[bid].active_scheme end) == "ph_car", tostring(safe(function() return db.storage[bid].active_scheme end)))
			end
		end,
		function() return L.wait(25) end,
		function()
			local o = safe(function() return db.storage[bid].object end)
			if o ~= nil then
				local p = o:position()
				local d = math.sqrt((p.x - t0.x) ^ 2 + (p.z - t0.z) ^ 2)
				ev(string.format("BTR after 25 s at %.1f %.1f %.1f (moved %.1f m) scheme=%s", p.x, p.y, p.z, d, tostring(safe(function() return db.storage[bid].active_scheme end))))
				qa.assert("AESW the BTR drove (moved more than 5 m in 25 s)", d > 5.0, string.format("%.1f", d))
			end
			return L.screenshot("aesw_btr")
		end,
		function() return L.wait(30) end,
		function()
			ev("final status: " .. tostring(safe(coop_soc_aes_war.status)))
		end,
	})
end

local function host_run()
	local stage = L.state_get("aesw_stage", 0)
	if stage == 0 then
		L.state_set("aesw_stage", 1)
		L.god(true)
		L.task("aesw_cordon", {
			function() return L.wait(8) end,
			function() qa.assert("AESW cordon: the level is Cordon", L.level_name() == "coop_l01_escape", tostring(L.level_name())) end,
			function() return L.travel("aes_1", { timeout = 240, fallback = true }) end,
			function(cc, ok, why) qa.assert("AESW route to CNPP-1 through the guide vote", ok == true, tostring(why)) end,
		})
		return
	end
	local arrived, level, secs = L.travel_arrived()
	qa.assert("AESW arrived on CNPP-1", arrived and level == CNPP, string.format("%s after %s s", tostring(level), tostring(secs)))
	L.god(true)
	L.task("aesw_run", host_steps())
end

local function client_run()
	local stage = L.state_get("aesw_cstage", 0)
	if stage == 0 then
		L.state_set("aesw_cstage", 1)
		return
	end
	L.task("aesw_client", {
		function() return L.wait_for(played_down, 400) end,
		function(cc, got)
			qa.assert("AESWC the client heard aes_choper_down_1 on the radio", got == true, tostring(safe(function() return coop_soc_aes_military.played end)))
		end,
		function() return L.wait_for(function() return find_btr_here() ~= nil end, 120) end,
		function(cc, got)
			qa.assert("AESWC the client sees the BTR object (synced)", got == true)
			local o = find_btr_here()
			if o ~= nil then
				local p = o:position()
				ev(string.format("client sees the BTR at %.1f %.1f %.1f", p.x, p.y, p.z))
			end
		end,
	})
end

qa.once("aesw_run", function(t, lo)
	if _G.__aesw_started then return end
	_G.__aesw_started = true
	if L.is_dedicated() then return end
	if L.on_server() then host_run() else client_run() end
end)
