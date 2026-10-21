--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Game hook of patch freeplay: after the true ending the whole party ends up on the Cordon, alive, with its
-- inventory and money, with every story flag intact, and the world keeps running.
--
--   MODE = "quick" (default, the line below): the end scene is not played; the test sets the final-scene flags (AES_2_THE_END_SPACE_RESTRICTOR_INFO,
--                   SCN_END_PEACE_PLAYED) and calls the end_peace hook the director calls at the end of the movie. The credits scene then
--                   really runs and the test votes to skip it (majority), the freeplay scene really runs.
--   MODE = "full"   : only AES_2_THE_END_SPACE_RESTRICTOR_INFO is given: the real movie (about 110 s) plays, the real credits start, the test votes
--                   to skip them. Needs the ending media (they are in the add-on).
-- run_coop -File takes ONE -Cfg only, so the mode is the MODE line (make a copy with "full" for the long run, see NOTES.md).
--
-- Listen mode (the host is a player, alife() exists), start map coop_l01_escape, one client. The test travels to CNPP-2 through the guide vote:
--   powershell -NoProfile -ExecutionPolicy Bypass -File <games>\tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner fpquick -Mode listen -Clients 1 `
--     -DbFile <out>\zzz.db -Hooks <repo>\patches\freeplay\tests\freeplay_hooks.lua -Cfg no_respawn=1 -SoakSeconds 600 `
--     -CompareTimeout 10 -ResultDir <dir>
--   python <games>\tools\stalker_xrmpe\qa_verdict.py <dir> --prefix FP --require 25
-- Host switch off: add to <game>\_appdata_qa_<tag>_A\coop_settings.ltx the lines "[freeplay]" / "enabled = false" BEFORE the run (the harness makes a
-- fresh folder, so use the "off" copy of this file: OFF = true makes the hook write the file itself on Cordon and reload) and expect the OLD end:
-- the credits end with the disconnect and the run stops; the hook then asserts only that no freeplay flag exists and the exit stays closed.
--
-- Stages (qa_lib state; every level change restarts the Lua VM):
--   0 Cordon: give every player 3 medkits, 2 bread and 12345 money, mark the story (shared flag), record the counts, travel to CNPP-2.
--   1 CNPP-2: the exit exists, the end is triggered, the credits are skipped by vote, wait for the level change to the Cordon.
--   2 Cordon: all asserts.
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local MODE = "quick"      -- "quick" or "full"
local OFF = false         -- true: freeplay switched off by the host file (old end)

local MARK = "FP_TEST_MARK"
local EXIT = "aes_2_esc_freeplay_level_changer"
local ALLOWED_NEW = { SCN_CREDITS_PLAYED = true, SCN_FREEPLAY_PLAYED = true, SCN_END_PEACE_PLAYED = true }
local FP = { x = -199.0, y = -19.9, z = -140.6 }   -- arrival point (rookie village, 8 m from the campfire)

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

local function key(name, what) return "fp_" .. what .. "_" .. string.lower(tostring(name)) end

local function write_host_file_off()
	-- the harness profile folder is fresh: write the host file with freeplay off and let coop_host_cfg read it
	local ok, err = pcall(function()
		local p = getFS():update_path("$app_data_root$", "coop_settings.ltx")
		local f = io.open(p, "a")
		if f then f:write("\n[freeplay]\nenabled = false\n") f:close() end
		coop_host_cfg.reload()
	end)
	return ok, err
end

qa.once("freeplay", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	local stage = tonumber(L.state_get("fp_stage", 0)) or 0
	local lvl = L.level_name()

	if stage == 0 then
		if lvl ~= "coop_l01_escape" then qa.assert("FP start on Cordon", false, tostring(lvl)) return end
		L.god(true)
		L.state_set("fp_stage", 1)
		L.state_set("fp_players", #L.players())
		if OFF then
			local ok, err = write_host_file_off()
			qa.assert("FP host file written with freeplay off", ok, tostring(err))
			qa.assert("FP coop_host_cfg reads freeplay.enabled = false", coop_host_cfg.bool("freeplay", "enabled", true) == false)
		end
		L.flag_give(MARK)
		for _, pl in ipairs(L.players()) do
			L.give_item(pl.id, "medkit", 3)
			L.give_item(pl.id, "bread", 2)
			L.set_money(pl.id, 12345)
		end
		L.task("freeplay_prepare", {
			function() return L.wait(4) end,
			function()
				for _, pl in ipairs(L.players()) do
					L.state_set(key(pl.name, "med"), L.count_item(pl.id, "medkit"))
					L.state_set(key(pl.name, "bread"), L.count_item(pl.id, "bread"))
					L.state_set(key(pl.name, "money"), L.money(pl.id))
					qa.event(string.format("FP record %s medkit=%s bread=%s money=%s", tostring(pl.name), tostring(L.count_item(pl.id, "medkit")), tostring(L.count_item(pl.id, "bread")), tostring(L.money(pl.id))))
				end
				L.state_set("fp_scenes0", played_set())
				return L.travel("aes_2", { timeout = 240, fallback = true })
			end,
			function(c, ok, why) qa.assert("FP route to CNPP-2 via the guide vote", ok == true, tostring(why)) end,
		})
		return
	end

	L.god(true)

	if stage == 1 then
		local arrived, level, secs = L.travel_arrived()
		qa.assert("FP arrived on CNPP-2", arrived and level == "coop_l11_stancia_2", string.format("%s after %s s", tostring(level), tostring(secs)))
		L.state_set("fp_stage", 2)
		L.state_set("fp_scenes1", played_set())
		L.task("freeplay_end", {
			function() return L.wait(20) end,
			function()
				local se = nil
				pcall(function() se = alife():object(EXIT) end)
				qa.assert("FP the exit " .. EXIT .. " exists on the server", se ~= nil)
				local lc = nil
				pcall(function() lc = level.object(EXIT) end)
				qa.event("FP exit online on this machine: " .. tostring(lc ~= nil))
				qa.assert("FP no freeplay flag before the ending", not L.flag_has("COOP_FREEPLAY_PENDING") and not L.flag_has("COOP_FREEPLAY_OPEN") and not L.flag_has("COOP_FREEPLAY_DONE"))
				qa.assert("FP freeplay setting reads " .. (OFF and "off" or "on"), pcall(function() return coop_scn_freeplay.enabled() end) and (coop_scn_freeplay.enabled() == (not OFF)), tostring(coop_scn_freeplay.enabled()))
				-- the final-scene flags
				if MODE == "quick" then
					story_flags.give_flag("SCN_END_PEACE_PLAYED")          -- the real end_peace scene must not play again on top of the manual end
					story_flags.give_flag("AES_2_THE_END_SPACE_RESTRICTOR_INFO")
					local ok, err = pcall(function() coop_scenes.defs.end_peace.on_end({}, nil, "all_acked") end)
					qa.assert("FP end_peace.on_end ran (requests the credits)", ok, tostring(err))
				else
					story_flags.give_flag("AES_2_THE_END_SPACE_RESTRICTOR_INFO")
				end
				qa.event("FP end triggered mode=" .. MODE .. " pending=" .. tostring(L.flag_has("COOP_FREEPLAY_PENDING")))
				if OFF then
					qa.assert("FP switched off: no PENDING flag after the end", not L.flag_has("COOP_FREEPLAY_PENDING"))
				else
					qa.assert("FP PENDING flag after the end", L.flag_has("COOP_FREEPLAY_PENDING"))
				end
				return L.wait_for(function() return coop_scenes.is_active("credits") end, MODE == "full" and 240 or 60)
			end,
			function(c, active)
				qa.assert("FP the credits started", active == true, tostring(active))
				local n = 0
				for _, pl in ipairs(L.players()) do
					if pcall(function() coop_scenes.on_skip(pl.id) end) then n = n + 1 end
				end
				qa.event("FP credits skip vote from " .. n .. " player(s)")
				if OFF then return L.done(true) end
				return L.wait(110)
			end,
			function()
				qa.assert("FP the level changed to the Cordon after the credits", false, "still on " .. tostring(L.level_name()) .. " 110 s after the skip vote, status: " .. tostring(coop_scn_freeplay.status()))
			end,
		})
		return
	end

	if stage == 2 then
		L.state_set("fp_stage", 3)
		L.task("freeplay_check", {
			function() return L.wait_for(function() return #L.players() >= (tonumber(L.state_get("fp_players", 0)) or 0) end, 90) end,
			function() return L.wait(15) end,
			function()
				qa.assert("FP all players are on the Cordon", lvl == "coop_l01_escape", tostring(lvl))
				local n = tonumber(L.state_get("fp_players", 0)) or 0
				qa.assert("FP all " .. n .. " players alive", #L.players() >= n and #L.players() >= 1, #L.players() .. " of " .. n)
				for _, pl in ipairs(L.players()) do
					local med0, bread0, money0 = tonumber(L.state_get(key(pl.name, "med"), -1)), tonumber(L.state_get(key(pl.name, "bread"), -1)), tonumber(L.state_get(key(pl.name, "money"), -1))
					local med, bread, money = L.count_item(pl.id, "medkit"), L.count_item(pl.id, "bread"), L.money(pl.id)
					qa.assert("FP " .. tostring(pl.name) .. " keeps the medkits", med0 >= 3 and med == med0, med .. " / " .. med0)
					qa.assert("FP " .. tostring(pl.name) .. " keeps the bread", bread0 >= 2 and bread == bread0, bread .. " / " .. bread0)
					qa.assert("FP " .. tostring(pl.name) .. " keeps the money", money0 == 12345 and money == money0, tostring(money) .. " / " .. tostring(money0))
					local p = nil
					pcall(function() p = pl.obj:position() end)
					if p ~= nil then
						qa.assert("FP " .. tostring(pl.name) .. " stands in the rookie village", L.dist3(p, FP) < 120, string.format("%.0f m from the arrival point", L.dist3(p, FP)))
					end
				end
				-- story flags intact, nothing replayed
				qa.assert("FP marker flag kept", L.flag_has(MARK))
				for _, f in ipairs({ "SCN_END_PEACE_PLAYED", "SCN_CREDITS_PLAYED", "COOP_FREEPLAY_DONE", "AES_2_THE_END_SPACE_RESTRICTOR_INFO" }) do
					qa.assert("FP story flag kept: " .. f, L.flag_has(f))
				end
				qa.assert("FP the exit flag is closed again on the Cordon", not L.flag_has("COOP_FREEPLAY_OPEN"))
				local before, after = split(L.state_get("fp_scenes1", "")), split(played_set())
				local lost, added = {}, {}
				for k in pairs(before) do if not after[k] then lost[#lost + 1] = k end end
				for k in pairs(after) do if not before[k] and not ALLOWED_NEW[k] then added[#added + 1] = k end end
				qa.assert("FP no played scene lost", #lost == 0, table.concat(lost, ","))
				qa.assert("FP no other scene played by the way home", #added == 0, table.concat(added, ","))
				-- the world keeps running
				local list = L.npcs_near(L.player(), 250) or {}
				qa.assert("FP NPCs live around the village (the world runs)", #list >= 3, tostring(#list))
				local sid = nil
				pcall(function() sid = L.find_online("sidorovich") end)
				qa.event("FP trader found online: " .. tostring(sid ~= nil))
				qa.assert("FP the repeatable-job and trader scripts still answer (coop_repeat_quests loaded)", pcall(function() return coop_repeat_quests ~= nil end))
				qa.event("FP done " .. tostring(coop_scn_freeplay.status()))
			end,
		})
		return
	end
	qa.event("FP stage " .. tostring(stage) .. " already finished")
end)
