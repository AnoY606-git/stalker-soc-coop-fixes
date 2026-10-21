-- Slot-restore test v2.
-- Setup: per player, the HIGHER-id weapons/outfit end up in the slots and the lower-id ones in the backpack (as after a player swapped them
-- by hand). Items are created X0,Y0,Z0 (they auto-slot), A*,  B*; X0..Z0 are handed to a holder NPC (transfer_item), B* go out and back
-- (they take the empty slots), A* stay in the backpack.  Then save (game_sv.saveGame) and load (game_sv.loadLastSave) twice.
-- Every role dumps slots + inventory every 3 s ("SLOT" lines in qa_events.log).  State survives a load in $logs$\slot_stage.txt.
local H = { stage = nil, pt = 0, loads = 0, ids = "", expect = {}, last_dump = 0, q = nil, qi = 1, qt = 0 }

local function spath() return getFS():update_path("$logs$", "slot_stage.txt") end

local function wstate()
	local f = io.open(spath(), "w")
	if not f then return end
	f:write("stage=" .. tostring(H.stage), "\n")
	f:write("loads=" .. tostring(H.loads), "\n")
	f:write("ids=" .. tostring(H.ids), "\n")
	for name, s in pairs(H.expect) do f:write("expect_" .. name .. "=" .. s, "\n") end
	f:close()
end

local function rstate()
	local f = io.open(spath(), "r")
	if not f then return false end
	for line in f:lines() do
		local k, v = string.match(line, "^([%w_]+)=(.*)$")
		if k == "stage" then H.stage = tonumber(v)
		elseif k == "loads" then H.loads = tonumber(v)
		elseif k == "ids" then H.ids = v
		elseif string.sub(k, 1, 7) == "expect_" then H.expect[string.sub(k, 8)] = v end
	end
	f:close()
	return true
end

local function slots_of(p)
	local out = {}
	for s = 0, 14 do
		local ok, it = pcall(function() return p:item_in_slot(s) end)
		if ok and it then out[#out + 1] = string.format("s%d=%s#%d", s, it:section(), it:id()) end
	end
	local ok, w = pcall(function() return p:get_current_outfit() end)
	if ok and w then out[#out + 1] = string.format("outfit=%s#%d", w:section(), w:id()) end
	local ok2, a = pcall(function() return p:active_item() end)
	if ok2 and a then out[#out + 1] = string.format("active=%s#%d", a:section(), a:id()) end
	return table.concat(out, ",")
end

-- the part that must survive a load: weapon slots 2/3, outfit (slot 7), helmet slot 12, money and the multiset of sections
local function key_of(p)
	local out = {}
	for _, sl in ipairs({ 2, 3, 7, 12 }) do
		local ok, it = pcall(function() return p:item_in_slot(sl) end)
		out[#out + 1] = (ok and it) and string.format("s%d=%s#%d", sl, it:section(), it:id()) or string.format("s%d=none", sl)
	end
	local cnt, names = {}, {}
	p:iterate_inventory(function(_, it) local sc = it:section(); if not cnt[sc] then names[#names + 1] = sc end; cnt[sc] = (cnt[sc] or 0) + 1 end, p)
	table.sort(names)
	local fp = {}
	for _, sc in ipairs(names) do fp[#fp + 1] = sc .. "x" .. cnt[sc] end
	local okm, m = pcall(function() return p:money() end)
	return table.concat(out, ",") .. ";m=" .. tostring(okm and m or "?") .. ";inv=" .. table.concat(fp, ",")
end

local function inv_of(p)
	local out = {}
	p:iterate_inventory(function(_, it)
		local par = "-"
		local ok, pr = pcall(function() return it:parent() end)
		if ok and pr then par = tostring(pr:id()) end
		out[#out + 1] = string.format("%s#%d(p%s)", it:section(), it:id(), par)
	end, p)
	table.sort(out)
	return table.concat(out, ",")
end

local function alife_view()
	if not OnServer() then return "" end
	local out = {}
	for id in string.gmatch(H.ids, "%d+") do
		local ok, o = pcall(function() return alife():object(tonumber(id)) end)
		if ok and o then out[#out + 1] = string.format("%s#%s(par%s)", o:section_name(), id, tostring(o.parent_id))
		else out[#out + 1] = "#" .. id .. "(gone)" end
	end
	return table.concat(out, ",")
end

local function dump(tag, lo)
	local role = qa.cfg.role or "?"
	if OnServer() then
		for id, p in pairs(db.mp_actors) do
			pcall(function()
				qa.event(string.format("SLOT %s role=%s srv name=%s id=%d alive=%s level=%s | %s | inv: %s", tag, role, tostring(p:name()), id, tostring(p:alive()), level.name(), slots_of(p), inv_of(p)))
			end)
		end
		qa.event(string.format("SLOT %s role=%s ALIFE %s", tag, role, alife_view()))
	end
	if lo and not IsDedicatedServer() then
		pcall(function()
			qa.event(string.format("SLOT %s role=%s cli name=%s id=%d level=%s | %s | inv: %s", tag, role, tostring(lo:name()), lo:id(), level.name(), slots_of(lo), inv_of(lo)))
		end)
	end
end

-- nearest living stalker NPC to p (the holder)
local function find_holder(p)
	local best, bd = nil, 1e9
	for id, st in pairs(db.storage) do
		local o = st and st.object
		if o and id ~= p:id() then
			local ok, res = pcall(function()
				if IsStalker(o) and o:alive() then return o:position():distance_to(p:position()) end
				return nil
			end)
			if ok and res and res < bd then best, bd = o, res end
		end
	end
	return best, bd
end

local function create_in(p, sect)
	local o = alife():create(sect, p:position(), p:level_vertex_id(), p:game_vertex_id(), p:id())
	return o.id
end

local function xfer(from, id, to, why)
	local o = level.object_by_id(id)
	if not o then qa.event("SLOT xfer " .. why .. " id=" .. id .. " object missing") return end
	local ok, err = pcall(function() from:transfer_item(o, to) end)
	qa.event(string.format("SLOT xfer %s id=%d %s %s", why, id, tostring(ok), tostring(err)))
end

local function build_queue(p)
	local R = {}   -- records
	local q = {}
	local holder
	q[#q + 1] = function()
		local hb, hd = find_holder(p)
		holder = hb
		qa.event("SLOT holder " .. (hb and (hb:name() .. " dist=" .. string.format("%.0f", hd)) or "NONE"))
		R.X0 = create_in(p, "wpn_ak74");  R.Y0 = create_in(p, "wpn_pm");   R.Z0 = create_in(p, "stalker_outfit")
		R.A1 = create_in(p, "wpn_abakan"); R.A2 = create_in(p, "wpn_fort"); R.A3 = create_in(p, "merc_outfit")
		R.B1 = create_in(p, "wpn_lr300");  R.B2 = create_in(p, "wpn_walther"); R.B3 = create_in(p, "specops_outfit")
		H.ids = table.concat({ R.X0, R.Y0, R.Z0, R.A1, R.A2, R.A3, R.B1, R.B2, R.B3 }, ",")
		qa.event("SLOT created ids=" .. H.ids)
	end
	q[#q + 1] = function() dump("AFTERCREATE", nil) end
	q[#q + 1] = function()
		if not holder then return end
		xfer(p, R.X0, holder, "X0->holder"); xfer(p, R.Y0, holder, "Y0->holder"); xfer(p, R.Z0, holder, "Z0->holder")
	end
	q[#q + 1] = function() dump("HOLDER1", nil) end
	q[#q + 1] = function()
		if not holder then return end
		xfer(p, R.B1, holder, "B1->holder"); xfer(p, R.B2, holder, "B2->holder"); xfer(p, R.B3, holder, "B3->holder")
	end
	q[#q + 1] = function()
		if not holder then return end
		xfer(holder, R.B1, p, "B1<-holder"); xfer(holder, R.B2, p, "B2<-holder"); xfer(holder, R.B3, p, "B3<-holder")
	end
	q[#q + 1] = function() pcall(function() p:give_money(12000 + (p:id() % 1000)) end) end
	q[#q + 1] = function() dump("SETUPDONE", nil) end
	return q
end

local function disable_harness_respawn()
	qa.cfg.no_respawn = "1"
	qa.first_level = "__slot_test__"
end

qa.hooks.slotrestore = function(t, lo)
	local now = time_global()
	if H.stage == nil then
		if not rstate() then H.stage = 0 end
		H.pt = now
		qa.event("SLOT init stage=" .. tostring(H.stage) .. " loads=" .. tostring(H.loads))
	end
	if H.loads > 0 then disable_harness_respawn() end
	if now - H.last_dump >= 3000 then
		H.last_dump = now
		dump("S" .. tostring(H.stage) .. "L" .. tostring(H.loads), lo)
	end
	if not OnServer() then return end
	local want = tonumber(qa.cfg.clients or "1") or 1
	local actors = {}
	for id, v in pairs(db.mp_actors) do
		if v ~= nil and v:alive() and v:section() ~= "spectator" then actors[#actors + 1] = v end
	end
	local el = now - H.pt
	if H.stage == 0 then
		if #actors >= want and t > 14 then
			H.q = {}
			for _, a in ipairs(actors) do
				for _, f in ipairs(build_queue(a)) do H.q[#H.q + 1] = f end
			end
			H.qi = 1; H.qt = now - 10000
			H.stage = 1; H.pt = now
			qa.event("SLOT setup start")
		end
	elseif H.stage == 1 then
		if now - H.qt >= 3500 then
			H.qt = now
			local f = H.q[H.qi]
			if f then
				local ok, err = pcall(f)
				if not ok then qa.event("SLOT setup step " .. H.qi .. " error " .. tostring(err)) end
				H.qi = H.qi + 1
			else
				for _, v in ipairs(actors) do
					H.expect[v:name()] = key_of(v)
					qa.event("SLOT EXPECT " .. v:name() .. " " .. H.expect[v:name()])
				end
				H.stage = 2; H.pt = now; wstate()
			end
		end
	elseif H.stage == 2 then
		if el > 6000 then
			dump("PRESAVE", lo)
			H.stage = 21; H.pt = now; wstate()
			local ok, err = pcall(function() game_sv.saveGame(0) end)
			qa.event("SLOT saveGame " .. tostring(ok) .. " " .. tostring(err))
		end
	elseif H.stage == 21 then
		if el > 8000 then
			dump("PRELOAD", lo)
			H.stage = 3; H.loads = H.loads + 1; H.pt = now; wstate()
			qa.event("SLOT loadLastSave #" .. H.loads)
			local ok, err = pcall(function() game_sv.loadLastSave(0) end)
			qa.event("SLOT loadLastSave call " .. tostring(ok) .. " " .. tostring(err))
		end
	elseif H.stage == 3 then
		-- poll: every player has exactly his own body back (highest id of that name) and no extra living body is left
		local all_ok, detail = true, {}
		local used = {}
		for name, exp in pairs(H.expect) do
			local found
			for _, v in ipairs(actors) do
				if not used[v:id()] and key_of(v) == exp then found = v break end
			end
			if found == nil then
				all_ok = false
				local seen = {}
				for _, v in ipairs(actors) do seen[#seen + 1] = tostring(v:name()) .. "#" .. v:id() .. "[" .. key_of(v) .. "]" end
				detail[#detail + 1] = name .. ": no living body with expect[" .. exp .. "] among " .. table.concat(seen, " ; ")
			else used[found:id()] = true end
		end
		local n_exp = 0
		for _ in pairs(H.expect) do n_exp = n_exp + 1 end
		if #actors ~= n_exp then all_ok = false; detail[#detail + 1] = "living bodies " .. #actors .. " expected " .. n_exp end
		if all_ok and el > 30000 then
			dump("POSTLOAD" .. H.loads, lo)
			qa.assert("postload" .. H.loads .. " all players restored, no extra body", true, string.format("after %.0f s", el / 1000))
		elseif el > 110000 then
			dump("POSTLOAD" .. H.loads, lo)
			qa.assert("postload" .. H.loads .. " all players restored, no extra body", false, table.concat(detail, " | "))
			all_ok = true
		else
			all_ok = false
		end
		if all_ok then
			if H.loads < 2 then
				H.loads = H.loads + 1; H.pt = now; wstate()
				qa.event("SLOT loadLastSave #" .. H.loads)
				pcall(function() game_sv.loadLastSave(0) end)
			else
				H.stage = 4; H.pt = now; wstate()
				qa.event("SLOT DONE")
			end
		end
	end
end

-- The harness tick dies with the level on a load (the Lua VM is kept on a client), so re-arm a small loop of our own on each actor spawn.
local function rearm()
	local id = time_global()
	_G.slot_arm = id
	local last_ticks = -1
	local last_run = 0
	pcall(function()
		level.add_call(function()
			if _G.slot_arm ~= id then return true end
			local nowms = time_global()
			if nowms - last_run < 1000 then return false end
			last_run = nowms
			if qa.ticks ~= last_ticks then last_ticks = qa.ticks return false end   -- harness is alive and calls the hook itself
			local ok, err = pcall(function()
				qa.hooks.slotrestore(1000, qa.local_object())
			end)
			if not ok then qa.event("slot loop error " .. tostring(err)) end
			return false
		end, function() end)
	end)
	qa.event("SLOT rearm loop " .. tostring(id))
end
if mp_actor_binder and not _G.slot_wrapped then
	_G.slot_wrapped = true
	local orig = mp_actor_binder.net_spawn
	mp_actor_binder.net_spawn = function(self, data)
		local r = orig(self, data)
		pcall(rearm)
		return r
	end
end
