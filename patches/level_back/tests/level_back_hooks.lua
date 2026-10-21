--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Game hook of patch level_back: the way back from the Radar and from Pripyat.
--
--   DEST = "rad" (default, the line below): Cordon -> Radar (guide vote), checks, back to the Army Warehouses through rad_mil_level_changer, forward to
--                    the Radar again through the old mil_rad_level_changer.
--   DEST = "pri"   : Cordon -> Pripyat, checks, back to the Radar through pri_rad_level_changer, forward to Pripyat again through the old
--                    rad_level_changer_2.
-- run_coop -File takes ONE -Cfg only, so the destination is the DEST line (make a copy with "pri" for the Pripyat run, see NOTES.md).
-- Listen mode (the host is a player, alife() exists), start map coop_l01_escape, one client:
--   powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner lbrad -Mode listen -Clients 1 `
--     -DbFile <out>\zzz.db -Hooks <repo>\patches\level_back\tests\level_back_hooks.lua -Cfg no_respawn=1 -SoakSeconds 420 `
--     -CompareTimeout 10 -ResultDir <dir>
--   python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix LB --require 24
--
-- Stages (kept in qa_lib state, every level change restarts the Lua VM):
--   0 Cordon: mark the story (shared flags), give the guide flag, vote yes, travel.
--   1 target level: (a) the back changer exists, is enabled, nobody sees a "cannot go back" text; then every player is teleported into the back changer.
--   2 level behind: arrived, alive, flags and the played-scene set unchanged; the forward changer takes the party to the target level again.
--   3 target level again: same checks. Done.
-- The scene set is the list of SCN_*_PLAYED flags: a return trip must not add one (nothing replays) and must not remove one.
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local DEST = "rad"   -- "rad" or "pri"

local CASES = {
	rad = { lvl = "coop_l09_radar", back = "rad_mil_level_changer", back_lvl = "coop_l07_military", fwd = "mil_rad_level_changer", tag = "Radar" },
	pri = { lvl = "coop_l10_pripyat", back = "pri_rad_level_changer", back_lvl = "coop_l09_radar", fwd = "rad_level_changer_2", tag = "Pripyat" },
}
local MARK = "LB_TEST_MARK"
local X10_FLAGS = { "X10_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO", "X10_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO" }

local function played_set()
	local t = {}
	local tbl = story_flags.story_flags
	if type(tbl) == "table" then
		for k, v in pairs(tbl) do
			if v == true and string.sub(k, 1, 4) == "SCN_" and string.sub(k, -7) == "_PLAYED" then t[#t + 1] = k end
		end
	end
	table.sort(t)
	return table.concat(t, ",")
end

local function split(s)
	local t = {}
	for w in string.gmatch(s or "", "[^,]+") do t[w] = true end
	return t
end

local function same_scenes(before, after)
	local b, a = split(before), split(after)
	for k in pairs(b) do if not a[k] then return false, "lost " .. k end end
	for k in pairs(a) do if not b[k] then return false, "new " .. k end end
	return true, ""
end

local function changer_pos(name)
	local ok, p = pcall(function() return alife():object(name).position end)
	if ok and p ~= nil then return p end
	return nil
end

-- teleport every alive player (one after the other) into the box of the named changer
local function into_changer_steps(name, label)
	local steps = {
		function() return L.wait(3) end,
	}
	for i = 1, 4 do
		steps[#steps + 1] = function()
			local ps = L.players()
			local pl = ps[i]
			if pl == nil then return end
			local pos = changer_pos(name)
			if pos == nil then qa.assert("LB " .. label .. ": server object " .. name .. " found", false, "no server object") return end
			return L.teleport(pl.id, { pos.x, pos.y + 0.3, pos.z })
		end
	end
	steps[#steps + 1] = function() return L.wait(100) end   -- the level change restarts the VM; reaching the next line means it did not happen
	steps[#steps + 1] = function()
		qa.assert("LB " .. label .. ": the level changed after the teleport into " .. name, false, "still on " .. tostring(L.level_name()) .. " after 100 s")
	end
	return steps
end

qa.once("level_back", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	local dest = DEST
	local c = CASES[dest]
	if c == nil then qa.assert("LB known case", false, tostring(dest)) return end
	local stage = tonumber(L.state_get("lb_stage", 0)) or 0
	local lvl = L.level_name()

	if stage == 0 then
		-- Cordon: mark the story state, then travel
		if lvl ~= "coop_l01_escape" then
			qa.assert("LB start on Cordon", false, tostring(lvl))
			return
		end
		L.god(true)
		L.state_set("lb_stage", 1)
		L.state_set("lb_players", #L.players())
		for _, f in ipairs(X10_FLAGS) do L.flag_give(f) end     -- the Brain Scorcher counts as switched off (story state a return must keep)
		L.flag_give(MARK)
		L.state_set("lb_scenes0", played_set())
		L.task("level_back_travel", {
			function() return L.wait(6) end,
			function() return L.travel(dest, { timeout = 240, fallback = true }) end,
			function(cc, ok, why) qa.assert("LB route to " .. c.tag .. " via the guide vote", ok == true, tostring(why)) end,
		})
		return
	end

	L.god(true)

	if stage == 1 then
		local arrived, level, secs = L.travel_arrived()
		qa.assert("LB arrived on " .. c.tag, arrived and level == c.lvl, string.format("%s after %s s", tostring(level), tostring(secs)))
		L.state_set("lb_stage", 2)
		L.task("level_back_stage1", {
			function() return L.wait(15) end,
			function()
				-- (a) the back changer exists and is enabled
				local se = nil
				pcall(function() se = alife():object(c.back) end)
				qa.assert("LB " .. c.tag .. ": back changer " .. c.back .. " exists on the server", se ~= nil, tostring(c.back))
				if se ~= nil then
					local en = nil
					pcall(function() en = se.enabled end)
					qa.assert("LB " .. c.tag .. ": back changer is enabled", en ~= false, "enabled=" .. tostring(en))
					local lc = nil
					pcall(function() lc = level.object_by_id(se.id) end)
					if lc == nil then pcall(function() lc = level.object(c.back) end) end
					-- level.object(name) returns nil for level changers in xrMPE (run 2026-10-21: the changer was in all.spawn, enabled and the party
					-- travelled through it), so a missing client object is only logged here; the real proof is the level change after the teleport below.
					if lc == nil then L.ev("LB " .. c.tag .. ": no client object for " .. c.back .. " by id or name (not a failure, see the teleport step)") end
					if lc ~= nil then
						local ok, e = pcall(function() lc:enable_level_changer(true) end)
						qa.assert("LB " .. c.tag .. ": enable_level_changer(true) works on it", ok, tostring(e))
					end
				end
				local fwd = nil
				pcall(function() fwd = alife():object(c.fwd) end)
				qa.assert("LB " .. c.tag .. ": the old way on (" .. c.fwd .. ") is still there", fwd ~= nil)
				-- no "cannot go back" message
				local txt = ""
				pcall(function() txt = game.translate_string("st_test_text_yes_no") end)
				local low = string.lower(txt)
				qa.assert("LB no 'cannot go back' text (st_test_text_yes_no)", txt ~= "" and not string.find(low, "turning back", 1, true) and not string.find(low, "no way back", 1, true)
					and not string.find(txt, "\206\225\240\224\242\237\238\227\238", 1, true), txt)    -- cp1251 "Obratnogo"
				L.state_set("lb_scenes1", played_set())
				qa.assert("LB story state kept on arrival: marker flag", L.flag_has(MARK))
				for _, f in ipairs(X10_FLAGS) do qa.assert("LB Brain Scorcher flag " .. f .. " still set on " .. c.tag, L.flag_has(f)) end
				return L.now(true)
			end,
			function() return L.seq(into_changer_steps(c.back, c.tag), "into_back") end,
		})
		return
	end

	if stage == 2 then
		L.state_set("lb_stage", 3)
		L.task("level_back_stage2", {
			function() return L.wait_for(function() return #L.players() >= (tonumber(L.state_get("lb_players", 0)) or 0) end, 60) end,
			function()
				qa.assert("LB went back to " .. c.back_lvl, lvl == c.back_lvl, tostring(lvl))
				qa.assert("LB players alive after the way back", #L.players() >= 1, tostring(#L.players()))
				qa.assert("LB all players came along", #L.players() >= (tonumber(L.state_get("lb_players", 0)) or 0), #L.players() .. " of " .. tostring(L.state_get("lb_players")))
				qa.assert("LB marker flag kept after the way back", L.flag_has(MARK))
				for _, f in ipairs(X10_FLAGS) do qa.assert("LB Brain Scorcher stays off after the way back: " .. f, L.flag_has(f)) end
				local same, why = same_scenes(L.state_get("lb_scenes1", ""), played_set())
				qa.assert("LB no scene replayed or lost by the way back (SCN_*_PLAYED set equal)", same, why)
				return L.wait(10)
			end,
			function() return L.seq(into_changer_steps(c.fwd, c.back_lvl), "into_fwd") end,
		})
		return
	end

	if stage == 3 then
		L.state_set("lb_stage", 4)
		L.task("level_back_stage3", {
			function() return L.wait_for(function() return #L.players() >= (tonumber(L.state_get("lb_players", 0)) or 0) end, 60) end,
			function()
				qa.assert("LB forward again to " .. c.tag, lvl == c.lvl, tostring(lvl))
				qa.assert("LB players alive after the round trip", #L.players() >= 1, tostring(#L.players()))
				qa.assert("LB marker flag kept after the round trip", L.flag_has(MARK))
				for _, f in ipairs(X10_FLAGS) do qa.assert("LB Brain Scorcher still off after the round trip: " .. f, L.flag_has(f)) end
				local same, why = same_scenes(L.state_get("lb_scenes1", ""), played_set())
				qa.assert("LB no scene replayed by the round trip", same, why)
				qa.event("LB done")
			end,
		})
		return
	end
	qa.event("LB stage " .. tostring(stage) .. " already finished")
end)
