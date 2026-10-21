--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped), NOT RUN YET (written offline, see NOTES.md "Test plan").
-- Technician parts are gone: no alife object of the five jup_b200_tech_materials_* sections, and the Bar technician (Plyushkin)
-- no longer talks about them while his repair / upgrade data still works.
--
-- Listen mode, ONE game process, start on Cordon (the Bar alife only comes online after a travel, see stalker.md):
--   run_coop.ps1 -Map coop_l01_escape -Owner noparts -Mode listen -Clients 1 -Cfg no_respawn=1 `
--     -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 240 -CompareTimeout 10 -ResultDir <dir>
-- (<stage> = build.py --stage output of the whole tree with --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing,inventory_carry)
-- Verdict: python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix NP --require 12
--
-- Stage 0 (Cordon): scan EVERY alife object (all levels are registered, online or not) for the five sections / names containing
--   "tech_materials" (expect 0), check the Lua helpers and strings, then travel to the Bar through the guide vote.
-- Stage 1 (Bar, new VM): scan again (expect 0), find Plyushkin, check his greeting string, that the cut dialog strings are gone, that
--   inventory_upgrades still lets him upgrade a pistol, then open his talk window (expect is_talking).
-------------------------------------------------------------------------------------------------------
local L = qa_lib

local FAMILY = {
	jup_b200_tech_materials_wire = true,        -- coil of copper wire
	jup_b200_tech_materials_acetone = true,     -- can of rosin
	jup_b200_tech_materials_textolite = true,   -- textolite base
	jup_b200_tech_materials_transistor = true,  -- box of transistors
	jup_b200_tech_materials_capacitor = true,   -- pack of capacitors
}
local TECH = "bar_smart_terrain_10_stalker_plyushkin"
local CUT_STRINGS = {
	TECH .. "_hand_over_the_trash_dialog_2", TECH .. "_hand_over_the_trash_dialog_5",
	TECH .. "_what_kind_of_junk_is_needed_dialog_0", TECH .. "_what_kind_of_junk_is_needed_dialog_1",
}

local function scan()
	local sim = alife()
	local hits, total = {}, 0
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil then
			total = total + 1
			local sec, nm = "", ""
			pcall(function() sec = se:section_name() nm = se:name() end)
			if FAMILY[sec] or string.find(nm, "tech_materials", 1, true) then
				hits[#hits + 1] = string.format("%d %s %s", id, sec, nm)
			end
		end
	end
	return #hits, total, hits
end

local function check_scan(tag)
	local n, total, hits = scan()
	for i = 1, math.min(#hits, 10) do qa.event("NP leftover " .. hits[i]) end
	qa.assert("NP " .. tag .. ": no technician part among the alife objects", n == 0, string.format("%d of %d objects", n, total))
	qa.assert("NP " .. tag .. ": the scan saw the whole world (many objects)", total > 5000, tostring(total))
end

local function check_text_and_lua(tag)
	local g = ""
	pcall(function() g = game.translate_string(TECH .. "_start_dialog_0") end)
	qa.event("NP " .. tag .. " greeting=" .. tostring(g))
	qa.assert("NP " .. tag .. ": technician greeting no longer asks 'brought anything'", g ~= "" and not string.find(g, "brought anything", 1, true) and not string.find(g, string.char(0xEF, 0xF0, 0xE8, 0xED, 0xE5, 0xF1), 1, true), g)
	for _, sid in ipairs(CUT_STRINGS) do
		local t = sid
		pcall(function() t = game.translate_string(sid) end)
		qa.assert("NP " .. tag .. ": cut dialog string is gone " .. sid, t == sid, t)
	end
	local ok, f = pcall(function() return dialogs_item.if_actor_has_materials_wire_3x end)
	qa.assert("NP " .. tag .. ": Lua helper if_actor_has_materials_wire_3x is removed", ok and f == nil, tostring(ok) .. " " .. tostring(f))
	ok, f = pcall(function() return dialogs_item.transfer_materials_transistor_3x end)
	qa.assert("NP " .. tag .. ": Lua helper transfer_materials_transistor_3x is removed", ok and f == nil, tostring(ok) .. " " .. tostring(f))
	ok, f = pcall(function() return dialogs_item.transfer_mutant_chimera_part_1x end)
	qa.assert("NP " .. tag .. ": neighbouring helper transfer_mutant_chimera_part_1x is still there", ok and f ~= nil, tostring(ok) .. " " .. tostring(f))
end

qa.once("no_parts", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	if _G.__np_started then return end   -- appended to three scripts that can load at different times: start once
	_G.__np_started = true
	local stage = L.state_get("np_stage", 0)
	if stage == 0 then
		L.state_set("np_stage", 1)
		L.god(true)
		L.task("no_parts cordon", {
			function() return L.wait(15) end,
			function()
				check_scan("cordon start")
				check_text_and_lua("cordon start")
				return L.travel("bar", { timeout = 200, fallback = true })
			end,
			-- a successful level change restarts the Lua VM: this step is only reached on failure
			function(c, ok, why) qa.assert("NP route to the Bar via the guide vote", ok == true, tostring(why)) end,
		})
	else
		local arrived, level, secs = L.travel_arrived()
		qa.assert("NP arrived on the Bar", arrived and level == "coop_l05_bar", string.format("%s after %s s", tostring(level), tostring(secs)))
		L.god(true)
		local npc
		L.task("no_parts bar", {
			function() return L.wait(25) end,
			function()
				check_scan("bar")
				npc = L.find_online("plyushkin")
				qa.assert("NP Bar technician Plyushkin is online", npc ~= nil, (npc ~= nil) and npc:name() or "nil")
				if npc == nil then return L.done(false, "no technician") end
				local ok, can = pcall(function() return inventory_upgrades.can_upgrade_item("wpn_pm", TECH) end)
				qa.event("NP can_upgrade_item(wpn_pm) ok=" .. tostring(ok) .. " -> " .. tostring(can))
				qa.assert("NP technician can still upgrade a pistol (no parts needed)", ok and can == true, tostring(ok) .. " " .. tostring(can))
				ok, can = pcall(function() return inventory_upgrades.can_repair_item("wpn_pm", 0.5, TECH) end)
				qa.event("NP can_repair_item ok=" .. tostring(ok) .. " -> " .. tostring(can))
				return L.open_talk(npc, { shot = "bar_tech_talk" })
			end,
			function(c, ok, why)
				qa.assert("NP technician talk window opens (greeting dialog, repair / upgrade buttons)", ok == true, tostring(why))
				check_text_and_lua("bar")
				L.close_talk()
			end,
		})
	end
end)
