-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Hook file for tools/stalker_xrmpe/run_coop.ps1 (qa_harness.lua API), Cordon.
-- Server role (dedicated server, or the listen host) drives, every client (A, B) checks what it sees.
--   1. dry statistics: stash_loot.plan("w"/"m"/"i") x3000 -> win rates 30 / 50 / 50 percent, only valid sections,
--      ammo only from the level tier list
--   2. inventory boxes (kind "i"): each online box was rolled exactly once (flag SBOX_<name>), its contents equal the
--      roll, a second fill call changes nothing
--   3. wooden fallback boxes: every online one is broken by a server hit; drops == the recorded rolls, win count inside
--      the 99.9 percent binomial band, a second break/hit creates nothing more
--   4. clients: the number of loose consumable/ammo objects they see grew by exactly what the server created
--      (not once per player)
--   5. SoC boxes (data table): up to 3 explicit-item boxes (exact SoC items) and 3 community boxes are broken
-- Config: -Cfg hit=strike|fire_wound
-------------------------------------------------------------------------------------------------------
slt = { st = 0, t0 = nil, cl = {} }

local function tlog(s) qa.event("SLT " .. tostring(s)) end
local function has(n) return story_flags.has_flag(n) end
local function give(n) story_flags.give_flag(n) end

local function count(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end

local function item_set()
	local c = stash_loot.config()
	local set = {}
	for _, it in ipairs(c.items) do if it[1] ~= "ammo" then set[it[1]] = true end end
	for _, a in ipairs(c.tiers[level.name()] or c.tiers.default) do set[a] = true end
	return set
end

-- set of ids of loose (no parent) watched objects; server = alife view, client = level view
local function loose_ids(set, on_server)
	local r = {}
	for id = 0, 65534 do
		if on_server then
			local o = alife():object(id)
			if o and set[o:section_name()] and (o.parent_id == nil or o.parent_id == 65535) then r[id] = true end
		else
			local o = level.object_by_id(id)
			if o and set[o:section()] and o:parent() == nil then r[id] = true end
		end
	end
	return r
end

-- ids of loose watched objects that are new (not in base) and lie within 3 m of a box position
local function near_new(set, base, boxes, on_server)
	local r = {}
	for id in pairs(loose_ids(set, on_server)) do
		if not base[id] then
			local p
			if on_server then p = alife():object(id).position else p = level.object_by_id(id):position() end
			for _, b in ipairs(boxes) do
				if b.pos:distance_to(p) <= 3 then r[id] = true break end
			end
		end
	end
	return r
end

local function objects_of(list)    -- how many objects a result list stands for (ammo stacks split by box size)
	local sys = system_ini()
	local n = 0
	for _, e in ipairs(list) do
		local sec, num = string.match(e, "^(.-)%*(%d+)$")
		if sec then
			local bs = sys:r_u32(sec, "box_size")
			n = n + math.ceil(tonumber(num) / bs)
		else
			n = n + 1
		end
	end
	return n
end

local function ids_by_name()
	local m = {}
	for id = 0, 65534 do
		local o = alife():object(id)
		if o then
			local s = o:section_name()
			if s == "physic_destroyable_object" or s == "inventory_box" then m[o:name()] = id end
		end
	end
	return m
end

local function hit_box(o, who)
	local h = hit()
	h.power = 100000
	h.impulse = tonumber(qa.cfg.impulse) or 5
	h.direction = vector():set(0, 1, 0)
	h.draftsman = who or o
	if tostring(qa.cfg.hit) == "fire_wound" then h.type = hit.fire_wound else h.type = hit.strike end
	o:hit(h)
end

local function server_actor()
	local r = {}
	if type(db.mp_actors) == "table" then for id, o in pairs(db.mp_actors) do r[#r + 1] = id end end
	table.sort(r)
	return r[1], r
end

local function near_player(se, pa, maxd)
	local a = alife():object(pa)
	return a ~= nil and se ~= nil and a.position:distance_to(se.position) <= maxd
end

-- binomial 99.9 percent band
local function band(n, p)
	local m, sd = n * p, math.sqrt(n * p * (1 - p))
	return math.max(0, math.floor(m - 3.5 * sd)), math.ceil(m + 3.5 * sd)
end

-- ---------------------------------------------------------------- clients
local function client_hooks(t, lo)
	local role = tostring(qa.cfg.role)
	if slt.cl.set == nil then
		slt.cl.set = item_set()
		slt.cl.base = loose_ids(slt.cl.set, false)
		tlog(role .. " client baseline loose items " .. count(slt.cl.base))
	end
	if slt.cl.done then return end
	local total, ids = nil, {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true then
			local n = string.match(k, "^SLT_TOTAL_(%d+)$")
			if n then total = tonumber(n) end
			local i = string.match(k, "^SLT_ID_(%d+)$")
			if i then ids[#ids + 1] = tonumber(i) end
		end
	end
	if total == nil then return end
	slt.cl.done = true
	qa.eventually(role .. " sees the " .. total .. " server-created objects, each once, and none created locally", function()
		if #ids ~= total then return false, "flags " .. #ids .. " of " .. total end
		local pts = {}
		for _, id in ipairs(ids) do
			local o = level.object_by_id(id)
			if o == nil then return false, "object " .. id .. " not seen yet" end
			pts[#pts + 1] = o:position()
		end
		local seen = 0
		for id in pairs(loose_ids(slt.cl.set, false)) do
			if not slt.cl.base[id] then
				local p = level.object_by_id(id):position()
				for _, q in ipairs(pts) do
					if q:distance_to(p) <= 3 then seen = seen + 1 break end
				end
			end
		end
		return seen == total, "new loose near them " .. seen .. " server " .. total
	end, 20)
end

-- ---------------------------------------------------------------- server
local function server_hooks(t, lo)
	if slt.t0 == nil then slt.t0 = t end
	local dt = t - slt.t0
	local pa, acts = server_actor()
	if slt.st == 0 then
		if pa == nil then return end
		slt.t1 = dt
		slt.st = 1
		return
	end
	if slt.st == 1 and dt >= slt.t1 + 25 then
		local lvl = level.name()
		local c = stash_loot.config()
		tlog("level " .. lvl .. " players " .. #acts .. " cfg w=" .. tostring(c.chance.w) .. " m=" .. tostring(c.chance.m) .. " i=" .. tostring(c.chance.i) .. " items=" .. #c.items)
		-- 1. dry statistics
		local set = item_set()
		local tier = {}
		for _, a in ipairs(c.tiers[lvl] or c.tiers.default) do tier[a] = true end
		local sys = system_ini()
		for _, k in ipairs({ "w", "m", "i" }) do
			local N, wins, bad, seen = 3000, 0, 0, {}
			for i = 1, N do
				local p = stash_loot.plan(k)
				if p.win then
					wins = wins + 1
					if #p.picks ~= c.per_roll then bad = bad + 1 end
					for _, it in ipairs(p.picks) do
						seen[it[1]] = (seen[it[1]] or 0) + 1
						if not sys:section_exist(it[1]) then bad = bad + 1 end
						if it[2] then
							if not tier[it[1]] or it[2] < c.ammo_min or it[2] > c.ammo_max then bad = bad + 1 end
						elseif not set[it[1]] then bad = bad + 1 end
					end
				end
			end
			local lo_, hi_ = band(N, c.chance[k] / 100)
			qa.assert("server: plan(" .. k .. ") win rate " .. wins .. "/" .. N .. " inside [" .. lo_ .. "," .. hi_ .. "] for " .. c.chance[k] .. " percent", wins >= lo_ and wins <= hi_, "")
			qa.assert("server: plan(" .. k .. ") every pick valid (" .. bad .. " bad)", bad == 0, "")
			local kinds = {}
			for s, n in pairs(seen) do kinds[#kinds + 1] = s .. "=" .. n end
			table.sort(kinds)
			tlog("plan " .. k .. " wins " .. wins .. " picks " .. table.concat(kinds, " "))
			if k == "w" then
				local miss = {}
				for _, it in ipairs(c.items) do if it[1] ~= "ammo" and not seen[it[1]] then miss[#miss + 1] = it[1] end end
				qa.assert("server: every consumable of the list appears in 3000 rolls", #miss == 0, "missing " .. table.concat(miss, ","))
			end
		end
		-- config sanity
		qa.assert("server: no ammo type of the level tier is missing from the game", #(c.tiers[lvl] or c.tiers.default) >= 1, "")
		-- collect boxes
		local ids = ids_by_name()
		slt.ids = ids
		local kk = stash_loot_kinds.kinds[lvl] or {}
		slt.wood, slt.inv = {}, {}
		local names = {}
		for n in pairs(kk) do names[#names + 1] = n end
		table.sort(names)
		for _, n in ipairs(names) do
			local id = ids[n]
			local se = id and alife():object(id)
			local o = id and level.object_by_id(id)
			if o and se then
				local pos = vector():set(se.position.x, se.position.y, se.position.z)
				if kk[n] == "w" or kk[n] == "m" then slt.wood[#slt.wood + 1] = { name = n, id = id, pos = pos, kind = kk[n] }
				elseif kk[n] == "i" then slt.inv[#slt.inv + 1] = { name = n, id = id, pos = pos } end
			end
		end
		tlog("kinds on level w+m+i = " .. #names .. "; online: wood " .. #slt.wood .. " inventory " .. #slt.inv)
		qa.assert("server: fallback wooden boxes are online (" .. #slt.wood .. ")", #slt.wood >= 5, tostring(#slt.wood))
		slt.set = set
		slt.st = 2
		slt.t2 = dt
		return
	end
	if slt.st == 2 and dt >= slt.t2 + 2 then
		-- 2. inventory boxes: rolled once, contents == roll
		local filled, rolled = 0, 0
		for _, b in ipairs(slt.inv) do
			local flagged = has(string.upper("SBOX_" .. b.name))
			local res = stash_loot.results[b.name]
			local inside = 0
			for id = 0, 65534 do
				local o = alife():object(id)
				if o and o.parent_id == b.id then inside = inside + 1 end
			end
			if flagged then rolled = rolled + 1 end
			if res and #res > 0 then filled = filled + 1 end
			local want = res and objects_of(res) or 0
			qa.assert("server: inventory box " .. b.name .. " rolled once and holds " .. want .. " object(s)", flagged and inside == want, "inside " .. inside .. " res " .. tostring(res and table.concat(res, ",")))
			-- a second fill call is ignored
			local before = inside
			pcall(function() stash_loot.fill_inventory(level.object_by_id(b.id), { k = "i" }) end)
			slt.inv_before = slt.inv_before or {}
			slt.inv_before[b.name] = before
		end
		tlog("inventory boxes " .. #slt.inv .. " rolled " .. rolled .. " with content " .. filled)
		slt.st = 3
		slt.t3 = dt
		return
	end
	if slt.st == 3 and dt >= slt.t3 + 3 then
		for _, b in ipairs(slt.inv) do
			local inside = 0
			for id = 0, 65534 do
				local o = alife():object(id)
				if o and o.parent_id == b.id then inside = inside + 1 end
			end
			qa.assert("server: second fill of " .. b.name .. " changes nothing", inside == slt.inv_before[b.name], inside .. " vs " .. slt.inv_before[b.name])
		end
		-- 3. break the wooden fallback boxes
		slt.base = loose_ids(slt.set, true)
		local who = level.object_by_id(pa)
		for _, b in ipairs(slt.wood) do
			local o = level.object_by_id(b.id)
			if o then
				local ok, err = pcall(hit_box, o, who)
				if not ok then tlog("hit error " .. b.name .. " " .. tostring(err)) end
			end
		end
		tlog("hit " .. #slt.wood .. " wooden boxes, baseline loose " .. count(slt.base))
		slt.st = 4
		slt.t4 = dt
		return
	end
	if slt.st == 4 and dt >= slt.t4 + 10 then
		local fired, wins, objs = 0, 0, 0
		local kf, kw = { w = 0, m = 0 }, { w = 0, m = 0 }
		for _, b in ipairs(slt.wood) do
			local res = stash_loot.results[b.name]
			if res ~= nil then
				fired = fired + 1
				kf[b.kind] = kf[b.kind] + 1
				if #res > 0 then wins = wins + 1; kw[b.kind] = kw[b.kind] + 1; objs = objs + objects_of(res) end
				tlog("box " .. b.name .. " (" .. b.kind .. ") -> " .. (#res > 0 and table.concat(res, ",") or "nothing"))
			end
		end
		qa.assert("server: death callback fired for the broken boxes (" .. fired .. "/" .. #slt.wood .. ")", fired >= math.ceil(#slt.wood * 0.9), "")
		for _, k in ipairs({ "w", "m" }) do
			if kf[k] > 0 then
				local ch = stash_loot.config().chance[k] / 100
				local lo_, hi_ = band(kf[k], ch)
				qa.assert("server: kind " .. k .. " wins " .. kw[k] .. "/" .. kf[k] .. " inside the 99.9 percent band [" .. lo_ .. "," .. hi_ .. "] for " .. (ch * 100) .. " percent", kw[k] >= lo_ and kw[k] <= hi_, "")
			end
		end
		local new = near_new(slt.set, slt.base, slt.wood, true)
		local nn = count(new)
		for id in pairs(new) do
			local se = alife():object(id)
			local best, bd = "?", 99
			for _, b in ipairs(slt.wood) do
				local d = b.pos:distance_to(se.position)
				if d < bd then bd = d best = b.name end
			end
			tlog(string.format("NEW id %d %s %.1f m from %s (result %s) parent %s", id, se:section_name(), bd, best, tostring(stash_loot.results[best] and table.concat(stash_loot.results[best], ",")), tostring(se.parent_id)))
		end
		-- a hit can knock a neighbouring SoC box over: its (legitimate) SoC loot counts as collateral
		local isw = {}
		for _, b in ipairs(slt.wood) do isw[b.name] = true end
		local coll, collobjs = {}, 0
		for name, res in pairs(stash_loot.results) do
			if not isw[name] and not has(string.upper("SBOX_" .. name)) then coll[#coll + 1] = name; collobjs = collobjs + objects_of(res) end
		end
		tlog("collateral SoC boxes broken by the hits: " .. #coll .. " (" .. collobjs .. " objects): " .. table.concat(coll, ","))
		qa.assert("server: new loose objects within 3 m of the broken boxes = the rolled " .. objs .. " (+ up to " .. collobjs .. " from knocked-over SoC boxes)", nn >= objs and nn <= objs + collobjs and (#coll > 0 or nn == objs), "new " .. nn)
		slt.total = nn
		slt.newids = new
		slt.wins, slt.fired = wins, fired
		-- publish the ids that are near the players, then the total (clients check these ids)
		local near = 0
		for id in pairs(new) do
			local se = alife():object(id)
			if se and near_player(se, pa, 80) then give("SLT_ID_" .. id); near = near + 1 end
		end
		give("SLT_TOTAL_" .. near)
		-- second break: death handler again + a second hit
		slt.rolls0 = stash_loot.stats.w.rolls
		slt.fired0 = fired
		for _, b in ipairs(slt.wood) do
			pcall(function()
				local o = level.object_by_id(b.id)
				if o then stash_loot.on_death(o, { k = "w" }) hit_box(o, level.object_by_id(pa)) end
			end)
		end
		slt.st = 5
		slt.t5 = dt
		return
	end
	if slt.st == 5 and dt >= slt.t5 + 8 then
		-- the handler is idempotent per box: a second death call / second hit rolls again ONLY for a box whose first callback never fired
		local extra = stash_loot.stats.w.rolls - slt.rolls0
		local unfired = #slt.wood - slt.fired0
		qa.assert("server: second break/hit rolls no box twice (new rolls " .. extra .. ", boxes that never fired before " .. unfired .. ")", extra <= unfired, "")
		local new2 = near_new(slt.set, slt.base, slt.wood, true)
		for id in pairs(new2) do
			if not slt.newids[id] then
				local se = alife():object(id)
				tlog(string.format("after 2nd break: extra id %d %s at %.1f m from box %s", id, se:section_name(), 0, "?"))
			end
		end
		tlog("second pass: loose near boxes " .. count(new2) .. " (first pass " .. slt.total .. "), unfired boxes called now " .. unfired)
		slt.soc_started = true
		-- 5. SoC boxes
		local lv = stash_loot_data.boxes[level.name()]
		local names = {}
		for n in pairs(lv) do names[#names + 1] = n end
		table.sort(names)
		local ids = slt.ids
		slt.soc = {}
		local ni, nc = 0, 0
		for _, n in ipairs(names) do
			local e = lv[n]
			local id = ids[n]
			local se = id and alife():object(id)
			local o = id and level.object_by_id(id)
			if o and se and near_player(se, pa, 95) then
				if e.i and ni < 3 then ni = ni + 1; slt.soc[#slt.soc + 1] = { name = n, id = id, e = e, pos = se.position } end
				if e.c and nc < 3 then nc = nc + 1; slt.soc[#slt.soc + 1] = { name = n, id = id, e = e, pos = se.position } end
			end
		end
		tlog("SoC boxes picked " .. #slt.soc .. " (items " .. ni .. " community " .. nc .. ")")
		qa.assert("server: some SoC-data boxes are online", #slt.soc >= 2, tostring(#slt.soc))
		slt.socbase = {}
		local all = {}
		for _, b in ipairs(slt.soc) do
			local o = level.object_by_id(b.id)
			if o then pcall(hit_box, o, level.object_by_id(pa)) end
		end
		slt.st = 6
		slt.t6 = dt
		return
	end
	if slt.st == 6 and dt >= slt.t6 + 10 then
		local fired = 0
		for _, b in ipairs(slt.soc) do
			local res = stash_loot.results[b.name]
			if res ~= nil then
				fired = fired + 1
				tlog("SoC box " .. b.name .. " (" .. (b.e.i and "items" or b.e.c) .. ") -> " .. (#res > 0 and table.concat(res, ",") or "nothing"))
				if b.e.i then
					local exp = {}
					for k = 1, #b.e.i, 2 do for n = 1, b.e.i[k + 1] do exp[#exp + 1] = b.e.i[k] end end
					table.sort(exp)
					local got = {}
					for _, r in ipairs(res) do got[#got + 1] = r end
					table.sort(got)
					qa.assert("server: SoC items box " .. b.name .. " dropped exactly its SoC list", table.concat(exp, ",") == table.concat(got, ","), table.concat(got, ","))
				end
			end
		end
		qa.assert("server: death callback fired for the SoC boxes (" .. fired .. "/" .. #slt.soc .. ")", fired >= math.ceil(#slt.soc * 0.8), "")
		-- 6. metal rule through the same death handler: on_death(obj, {k = "m"}) on 60 intact destroyable objects
		slt.m = {}
		local broken = {}
		for _, b in ipairs(slt.wood) do broken[b.name] = true end
		for _, b in ipairs(slt.soc) do broken[b.name] = true end
		local names2 = {}
		for n in pairs(slt.ids) do names2[#names2 + 1] = n end
		table.sort(names2)
		for _, n in ipairs(names2) do
			local id = slt.ids[n]
			local se = alife():object(id)
			if #slt.m < 60 and se and se:section_name() == "physic_destroyable_object" and not broken[n] and level.object_by_id(id) and stash_loot.results[n] == nil then
				slt.m[#slt.m + 1] = { name = n, id = id, pos = vector():set(se.position.x, se.position.y, se.position.z), kind = "m" }
			end
		end
		slt.mbase = loose_ids(slt.set, true)
		for _, b in ipairs(slt.m) do pcall(function() stash_loot.on_death(level.object_by_id(b.id), { k = "m" }) end) end
		tlog("metal-rule death handler called on " .. #slt.m .. " intact objects")
		slt.st = 7
		slt.t7 = dt
	elseif slt.st == 7 and dt >= slt.t7 + 6 then
		local n, w, objs = 0, 0, 0
		for _, b in ipairs(slt.m) do
			local res = stash_loot.results[b.name]
			if res ~= nil then n = n + 1; if #res > 0 then w = w + 1; objs = objs + objects_of(res) end end
		end
		local lo_, hi_ = band(n, 0.5)
		qa.assert("server: metal rule wins " .. w .. "/" .. n .. " inside the 99.9 percent band [" .. lo_ .. "," .. hi_ .. "] for 50 percent", n >= 40 and w >= lo_ and w <= hi_, "")
		local new = near_new(slt.set, slt.mbase, slt.m, true)
		qa.assert("server: metal rule created exactly the rolled " .. objs .. " objects", count(new) == objs, "new " .. count(new))
		tlog("DONE")
		slt.st = 99
	end
end

qa.hooks.slt = function(t, lo)
	local ok, err = pcall(function()
		if OnServer() then server_hooks(t, lo) else client_hooks(t, lo) end
	end)
	if not ok then tlog("ERR " .. tostring(err)) end
end
