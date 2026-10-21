--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): opens Sidorovich's talk window on Cordon (listen host) and takes an engine screenshot.
--   powershell -NoProfile -ExecutionPolicy Bypass -File <tools>\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner stu -Mode listen -Clients 1 `
--       -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 60 -CompareTimeout 10 -ResultDir <dir>
--   Second run for 16:9:  add  -Cfg vid=1280x720   (the harness always starts at 800x600 = 4:3; this hook then runs
--   "vid_mode 1280x720" + "vid_restart" before it opens the window)
-- Screenshots: qa_stu_<mode>__*.jpg in the client's $screenshots$ folder. Assertions: qa_assert.log ("STU ..." lines).
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local TRADER_BUNKER = { -243.0, -24.2, -135.0 }

local function check(name, ok, detail)
	qa.assert("STU " .. name, ok == true, detail)
end

local vid = qa.cfg.vid
local mode = (vid ~= nil and vid ~= "") and vid or "800x600"

L.task("soc_talk_ui", {
	function(c) return L.wait(8) end,
	function(c)
		local loaded = (soc_talk_ui ~= nil and soc_talk_ui.on_show ~= nil)
		check("soc_talk_ui.script is loaded", loaded, tostring(loaded))
		if vid ~= nil and vid ~= "" then
			pcall(function() get_console():execute("vid_mode " .. vid) end)
			pcall(function() get_console():execute("vid_restart") end)
			L.ev("STU video mode set to " .. vid)
			return L.wait(12)
		end
	end,
	function(c) return L.teleport(nil, TRADER_BUNKER) end,
	function(c, ok, why)
		check("teleport to the trader bunker", ok == true, tostring(why))
		return L.wait(8)
	end,
	function(c) return L.open_talk("sidorovich", { shot = "stu_" .. mode }) end,
	function(c, ok, why, shot)
		check("talk window opens (is_talking)", ok == true, tostring(why) .. ", shot " .. tostring(shot))
		local okc, shown = L.try(function() return soc_talk_ui.is_shown() end)
		check("decoration window is in the render list", okc and shown == true, tostring(shown))
		return L.wait(3)
	end,
	function(c) return L.screenshot("stu_" .. mode .. "_b") end,
	function(c, f)
		L.ev("STU second shot " .. tostring(f))
		L.close_talk()
		return L.wait(3)
	end,
	function(c)
		local okc, shown = L.try(function() return soc_talk_ui.is_shown() end)
		check("decoration window is removed after close", okc and shown == false, tostring(shown))
	end,
})
