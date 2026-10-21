--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): shows the engine's "game saved" HUD static and takes engine screenshots of it.
--   powershell -NoProfile -ExecutionPolicy Bypass -File <tools>\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner svmsg -Mode listen -Clients 1 `
--       -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 60 -CompareTimeout 10 -ResultDir <dir>
--   16:9 (the real layout): add  -Cfg vid=1920x1080  (the harness starts at 800x600 = 4:3; the hook runs vid_mode + vid_restart first)
-- What is shot (qa_<tag>__*.jpg in the client screenshots folder; the message lives 3 s, shots are taken at once):
--   svmsg_<mode>_static     the same static ("game_saved") the engine uses, filled by script (deterministic)
--   svmsg_<mode>_autosave   the "autosave" static
--   svmsg_<mode>_real       a real server save (console "save quicksave - N"), the way FOSTER's screenshot was made
-- Expected: the text is centered at the BOTTOM of the screen (about 95% of the height, like SoC), not under the crosshair (69%).
-- Assertions in qa_assert.log ("SVMSG ..."): the static exists and its window is readable (GetWndPos ignores the anchor, so the position itself is judged on the screenshots).
-------------------------------------------------------------------------------------------------------
local L = qa_lib

local function check(name, ok, detail)
	qa.assert("SVMSG " .. name, ok == true, detail)
end

local vid = qa.cfg.vid
local mode = (vid ~= nil and vid ~= "") and vid or "800x600"

local function show_static(id, text)
	local hud = get_hud()
	hud:AddCustomStatic(id, true)
	local st = hud:GetCustomStatic(id)
	if st == nil then return nil end
	if text ~= nil then
		pcall(function() st:wnd():TextControl():SetText(text) end)
	end
	return st
end

-- reads the window rectangle: bottom edge as a fraction of the UI height (1080 on 16:9, 768 on 4:3 in the engine's UI space)
local function bottom_fraction(st)
	local ok, v = pcall(function()
		local w = st:wnd()
		local pos = w:GetWndPos()
		return { y = pos.y, h = w:GetHeight() }
	end)
	if not ok or v == nil then return nil, tostring(v) end
	local ui_h = (vid ~= nil and vid ~= "" and (string.match(vid, "x(%d+)") == "1080" or string.match(vid, "x(%d+)") == "720")) and 1080 or 768
	return (v.y + v.h) / ui_h, "y=" .. tostring(v.y) .. " h=" .. tostring(v.h) .. " ui_h=" .. tostring(ui_h)
end

local steps = {
	function(c) return L.wait(8) end,
	function(c)
		if vid ~= nil and vid ~= "" then
			pcall(function() get_console():execute("vid_mode " .. vid) end)
			pcall(function() get_console():execute("vid_restart") end)
			L.ev("SVMSG video mode set to " .. vid)
			return L.wait(12)
		end
	end,
	function(c)
		local st = show_static("game_saved", "Game saved: quicksave - 9")
		check("game_saved static exists", st ~= nil)
		if st ~= nil then
			local f, d = bottom_fraction(st)
			L.ev("SVMSG game_saved " .. tostring(d))
			-- GetWndPos returns the node's own x/y/height scaled to the screen, WITHOUT the anchor offset (the anchor is applied when the engine
			-- draws it): y=11 at 600 px gives 6.1 even though the text is drawn at the bottom. So this is only logged; the position is judged on the
			-- screenshots (the real save and autosave shots show the text at 96% and 93% of the height, centred).
			check("game_saved window readable", f ~= nil, tostring(f) .. " " .. tostring(d))
		end
		return L.screenshot("svmsg_" .. mode .. "_static")
	end,
	function(c, f)
		L.ev("SVMSG static shot " .. tostring(f))
		return L.wait(4)
	end,
	function(c)
		local st = show_static("autosave", nil)
		check("autosave static exists", st ~= nil)
		return L.screenshot("svmsg_" .. mode .. "_autosave")
	end,
	function(c, f)
		L.ev("SVMSG autosave shot " .. tostring(f))
		return L.wait(4)
	end,
	-- a real save: the engine itself shows the message on the clients; take the shot a moment after the file appears
	function(c) return L.save() end,
	function(c, name)
		check("real save written", name ~= nil, tostring(name))
		return L.screenshot("svmsg_" .. mode .. "_real")
	end,
	function(c, f)
		L.ev("SVMSG real shot " .. tostring(f))
		return L.wait(2)
	end,
}

L.task("soc_save_message", steps)
