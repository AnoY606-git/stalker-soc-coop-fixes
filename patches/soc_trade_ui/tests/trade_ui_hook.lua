--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): opens the TRADE window with Sidorovich on Cordon (listen host) and takes engine screenshots.
--   powershell -NoProfile -ExecutionPolicy Bypass -File <tools>\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner stt -Mode listen -Clients 1 `
--       -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 90 -CompareTimeout 10 -ResultDir <dir>
--   Second run for 16:9:  add  -Cfg vid=1280x720   (the harness always starts at 800x600 = 4:3; the hook then runs
--   "vid_mode 1280x720" + "vid_restart" before it opens the window)
--   Variant with the top panels skinned too: put  optional\soc_trade_top\gamedata  AFTER the stage in the lookup (copy it over the stage's gamedata) and run again.
-- Screenshots: qa_stt_<mode>__*.jpg in the client's $screenshots$ folder:
--   stt_<mode>_talk   the talk window (reference, the soc_talk_ui look)
--   stt_<mode>_trade  the trade window (the thing under test), stt_<mode>_trade_b a few seconds later
--   stt_<mode>_inv_N  taken every 4 s for 24 s AFTER the trade window is closed: press I (inventory) now by hand / with the harness's input tool to
--                     capture the normal inventory (and walk to a corpse and press USE for the loot window). There is no script call that opens them.
-- Assertions: qa_assert.log ("STT ..." lines).  Log check afterwards (client log):
--   findstr /i "ui_soc_trade actor_menu texture xml  cannot  can't" <client log>   -> nothing about ui_soc_trade / actor_menu may appear
-------------------------------------------------------------------------------------------------------
local L = qa_lib
local TRADER_BUNKER = { -243.0, -24.2, -135.0 }

local function check(name, ok, detail)
	qa.assert("STT " .. name, ok == true, detail)
end

local vid = qa.cfg.vid
local mode = (vid ~= nil and vid ~= "") and vid or "800x600"

-- the engine calls pda.actor_menu_mode(2) when the trade window opens (1 inventory, 3 upgrade, 4 loot)
local trade_seen = false
local function wrap_pda()
	pcall(function()
		if pda ~= nil and pda.trade_wnd_opened ~= nil and not pda.__stt_wrapped then
			local orig = pda.trade_wnd_opened
			pda.trade_wnd_opened = function(...)
				trade_seen = true
				return orig(...)
			end
			pda.__stt_wrapped = true
		end
	end)
end

local steps = {
	function(c) return L.wait(8) end,
	function(c)
		wrap_pda()
		if vid ~= nil and vid ~= "" then
			pcall(function() get_console():execute("vid_mode " .. vid) end)
			pcall(function() get_console():execute("vid_restart") end)
			L.ev("STT video mode set to " .. vid)
			return L.wait(12)
		end
	end,
	function(c) wrap_pda() return L.teleport(nil, TRADER_BUNKER) end,
	function(c, ok, why)
		check("teleport to the trader bunker", ok == true, tostring(why))
		return L.wait(8)
	end,
	function(c) return L.open_talk("sidorovich", { shot = "stt_" .. mode .. "_talk" }) end,
	function(c, ok, why, shot)
		check("talk window opens (is_talking)", ok == true, tostring(why) .. ", shot " .. tostring(shot))
		local lo = L.local_player()
		local okc, err = pcall(function() lo:switch_to_trade() end)
		L.ev("STT switch_to_trade " .. tostring(okc) .. " " .. tostring(err))
		return L.wait(5)
	end,
	function(c)
		check("trade window opened (pda.actor_menu_mode(2) seen)", trade_seen == true, tostring(trade_seen))
		return L.screenshot("stt_" .. mode .. "_trade")
	end,
	function(c, f)
		L.ev("STT trade shot " .. tostring(f))
		return L.wait(4)
	end,
	function(c) return L.screenshot("stt_" .. mode .. "_trade_b") end,
	function(c, f)
		L.ev("STT trade shot b " .. tostring(f))
		pcall(function() get_hud():HideActorMenu() end)
		L.close_talk()
		return L.wait(3)
	end,
}
-- inventory / loot window: no script entry point, so wait and photograph while the harness (or a person) presses I
for i = 1, 6 do
	steps[#steps + 1] = function(c) return L.screenshot("stt_" .. mode .. "_inv_" .. i) end
	steps[#steps + 1] = function(c, f)
		L.ev("STT inv shot " .. i .. " " .. tostring(f))
		return L.wait(4)
	end
end

L.task("soc_trade_ui", steps)
