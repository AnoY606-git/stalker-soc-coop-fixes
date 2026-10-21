--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). run_coop.ps1 -Mode listen -Clients 1 -Map coop_l01_escape -Hooks <this file> -SoakSeconds 60
-- Gives the first player every artifact section whose icon was checked (plain af_x, af_x_soc twins) and asserts, from system_ini,
-- that each section reads the SoC inv_grid cell and the real SoC name string. Then opens nothing: look at the inventory
-- screenshot (L.screenshot) if wanted. Verdict: python tools\stalker_xrmpe\qa_verdict.py <ResultDir> --prefix AI
-------------------------------------------------------------------------------------------------------
local L = qa_lib
-- section = { x, y } expected cell (the cell holds the real SoC icon, see tools\artifact_icons.py)
local WANT = {
	af_cristall_flower = { 24, 0 }, af_cristall_flower_soc = { 24, 0 },
	af_medusa = { 9, 4 }, af_medusa_soc = { 9, 4 },
	af_dummy_battery = { 36, 1 }, af_dummy_battery_soc = { 36, 1 },
	af_dummy_spring_soc = { 31, 1 }, af_dummy_pellicle_soc = { 32, 1 },
	af_night_star_soc = { 24, 1 }, af_fireball_soc = { 35, 1 },
}
qa.once("artifact_icons", function(t, lo)
	local ini = system_ini()
	for sec, xy in pairs(WANT) do
		local x = ini:r_u32(sec, "inv_grid_x")
		local y = ini:r_u32(sec, "inv_grid_y")
		qa.assert("AI grid " .. sec, x == xy[1] and y == xy[2], x .. "," .. y .. " want " .. xy[1] .. "," .. xy[2])
		qa.assert("AI size " .. sec, ini:r_u32(sec, "inv_grid_width") == 1 and ini:r_u32(sec, "inv_grid_height") == 1, "")
	end
	if OnServer() then
		for sec, _ in pairs(WANT) do L.give_item(1, sec, 1) end
	end
end)
