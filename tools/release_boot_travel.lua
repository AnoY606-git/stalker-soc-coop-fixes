--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): release.py boot check for levels that only come alive when reached from Cordon (the Bar).
-- Listen mode, start map coop_l01_escape, -Cfg dest=bar -Cfg no_respawn=1.  Travels through the guide + party vote (qa_lib.travel), then
-- on the target level checks that the player lives and that the level's alife is online (NPCs near the player).
-- Uses qa_lib's action API: L.task / L.wait / L.travel / L.travel_arrived (see tools\stalker_xrmpe\lua\QA_LIB.md).
-------------------------------------------------------------------------------------------------------
local L = qa_lib

qa.once("release_boot_travel", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	if _G.__rb_started then return end   -- appended to three scripts that can load at different times: start once
	_G.__rb_started = true
	local dest = qa.cfg.dest or "bar"
	local code, lvl = L.guide_code(dest)
	local stage = L.state_get("rb_stage", 0)
	if stage == 0 then
		L.state_set("rb_stage", 1)
		L.god(true)
		L.task("release_boot_travel", {
			function() return L.wait(6) end,
			-- a successful level change restarts the Lua VM: this action only ends on failure
			function() return L.travel(dest, { timeout = 200, fallback = true }) end,
			function(c, ok, why) qa.assert("RB route to " .. tostring(lvl) .. " via the guide vote", ok == true, tostring(why)) end,
		})
	else
		local arrived, level, secs = L.travel_arrived()
		qa.assert("RB route arrived on " .. tostring(lvl), arrived and level == lvl, string.format("%s after %s s", tostring(level), tostring(secs)))
		L.god(true)
		L.task("release_boot_alife", {
			function() return L.wait(20) end,
			function()
				local list = L.npcs_near(L.player(), 400) or {}
				qa.assert("RB " .. tostring(lvl) .. " alife is online (NPCs within 400 m)", #list >= 1, tostring(#list))
				qa.assert("RB player alive on " .. tostring(lvl), #L.players() >= 1, tostring(#L.players()))
			end,
		})
	end
end)
