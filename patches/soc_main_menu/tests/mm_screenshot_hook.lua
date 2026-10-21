-- Main menu screenshot hook (soc_main_menu). Opens the menu with the console command, waits, takes engine screenshots.
-- qa.cfg.vid=1280x720 (optional) switches the resolution first with vid_mode + vid_restart.
local st = {}
local function con(c)
	local ok, err = pcall(function() get_console():execute(c) end)
	qa.event("CON " .. c .. " -> " .. (ok and "ok" or tostring(err)))
end
qa.hooks.mm_shot = function(t, lo)
	if OnServer() then return end
	if qa.cfg.vid and not st.vid and t >= 4 then
		st.vid = true
		con("vid_mode " .. qa.cfg.vid)
		con("vid_restart")
		return
	end
	local base = qa.cfg.vid and 14 or 6
	if t >= base and not st.on then
		st.on = true
		con("main_menu on")
	end
	if t >= base + 8 and not st.s1 then
		st.s1 = true
		con("screenshot")
		qa.event("MM shot 1")
	end
	if t >= base + 12 and not st.s2 then
		st.s2 = true
		con("screenshot")
		qa.event("MM shot 2")
	end
	if t >= base + 14 and not st.done then
		st.done = true
		qa.assert("main menu hook ran", true, "t=" .. tostring(t))
	end
end
