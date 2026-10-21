--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped).  bar_arrival_anomalies: after arriving on the Bar through the level transition, exactly ONE anomaly zone of the
-- stock Bar is gone: FOSTER's gravitational mine level_prefix_zone_mine_gravitational_strong (12.1 m in front of the Garbage arrival point,
-- 354.7, 9.3, -178.0).  The other nine zones that an earlier version of the patch had removed are back (FOSTER: "return all but one").
-- Listen mode, start map coop_l01_escape, one client, -Cfg no_respawn=1 (and -Cfg dest=bar, the default).  Run it ONE game at a time.
--   run_coop.ps1 -Map coop_l01_escape -Owner baranom -Mode listen -Clients 1 -Cfg no_respawn=1 -Hooks <this file> -SoakSeconds 90 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix BA --require 6
-- Travels from Cordon by the guide flag + party vote (qa_lib.travel; the Bar's alife only comes online that way).  The zones are looked up in
-- the server's object list by name, so the Garbage entrance of FOSTER's screenshot is covered without walking there.
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local FOSTER = "level_prefix_zone_mine_gravitational_strong"
local RESTORED = {
	"bar_zone_field_radioactive_strong_0003",           -- 7.6 m from the Garbage arrival
	"bar_zone_field_radioactive_strong_0004",           -- 16.3 m (Garbage)
	"level_prefix_zone_mine_gravitational_strong_0000", -- 22.3 m (Garbage)
	"level_prefix_zone_mine_gravitational_strong_0011", -- 6.9 m (Wild Territory)
	"level_prefix_zone_mine_gravitational_strong_0014", -- 14.5 m (Wild Territory)
	"level_prefix_zone_mine_gravitational_weak",        -- 16.3 m (Wild Territory)
	"level_prefix_zone_mine_electric_strong_0010",      -- 25.5 m (Wild Territory)
	"level_prefix_zone_mine_electric_strong_0011",      -- 29.3 m (Wild Territory)
	"bar_zone_field_radioactive_strong_0016",           -- 19.5 m (Cordon guide)
}

local function sf(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end

-- names of every anomaly zone object (section zone_*) of the level lid, as a set name -> true
local function zone_names(lid)
	local out, n = {}, 0
	for id = 1, 65534 do
		local o = sf(function() return alife():object(id) end)
		if o ~= nil then
			local sec = sf(function() return o:section_name() end) or ""
			if string.sub(sec, 1, 5) == "zone_" then
				local ol = sf(function() return game_graph():vertex(o.m_game_vertex_id):level_id() end)
				if ol == lid then out[tostring(o:name())] = true n = n + 1 end
			end
		end
	end
	return out, n
end

local function my_level_id()
	local se = sf(function() return alife():actor() end)
	if se == nil then
		local p = L.players()[1]
		if p ~= nil then se = sf(function() return alife():object(p.id) end) end
	end
	if se == nil then return nil end
	return sf(function() return game_graph():vertex(se.m_game_vertex_id):level_id() end)
end

qa.once("bar_no_anomaly", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	if _G.__ba_started then return end   -- appended to three scripts that can load at different times: start once
	_G.__ba_started = true
	local dest = qa.cfg.dest or "bar"
	local code, lvl = L.guide_code(dest)
	local stage = L.state_get("ba_stage", 0)
	if stage == 0 then
		L.state_set("ba_stage", 1)
		L.god(true)
		L.task("bar_no_anomaly_travel", {
			function() return L.wait(6) end,
			-- a successful level change restarts the Lua VM: this action only ends on failure
			function() return L.travel(dest, { timeout = 200, fallback = true }) end,
			function(c, ok, why) qa.assert("BA route to " .. tostring(lvl) .. " via the guide vote", ok == true, tostring(why)) end,
		})
		return
	end
	local arrived, level, secs = L.travel_arrived()
	qa.assert("BA arrived on " .. tostring(lvl) .. " through the level transition", arrived and level == lvl, string.format("%s after %s s", tostring(level), tostring(secs)))
	L.god(true)
	L.task("bar_no_anomaly_check", {
		function() return L.wait(15) end,
		function()
			local lid = my_level_id()
			qa.assert("BA level id of the player known", lid ~= nil, tostring(lid))
			local names, n = zone_names(lid)
			qa.assert("BA the Bar has its anomaly zones (50 or more)", n >= 50, tostring(n))
			qa.assert("BA FOSTER's zone " .. FOSTER .. " is absent", names[FOSTER] == nil, tostring(names[FOSTER]))
			local missing = {}
			for _, nm in ipairs(RESTORED) do
				if not names[nm] then missing[#missing + 1] = nm end
			end
			qa.assert("BA the other 9 zones exist again", #missing == 0, table.concat(missing, ", "))
		end,
	})
end)
