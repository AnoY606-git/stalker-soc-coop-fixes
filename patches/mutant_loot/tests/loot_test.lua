--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Hook file for run_coop.ps1 -Mode listen -Clients 1 (one listen host = one player), qa_lib loaded.
--   powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner <name> `
--     -Mode listen -Clients 1 -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 120 -CompareTimeout 10 -ResultDir <dir>
--   (-Cfg mode=default runs the real SoC chance 0.2 instead of the forced chance 1.0)
-- The merged gamedata must hold mutant_loot + darkvalley_restore (bind_monster.script with the mutant_loot hooks) + soc_economy.
--
-- What it does (forced mode): the host spawns a dog, a boar and a flesh next to the player and kills them with hits credited to the
-- player. Then for each corpse it performs the take action a real player does: the USE path = mutant_loot.use_cb(binder, corpse,
-- actor), the exact function the engine calls through the corpse's use callback with who = the player's actor (a bot cannot press
-- the Use key). It checks that
--   * the death roll was made with the forced chance and the corpse carries the part (flag), the server binder armed the callback,
--   * the part reaches the player's inventory (online object walk AND server scan: exactly one),
--   * the corpse no longer offers it (flag off), a second use gives nothing more,
--   * the "Found: ..." tip and later the "Nothing useful ..." tip were shown to this player.
-- Default mode: 6 corpses at the real chance: every roll used 0.2 and the corpse flags match the rolls; every winner is taken the same way.
-- The window of the old version is gone, so nothing needs a click.
-------------------------------------------------------------------------------------------------------
mlt = { st = 0, t0 = nil, list = {}, done = {} }

local function tlog(s) qa.event('MLOOT ' .. tostring(s)) end
local function is_default() return tostring(qa.cfg.mode) == "default" end

local function count_parts(section)   -- server: { owner_id = n } over all server entities
	local r = {}
	for id = 0, 65534 do
		local o = alife():object(id)
		if o and o:section_name() == section then
			local p = o.parent_id
			if p ~= nil and p ~= 65535 then r[p] = (r[p] or 0) + 1 end
		end
	end
	return r
end

local function total(t) local n = 0 for _, v in pairs(t) do n = n + v end return n end

local function local_count(lo, section)
	local n = 0
	pcall(function() lo:iterate_inventory(function(own, it) if it:section() == section then n = n + 1 end end, lo) end)
	return n
end

local function spawn_near(sec, pa, k)
	local se_a = alife():object(pa)
	local p = se_a.position
	local pos = vector():set(p.x + 2.0 + (k or 0) * 0.4, p.y, p.z + (k or 0) * 0.3)
	local se = alife():create(sec, pos, se_a.m_level_vertex_id, se_a.m_game_vertex_id)
	return se.id
end

local function kill_with_hit(cid, pa)
	local o = level.object_by_id(cid)
	local a = level.object_by_id(pa)
	if o == nil then return false end
	if not o:alive() then return true end
	local h = hit()
	h.draftsman = a or o
	h.type = hit.fire_wound
	h.power = 100000
	h.impulse = 10
	h.direction = vector():set(0, 0, 1)
	h:bone("bip01_spine")
	o:hit(h)
	return true
end

local function has_tip(prefix, from)
	local tips = mutant_loot.test.tips
	for i = (from or 1), #tips do
		if string.sub(tips[i], 1, string.len(prefix)) == prefix then return true end
	end
	return false
end

-- the take action of a real player: the engine's use callback
local function press_use(cid, pa)
	local corpse = level.object_by_id(cid)
	local actor = level.object_by_id(pa)
	if corpse == nil or actor == nil then return false, "objects missing" end
	local n0 = #mutant_loot.test.uses
	mutant_loot.use_cb(nil, corpse, actor)
	return #mutant_loot.test.uses == n0 + 1
end

local function run(t, lo)
	if mlt.t0 == nil then mlt.t0 = t end
	local dt = t - mlt.t0
	local dflt = is_default()
	local pa = LocalActor()
	if mlt.st == 0 then
		if dt < 12 or db.mp_actors == nil or db.mp_actors[pa] == nil then return end
		qa_lib.god(true)
		mlt.pa = pa
		if dflt then
			mlt.list = {}
			for i = 0, 2 do
				mlt.list[#mlt.list + 1] = { tag = "DOG" .. i, sec = "dog_normal", part = "mutant_dog_part", k = i }
				mlt.list[#mlt.list + 1] = { tag = "FLESH" .. i, sec = "flesh_normal", part = "mutant_flesh_part", k = i + 3 }
			end
		else
			mutant_loot.test.chance = 1.0
			mlt.list = {
				{ tag = "DOG", sec = "dog_normal", part = "mutant_dog_part", k = 0 },
				{ tag = "BOAR", sec = "boar_normal", part = "mutant_boar_part", k = 2 },
				{ tag = "FLESH", sec = "flesh_normal", part = "mutant_flesh_part", k = 4 },
			}
		end
		for _, e in ipairs(mlt.list) do e.id = spawn_near(e.sec, pa, e.k) end
		tlog("spawned " .. #mlt.list .. " mutants near player " .. pa)
		mlt.st = 1
		mlt.t1 = dt
	elseif mlt.st == 1 and dt >= mlt.t1 + 1 then
		local online = 0
		for _, e in ipairs(mlt.list) do if level.object_by_id(e.id) ~= nil then online = online + 1 end end
		if online == #mlt.list or dt > mlt.t1 + 40 then
			qa.assert("mutants online before the kill", online == #mlt.list, online .. "/" .. #mlt.list)
			for _, e in ipairs(mlt.list) do kill_with_hit(e.id, pa) end
			mlt.st = 2
			mlt.t2 = dt
		end
	elseif mlt.st == 2 then
		local rolled, armed = 0, 0
		for _, e in ipairs(mlt.list) do
			if mutant_loot.test.rolls[e.id] then rolled = rolled + 1 end
			if mutant_loot.test.armed[e.id] then armed = armed + 1 end
		end
		if rolled == #mlt.list and (armed == #mlt.list or dt > mlt.t2 + 15 or dflt) then
			local wins = 0
			for _, e in ipairs(mlt.list) do
				local r = mutant_loot.test.rolls[e.id]
				e.win = r.win
				if r.win then wins = wins + 1 end
				tlog(string.format("roll %s id=%d part=%s chance=%.2f r=%.3f win=%s", e.tag, e.id, r.part, r.chance, r.r, tostring(r.win)))
				qa.assert("roll part of " .. e.tag .. " is " .. e.part, r.part == e.part, tostring(r.part))
				if dflt then
					qa.assert("default chance for " .. e.tag .. " is the SoC 0.2", math.abs(r.chance - 0.2) < 0.0001, tostring(r.chance))
					qa.assert("corpse flag of " .. e.tag .. " matches the roll", (#mutant_loot.parts_on(e.id) == 1) == r.win, tostring(#mutant_loot.parts_on(e.id)))
				else
					qa.assert(e.tag .. " rolled with the forced chance 1.0 and carries the part", r.win == true and #mutant_loot.parts_on(e.id) == 1, "r=" .. r.r)
					qa.assert("use callback + Search tip armed on the " .. e.tag .. " corpse", mutant_loot.test.armed[e.id] == true, tostring(mutant_loot.test.arm_err[e.id]))
				end
			end
			tlog("wins " .. wins .. "/" .. #mlt.list)
			mlt.queue = {}
			for _, e in ipairs(mlt.list) do if e.win then mlt.queue[#mlt.queue + 1] = e end end
			mlt.st = 3
			mlt.t3 = dt
		elseif dt > mlt.t2 + 40 then
			qa.assert("all mutants died and were rolled", false, "rolled " .. rolled .. "/" .. #mlt.list)
			mlt.st = 99
		end
	elseif mlt.st == 3 and dt >= mlt.t3 + 1 then
		-- take the next corpse (the USE path), one at a time
		local e = mlt.queue[1]
		if e == nil then mlt.st = 5; mlt.t5 = dt; return end
		mlt.cur = e
		mlt.n0 = local_count(lo, e.part)
		mlt.srv0 = count_parts(e.part)[pa] or 0
		mlt.tips0 = #mutant_loot.test.tips
		local ok, why = press_use(e.id, pa)
		qa.assert("use path reached use_cb on the server for " .. e.tag, ok == true, tostring(why))
		mlt.st = 4
		mlt.t4 = dt
	elseif mlt.st == 4 and dt >= mlt.t4 + 3 then
		local e = mlt.cur
		local now_n = local_count(lo, e.part)
		local srv = count_parts(e.part)
		qa.assert("part of " .. e.tag .. " reached the player's inventory (online walk)", now_n == mlt.n0 + 1, mlt.n0 .. " -> " .. now_n)
		qa.assert("exactly one " .. e.part .. " more on the server for the player", (srv[pa] or 0) == mlt.srv0 + 1, tostring(srv[pa]))
		qa.assert(e.tag .. " corpse no longer offers the part", #mutant_loot.parts_on(e.id) == 0, "")
		qa.assert("tip 'Found:' shown to the player for " .. e.tag, has_tip("Found", mlt.tips0 + 1) or has_tip(game.translate_string("st_mutant_loot_found"), mlt.tips0 + 1), table.concat(mutant_loot.test.tips, " | "))
		mlt.tips1 = #mutant_loot.test.tips
		-- second press after the repeat window: nothing more, "Nothing useful" tip
		mlt.t4b = dt
		mlt.st = 41
	elseif mlt.st == 41 and dt >= mlt.t4b + 4 then
		local e = mlt.cur
		local ok = press_use(e.id, mlt.pa)
		qa.assert("second use on " .. e.tag .. " reached use_cb", ok == true, "")
		mlt.st = 42
		mlt.t4c = dt
	elseif mlt.st == 42 and dt >= mlt.t4c + 3 then
		local e = mlt.cur
		local srv = count_parts(e.part)
		qa.assert("second use on " .. e.tag .. " gave no second part", (srv[mlt.pa] or 0) == mlt.srv0 + 1, tostring(srv[mlt.pa]))
		qa.assert("tip 'Nothing useful' shown after the second use on " .. e.tag, has_tip(game.translate_string("st_mutant_loot_empty"), mlt.tips1 + 1), table.concat(mutant_loot.test.tips, " | "))
		table.remove(mlt.queue, 1)
		mlt.st = 3
		mlt.t3 = dt
	elseif mlt.st == 5 and dt >= mlt.t5 + 1 then
		local takes = {}
		for _, tk in ipairs(mutant_loot.test.takes) do takes[#takes + 1] = string.format("%d:%s:%d", tk.corpse, tk.why, tk.n) end
		tlog("takes " .. table.concat(takes, " "))
		qa.assert("no take was refused as too far", (function() for _, tk in ipairs(mutant_loot.test.takes) do if tk.why == "far" then return false end end return true end)(), table.concat(takes, " "))
		qa.assert("mutant_loot test finished", true, "")
		mlt.st = 99
	end
end

qa.hooks.mloot = function(t, lo)
	local ok, err = pcall(function()
		if OnServer() and LocalActor() ~= nil then run(t, lo) end
	end)
	if not ok then tlog("ERR " .. tostring(err)) end
end
