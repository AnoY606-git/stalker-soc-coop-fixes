-- weapon upgrades check: every weapon section resolves, technicians list it, and upgrades install without a crash
local WEAPONS = {"wpn_ak74", "wpn_ak74_m1", "wpn_ak74u", "wpn_ak74u_m1", "wpn_fn2000", "wpn_fn2000_m1", "wpn_rpg7", "wpn_rg-6", "wpn_vintorez", "wpn_lr300", "wpn_lr300_m1", "wpn_mp5", "wpn_mp5_m1", "wpn_val", "wpn_val_m1", "wpn_gauss", "wpn_groza", "wpn_groza_m1", "wpn_hpsa", "wpn_pm", "wpn_pb", "wpn_walther", "wpn_walther_m1", "wpn_usp", "wpn_fort", "wpn_fort_m1", "wpn_toz34", "wpn_toz34_m1", "wpn_toz34_m2", "wpn_svd", "wpn_svu", "wpn_l85", "wpn_l85_m1", "wpn_l85_m2", "wpn_bm16", "wpn_bm16_m1", "wpn_spas12", "wpn_protecta", "wpn_wincheaster1300", "wpn_wincheaster1300_m1", "wpn_colt1911", "wpn_colt1911_m1", "wpn_beretta", "wpn_desert_eagle", "wpn_desert_eagle_m1", "wpn_sig220", "wpn_sig550", "wpn_sig550_m1", "wpn_abakan", "wpn_abakan_m1", "wpn_abakan_m2", "wpn_g36", "wpn_pkm", "wpn_fiveseven", "wpn_saiga12", "wpn_stechkin", "wpn_glock17", "wpn_tt33", "wpn_grach", "wpn_gsh18", "wpn_sr1m", "wpn_p90", "wpn_bizon", "wpn_mp5sd", "wpn_ump45", "wpn_apb", "wpn_pmm", "wpn_desert_eagle_silver", "wpn_fort17", "wpn_usp_match", "wpn_sig220r", "wpn_ak101", "wpn_sig552", "wpn_rgm-40", "wpn_akm"}
local SAMPLE = { "wpn_fn2000", "wpn_fn2000_m1", "wpn_spas12", "wpn_svu", "wpn_gauss", "wpn_rpg7", "wpn_rg-6", "wpn_sig552", "wpn_lr300_m1", "wpn_bm16_m1", "wpn_colt1911_m1", "wpn_mp5sd", "wpn_pmm", "wpn_fiveseven", "wpn_ak74" }
local MECH = { "bar_smart_terrain_10_stalker_plyushkin", "mil_smart_terrain_11_freedom_shurup" }
local did = {}
local function split(s)
	local t = {}
	for w in string.gmatch(s or "", "[^,%s]+") do t[#t + 1] = w end
	return t
end
local function check_all()
	local sys = system_ini()
	local iu = ini_file("item_upgrades.ltx")
	local inv = sys
	local listed = {}
	for i = 0, inv:line_count("upgraded_inventory") - 1 do
		local _, id = inv:r_line("upgraded_inventory", i, "", "")
		listed[id] = true
	end
	local mi = ini_file("misc" .. string.char(92) .. "stalkers_upgrade_info.ltx")
	local bad, nupg = {}, 0
	local inv_set = {}
	for i = 0, inv:line_count("upgraded_inventory") - 1 do
		local _, k = inv:r_line("upgraded_inventory", i, "", "")
		inv_set[k] = true
	end
	for _, w in ipairs(WEAPONS) do
		local why = nil
		if not sys:section_exist(w) then why = "no section"
		else
			local up = sys:line_exist(w, "upgrades") and sys:r_string(w, "upgrades") or ""
			local trees = split(up)
			if #trees == 0 then why = "empty upgrades" end
			for _, t in ipairs(trees) do
				if not iu:section_exist(t) then why = "tree " .. t .. " missing" break end
				for _, e in ipairs(split(iu:r_string(t, "elements"))) do
					if not iu:section_exist(e) then why = "element " .. e .. " missing" break end
					local sec = iu:r_string(e, "section")
					if not iu:section_exist(sec) then why = "upgrade section " .. sec .. " missing" break end
					nupg = nupg + 1
				end
				if why then break end
			end
			if not why and not listed[w] then why = "not in upgraded_inventory" end
			for _, m in ipairs(MECH) do
				if not why and not mi:line_exist(m, w) then why = "not in technician " .. m end
				if not why and not inventory_upgrades.can_upgrade_item(w, m) then why = "can_upgrade_item false for " .. m end
			end
		end
		if why then bad[#bad + 1] = w .. ": " .. why end
	end
	qa.assert("all " .. #WEAPONS .. " weapon sections resolve (trees, elements, sections, technicians)", #bad == 0, #bad == 0 and (nupg .. " upgrade slots checked") or table.concat(bad, "; "))
end
qa.hooks.wu = function(t, lo)
	if not OnServer() then return end
	if type(db.mp_actors) ~= "table" then return end
	local a
	for id, o in pairs(db.mp_actors) do a = o break end
	if not a then return end
	if not did.t0 then did.t0 = t end
	local dt = t - did.t0
	if dt > 2 and not did.chk then did.chk = true check_all() end
	if dt > 4 and not did.spawn then
		did.spawn = true
		did.items = {}
		local iu = ini_file("item_upgrades.ltx")
		local sys = system_ini()
		for _, w in ipairs(SAMPLE) do
			local se = alife():create(w, a:position(), a:level_vertex_id(), a:game_vertex_id(), a:id())
			local t1 = split(sys:r_string(w, "upgrades"))[1]
			local e1 = split(iu:r_string(t1, "elements"))[1]
			did.items[#did.items + 1] = { w = w, id = se.id, up = e1 }
		end
	end
	if dt > 9 and not did.apply then
		did.apply = true
		for _, it in ipairs(did.items) do
			local se = alife():object(it.id)
			local ok, err = pcall(function()
				local pk = net_packet()
				se:STATE_Write(pk)
				local n = pk:r_elapsed()
				local b = {}
				for i = 1, n do b[i] = pk:r_u8() end
				local out = net_packet()
				for i = 1, n - 16 do out:w_u8(b[i]) end
				out:w_u8(1) out:w_u8(0) out:w_u8(0) out:w_u8(0)
				for c in string.gmatch(it.up, ".") do out:w_u8(string.byte(c)) end
				out:w_u8(0)
				for i = n - 11, n do out:w_u8(b[i]) end
				se:STATE_Read(out, n - 16 + 4 + #it.up + 1 + 12)
				-- read back
				local pk2 = net_packet()
				se:STATE_Write(pk2)
				local m = pk2:r_elapsed()
				local found = false
				local s2 = {}
				for i = 1, m do s2[i] = string.char(pk2:r_u8()) end
				found = string.find(table.concat(s2), it.up, 1, true) ~= nil
				qa.event("UPGRADE " .. it.w .. " bytes " .. n .. " -> " .. m .. " upgrade string in entity state: " .. tostring(found))
				if not found then error("upgrade not found in state") end
			end)
			qa.assert("upgrade " .. it.up .. " installed on " .. it.w, ok, ok and "" or tostring(err))
		end
	end
	if dt > 16 and not did.alive then
		did.alive = true
		local n = 0
		for _, it in ipairs(did.items) do if alife():object(it.id) then n = n + 1 end end
		qa.assert("server alive and all " .. #did.items .. " upgraded weapons still exist after 7 s", n == #did.items, n .. "/" .. #did.items)
	end
end
