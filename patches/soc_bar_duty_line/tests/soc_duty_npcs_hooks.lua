--@qa_lib
-- Bar Duty / Freedom line, NPC part (test only, never shipped). Listen host, start map coop_l01_escape, -Cfg dest=bar then -Cfg dest=ros (two runs, one
-- run_coop.ps1 call each; run_coop takes one -Cfg per call):
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 0 -Owner socdutynpc -ExtraDir <stage>\gamedata -Hooks <this file> -Cfg dest=bar -Cfg no_respawn=1 -SoakSeconds 200 -ResultDir <dir>
-- Travels through the guide + party vote (qa_lib.travel). On the Bar it asserts that the gate commander and Captain Ivantsov were created by the
-- server, are ONLINE with an active logic scheme, and stand within 6 m of the SoC positions; on the Wild Territory (dest=ros, after the veterans
-- job flag was given) that Lucky and the two veterans exist, are hostile (their relation to the player is enemy) and Tyran is NOT there yet;
-- then the Tyran job flag is given and Tyran + four Mercs appear.
-- Lines in qa_events.log:  SOCDUTY ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCDUTY " .. s) end

local POS = {
	bar_dolg_guard_commander = { x = 191.87, y = 0.0, z = 104.53 },
	bar_dolg_captain_ivancov = { x = 192.91, y = 0.0, z = 117.22 },
	bar_crazy_veterans_leader = { x = -250.7, y = 1.2, z = 14.7 },
}

local function online_by_story(story)
	local id = safe(function() return get_story_object_id(story) end)
	if id == nil then return nil, "no story id" end
	local o = safe(function() return level.object_by_id(id) end)
	return o, id
end

local function expect_npc(story, what)
	local o, id = online_by_story(story)
	qa.assert(what .. " created (story id " .. story .. ")", id ~= nil and id ~= "no story id", tostring(id))
	qa.assert(what .. " is online", o ~= nil)
	if o ~= nil then
		local p = o:position()
		local sp = POS[story]
		if sp then
			local d = L.dist3({ x = p.x, y = p.y, z = p.z }, sp)
			ev(string.format("%s at %.1f %.1f %.1f distance to the SoC spot %.1f", what, p.x, p.y, p.z, d))
			qa.assert(what .. " within 6 m of the SoC position", d < 6.0, string.format("%.1f", d))
		end
		local st = db.storage[id]
		qa.assert(what .. " has an active logic scheme", st ~= nil and st.active_scheme ~= nil, tostring(st and st.active_scheme))
		qa.assert(what .. " is alive", safe(function() return o:alive() end) == true)
	end
	return o
end

qa.once("socduty_npcs", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	if _G.__sd_started then return end
	_G.__sd_started = true
	local dest = qa.cfg.dest or "bar"
	local code, lvl = L.guide_code(dest)
	local stage = L.state_get("sd_stage", 0)
	if stage == 0 then
		L.state_set("sd_stage", 1)
		L.god(true)
		if dest == "ros" then
			L.flag_give("BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO")
			L.flag_give("BAR_KILL_VETERAN_START")
		end
		L.task("socduty_travel", {
			function() return L.wait(6) end,
			function() return L.travel(dest, { timeout = 200, fallback = true }) end,
			function(c, ok, why) qa.assert("SD route to " .. tostring(lvl) .. " via the guide vote", ok == true, tostring(why)) end,
		})
	else
		local arrived, level, secs = L.travel_arrived()
		qa.assert("SD arrived on " .. tostring(lvl), arrived and level == lvl, tostring(level))
		L.god(true)
		local steps = {
			function() return L.wait(25) end,
			function()
				if dest == "bar" then
					expect_npc("bar_dolg_guard_commander", "gate commander")
					expect_npc("bar_dolg_captain_ivancov", "Captain Ivantsov")
				else
					local lucky = expect_npc("bar_crazy_veterans_leader", "Lucky")
					for _, k in ipairs({ "soc_duty_vet1", "soc_duty_vet2" }) do expect_npc(k, k) end
					if lucky ~= nil then
						local rel = safe(function() return lucky:relation(L.local_player()) end)
						ev("Lucky relation to the player: " .. tostring(rel))
						qa.assert("Lucky is an enemy of the player (relation 2)", rel == 2, tostring(rel))
					end
					qa.assert("Tyran is not there before his job", online_by_story("bar_svoboda_ambush_tiran") == nil)
					L.flag_give("BAR_KILL_SVOBODA_AMBUSH_START")
				end
				return L.wait(15)
			end,
			function()
				if dest == "ros" then
					for _, k in ipairs({ "bar_svoboda_ambush_tiran", "soc_duty_merc1", "soc_duty_merc2", "soc_duty_amb1", "soc_duty_amb2" }) do
						local id = safe(function() return get_story_object_id(k) end)
						qa.assert("Tyran job open: " .. k .. " created", id ~= nil, tostring(id))
					end
				end
				return L.screenshot("socduty_npcs_" .. dest)
			end,
		}
		L.task("socduty_npcs", steps)
	end
end)
