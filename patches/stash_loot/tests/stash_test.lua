-------------------------------------------------------------------------------------------------------
-- TEST ONLY: appended to xr_conditions.dscript of a test build (after Clear COOP's bot_start.lua), never shipped.
-- For up to 2 explicit-items boxes and 2 community boxes of the current level: hit the box on the server,
-- scan server objects near it before/after, assert the loot appeared once and that a second break call
-- (and a second hit) creates nothing more.
-------------------------------------------------------------------------------------------------------
st_test = { picks = nil, i = 0, phase = 0, t = 0, done = false }

local function slog(s) cs_bot.log("STASHTEST " .. s) end

local function scan(pos)
	local r = {}
	for id = 0, 65534 do
		local o = alife():object(id)
		if o then
			local q = o.position
			local dx, dy, dz = q.x - pos.x, q.y - pos.y, q.z - pos.z
			if dx * dx + dy * dy + dz * dz < 1.69 then r[id] = o:section_name() end
		end
	end
	return r
end

local function sorted_keys_sections(t)
	local l = {}
	for id, s in pairs(t) do table.insert(l, s) end
	table.sort(l)
	return l
end

local function newer(a, b)   -- ids in b not in a
	local r = {}
	for id, s in pairs(b) do if a[id] == nil then r[id] = s end end
	return r
end

local name_ids = nil
local function find(name)
	if name_ids == nil then
		name_ids = {}
		for id = 0, 65534 do
			local o = alife():object(id)
			if o and o:section_name() == "physic_destroyable_object" then name_ids[o:name()] = id end
		end
	end
	local id = name_ids[name]
	if id == nil then return nil end
	return level.object_by_id(id)
end

local function count(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end

local function pick()
	local lv = stash_loot_data.boxes[level.name()]
	local ni, nc, out = 0, 0, {}
	local names = {}
	for n in pairs(lv) do table.insert(names, n) end
	table.sort(names)
	for _, n in ipairs(names) do
		local e = lv[n]
		local o = find(n)
		if o then
			if e.i and ni < 2 then ni = ni + 1 table.insert(out, { name = n, e = e }) end
			if e.c and nc < 3 then nc = nc + 1 table.insert(out, { name = n, e = e }) end
		end
	end
	return out
end

local function hit_box(o)
	local h = hit()
	h.power = 100000
	h.impulse = 1000
	h.direction = vector():set(0, 1, 0)
	h.draftsman = o
	h.type = hit.strike
	o:hit(h)
end

local function check(name, ok, d) slog((ok and "PASS " or "FAIL ") .. name .. "  " .. tostring(d or "")) end

cs_bot.hooks.stash = function(t, lo)
	if st_test.done then return end
	if st_test.picks == nil then
		if t < 5 then return end
		st_test.picks = pick()
		slog(string.format("level %s picked %d boxes, data boxes=%d", level.name(), #st_test.picks, (function() local n=0 for _ in pairs(stash_loot_data.boxes[level.name()]) do n=n+1 end return n end)()))
		st_test.i = 1
		st_test.phase = 0
		st_test.t = t
	end
	local p = st_test.picks[st_test.i]
	if p == nil then
		st_test.done = true
		slog("DONE")
		return
	end
	local o = find(p.name)
	if st_test.phase == 0 then
		if not o then slog("box missing " .. p.name) st_test.i = st_test.i + 1 return end
		p.pos = vector():set(o:position().x, o:position().y, o:position().z)
		p.before = scan(p.pos)
		p.bound = (stash_loot.results[p.name] == nil)
		p.obj = o
		slog(string.format("break %s kind=%s pos=%.1f,%.1f,%.1f baseline=%d", p.name, p.e.i and "items" or "community", p.pos.x, p.pos.y, p.pos.z, count(p.before)))
		hit_box(o)
		st_test.phase = 1
		st_test.t = t
	elseif st_test.phase == 1 and t - st_test.t >= 3 then
		local res = stash_loot.results[p.name]
		check(p.name .. " handler fired (death callback)", res ~= nil, res and table.concat(res, ",") or "no result")
		p.after = scan(p.pos)
		local new = newer(p.before, p.after)
		local secs = sorted_keys_sections(new)
		slog(string.format("new objects near box: %d: %s", #secs, table.concat(secs, ",")))
		if res then
			if p.e.i then
				local exp = {}
				for k = 1, #p.e.i, 2 do for n = 1, p.e.i[k + 1] do table.insert(exp, p.e.i[k]) end end
				table.sort(exp)
				check(p.name .. " exact SoC items appeared", table.concat(exp, ",") == table.concat(secs, ","), table.concat(exp, ","))
			else
				local ok = #secs >= #res
				local allowed = {}
				for _, r in ipairs(res) do allowed[string.gsub(r, "%*%d+$", "")] = true end
				for _, s in ipairs(secs) do if not allowed[s] then ok = false end end
				check(p.name .. " rolled items appeared (" .. #res .. " rolled)", ok, table.concat(res, ","))
			end
		end
		p.n1 = count(new)
		-- second break call and second hit
		local ok, err = pcall(function() stash_loot.on_death(p.obj, p.e) end)
		slog("second on_death call: " .. tostring(ok) .. " " .. tostring(err))
		local o2 = find(p.name)
		slog("box still present after break: " .. tostring(o2 and true or false))
		if o2 then pcall(hit_box, o2) end
		st_test.phase = 2
		st_test.t = t
	elseif st_test.phase == 2 and t - st_test.t >= 3 then
		local after2 = scan(p.pos)
		local new2 = newer(p.before, after2)
		check(p.name .. " no duplicate on second break/hit", count(new2) == p.n1, count(new2) .. " vs " .. p.n1)
		st_test.i = st_test.i + 1
		st_test.phase = 0
	end
end
slog("loaded")
