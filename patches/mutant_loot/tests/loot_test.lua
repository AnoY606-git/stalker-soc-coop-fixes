-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Hook file for tools/stalker_xrmpe/run_coop.ps1 -Mode dedicated -Clients 2 (qa_harness.lua API).
-- Roles: the dedicated server (OnServer, no player) drives the scenario; the two clients (first / second actor id = P1 / P2)
-- act on server flags. Default (forced) mode, chance forced to 1.0:
--   server spawns a dog and a flesh next to P1 and kills both with a hit whose draftsman is P1's actor,
--   both clients see the right part on the corpse and the tip / use callback armed,
--   P1 takes the DOG part (it lands in P1's inventory), then P2 tries the same corpse and gets nothing (no duplicate),
--   then P1 and P2 request the FLESH part in the same tick: exactly one part exists.
-- Run with -Cfg mode=default for the real chances (0.2): spawns 5 dogs + 5 fleshes, kills them, checks that the clients'
-- view of every corpse matches the server's roll (no crash, no mismatch).
-------------------------------------------------------------------------------------------------------
mlt = { st = 0, t0 = nil, ids = {}, done = {} }

local function tlog(s) qa.event('MLOOT ' .. tostring(s)) end

local function has(n) return story_flags.has_flag(n) end
local function give(n) story_flags.give_flag(n) end
local function is_default() return tostring(qa.cfg.mode) == "default" end

local function flag_ids(pat)   -- { [tag] = id } for flags like PREFIX_<TAG>_<id>
	local r = {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true then
			local tag, id = string.match(k, pat)
			if tag then r[tag] = tonumber(id) end
		end
	end
	return r
end

local function server_actors()    -- sorted ids of the player actors on the server
	local r = {}
	if type(db.mp_actors) == "table" then for id, o in pairs(db.mp_actors) do r[#r + 1] = id end end
	table.sort(r)
	return r
end

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

local function ok_str(t) local l = {} for k, v in pairs(t) do l[#l + 1] = tostring(k) .. "=" .. tostring(v) end table.sort(l) return table.concat(l, ",") end
local function total(t) local n = 0 for _, v in pairs(t) do n = n + v end return n end

local function local_count(section)
	local lo = qa.local_object()
	local n = 0
	pcall(function() lo:iterate_inventory(function(own, it) if it:section() == section then n = n + 1 end end, lo) end)
	return n
end

local function spawn_near(sec, pa, k)
	local se_a = alife():object(pa)
	local p = se_a.position
	local pos = vector():set(p.x + 1.0 + (k or 0) * 0.3, p.y, p.z + (k or 0) * 0.2)   -- the actor's own vertex: the level lookup on the server returned far vertices
	local se = alife():create(sec, pos, se_a.m_level_vertex_id, se_a.m_game_vertex_id)
	return se.id
end

local function kill_with_hit(cid, pa)
	local o = level.object_by_id(cid)
	local a = level.object_by_id(pa)
	if o == nil or not o:alive() then return o ~= nil end
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

-- ---------------------------------------------------------------- both clients
local function client_hooks(t, lo)
	local me = LocalActor()
	local role = tostring(qa.cfg.role)
	local who = nil
	for k, v in pairs(story_flags.story_flags) do
		if v == true then
			local n = string.match(k, "^MLT_P(%d)_" .. tostring(me) .. "$")
			if n then who = "P" .. n end
		end
	end
	if who == nil then return end
	mlt.who = who
	local cids = flag_ids("^MLT_C_(%u+)_(%d+)$")

	if is_default() then
		if not mlt.done.dflt and has("MLT_DEFAULT_READY") then
			mlt.done.dflt = true
			qa.eventually(role .. " default-chance: all 10 corpses match the server's rolls", function()
				local bad = {}
				local cids = flag_ids("^MLT_C_(%u+%d)_(%d+)$")
				local n = 0
				for tag, id in pairs(cids) do n = n + 1 end
				if n < 10 then return false, "corpses " .. n end
				local wins = 0
				for k, v in pairs(story_flags.story_flags) do
					if v == true then
						local id = string.match(k, "^MLT_W_(%d+)$")
						if id then wins = wins + 1 end
					end
				end
				for tag, id in pairs(cids) do
					local want = has("MLT_W_" .. id)
					local got = #mutant_loot.parts_on(id) == 1
					if want ~= got then bad[#bad + 1] = tag end
					if want and mutant_loot.test.armed[id] ~= true then bad[#bad + 1] = tag .. "(not armed)" end
				end
				return #bad == 0, "corpses=" .. n .. " wins=" .. wins .. " bad=" .. table.concat(bad, ",")
			end, 40)
		end
		return
	end

	if not mlt.done.shared and cids.DOG and cids.FLESH and has("MLT_ROLLED") then
		mlt.done.shared = true
		for _, tag in ipairs({ "DOG", "FLESH" }) do
			local id = cids[tag]
			local part = (tag == "DOG") and "mutant_dog_part" or "mutant_flesh_part"
			qa.eventually(role .. "/" .. who .. " flags show " .. part .. " on the " .. tag .. " corpse", function()
				local p = mutant_loot.parts_on(id)
				return #p == 1 and p[1] == part, table.concat(p, ",")
			end, 40)
			qa.eventually(role .. "/" .. who .. " Search tip + use callback armed on the " .. tag .. " corpse", function()
				return mutant_loot.test.armed[id] == true, tostring(mutant_loot.test.arm_err[id])
			end, 40)
		end
		-- the Search window opens on the corpse (client side UI code path), then is closed again
		qa.eventually(role .. "/" .. who .. " Search window opens on the DOG corpse", function()
			local ok, err = pcall(function() ui_mutant_loot.open(cids.DOG) end)
			local cur = ui_mutant_loot.current() ~= nil
			pcall(function() ui_mutant_loot.close() end)
			return ok and cur, tostring(err)
		end, 10)
	end

	-- P1 takes the dog part (the function the Take button calls)
	if who == "P1" and has("MLT_GO_P1") and not mlt.done.p1 then
		mlt.done.p1 = true
		tlog("P1 request_take DOG " .. tostring(cids.DOG))
		mutant_loot.request_take(cids.DOG)
		qa.eventually("P1 inventory (client view) holds the dog part", function()
			return local_count("mutant_dog_part") == 1, "count " .. local_count("mutant_dog_part")
		end, 40)
	end
	-- P2 tries the same corpse afterwards
	if who == "P2" and has("MLT_GO_P2") and not mlt.done.p2 then
		mlt.done.p2 = true
		tlog("P2 request_take DOG " .. tostring(cids.DOG))
		mutant_loot.request_take(cids.DOG)
		qa.eventually("P2 inventory (client view) has no dog part", function()
			return has("MLT_P2_DONE") and local_count("mutant_dog_part") == 0, "count " .. local_count("mutant_dog_part")
		end, 40)
	end
	-- after P1 took it both clients agree: the corpse is empty, the tip is still armed (state consistent), window opens empty
	if has("MLT_GO_P2") and not mlt.done.empty then
		mlt.done.empty = true
		qa.eventually(role .. "/" .. who .. " DOG corpse empty on this client, tip still armed, empty window opens", function()
			local empty = #mutant_loot.parts_on(cids.DOG) == 0 and mutant_loot.test.armed[cids.DOG] == true
			if not empty then return false, "parts " .. #mutant_loot.parts_on(cids.DOG) end
			local ok = pcall(function() ui_mutant_loot.open(cids.DOG) end)
			pcall(function() ui_mutant_loot.close() end)
			return ok, "window"
		end, 40)
	end
	-- race on the FLESH corpse: both request in the same tick
	if has("MLT_GO_RACE") and not mlt.done.race then
		mlt.done.race = true
		tlog(who .. " race request_take FLESH " .. tostring(cids.FLESH))
		mutant_loot.request_take(cids.FLESH)
		pcall(function() ui_mutant_loot.open(cids.FLESH) end)    -- window with the part icon on screen for the engine screenshot
		pcall(function() get_console():execute("screenshot") end)
		mlt.close_t = t + 3
	end
	if mlt.close_t and t >= mlt.close_t then
		mlt.close_t = nil
		pcall(function() ui_mutant_loot.close() end)
	end
end

-- ---------------------------------------------------------------- server
local function server_hooks(t, lo)
	if mlt.t0 == nil then mlt.t0 = t end
	local dt = t - mlt.t0
	local dflt = is_default()
	if mlt.st == 0 then
		if dt < 5 then return end
		local acts = server_actors()
		if #acts < 2 then return end
		mlt.acts = acts
		mlt.t1 = dt
		mlt.st = 1
		return
	elseif mlt.st == 1 and dt >= mlt.t1 + 12 then       -- both players have settled in the level
		local acts = server_actors()
		local pa, pb = acts[1], acts[2]
		give("MLT_P1_" .. pa); give("MLT_P2_" .. pb)
		local a, b = alife():object(pa), alife():object(pb)
		tlog(string.format("P1=%d P2=%d distance %.1f", pa, pb, a.position:distance_to(b.position)))
		if dflt then
			mlt.list = {}
			for i = 0, 4 do
				mlt.list[#mlt.list + 1] = { tag = "DOG" .. i, id = spawn_near("dog_normal", pa, i) }
				mlt.list[#mlt.list + 1] = { tag = "FLESH" .. i, id = spawn_near("flesh_normal", pa, i + 5) }
			end
		else
			mutant_loot.test.chance = 1.0
			mlt.list = { { tag = "DOG", id = spawn_near("dog_normal", pa, 0) }, { tag = "FLESH", id = spawn_near("flesh_normal", pa, 3) } }
		end
		mlt.pa, mlt.pb = pa, pb
		for _, e in ipairs(mlt.list) do give("MLT_C_" .. e.tag .. "_" .. e.id) end
		tlog("spawned " .. #mlt.list .. " mutants")
		mlt.st = 2
		mlt.t2 = dt
	elseif mlt.st == 2 and dt >= mlt.t2 + 1 then
		local online = 0
		for _, e in ipairs(mlt.list) do
			if level.object_by_id(e.id) ~= nil then online = online + 1 end
		end
		if online == #mlt.list or dt > mlt.t2 + 40 then
			qa.assert("server: mutants online before the kill", online == #mlt.list, online .. "/" .. #mlt.list)
			for _, e in ipairs(mlt.list) do kill_with_hit(e.id, mlt.pa) end
			mlt.st = 3
			mlt.t3 = dt
		end
	elseif mlt.st == 3 then
		local rolled = 0
		for _, e in ipairs(mlt.list) do if mutant_loot.test.rolls[e.id] then rolled = rolled + 1 end end
		if rolled == #mlt.list then
			local wins = 0
			for _, e in ipairs(mlt.list) do
				local r = mutant_loot.test.rolls[e.id]
				tlog(string.format("roll %s id=%d part=%s chance=%.2f r=%.3f win=%s who=%s", e.tag, e.id, r.part, r.chance, r.r, tostring(r.win), tostring(r.who)))
				if r.win then wins = wins + 1; give("MLT_W_" .. e.id) end
				if dflt then
					qa.assert("server: default chance for " .. e.tag .. " is the SoC 0.2", math.abs(r.chance - 0.2) < 0.0001, tostring(r.chance))
				else
					qa.assert("server: " .. e.tag .. " rolled with forced chance 1.0 and carries " .. r.part, r.win == true, "r=" .. r.r)
				end
				local pn = nil
				pcall(function() pn = level.object_by_id(mlt.pa):name() end)
				if e.tag == "DOG" then   -- the flesh may be killed by a roaming NPC before the hit lands: only the dog is asserted
					qa.assert("server: death of " .. e.tag .. " credited to player P1 (" .. tostring(pn) .. ")", r.who ~= nil and r.who == pn, tostring(r.who))
				end
			end
			give("MLT_ROLLED")
			if dflt then give("MLT_DEFAULT_READY"); tlog("default mode: wins " .. wins .. "/" .. #mlt.list); mlt.st = 99
			else mlt.st = 4; mlt.t4 = dt end
		elseif dt > mlt.t3 + 40 then
			qa.assert("server: all mutants died and were rolled", false, "rolled " .. rolled .. "/" .. #mlt.list)
			mlt.st = 99
		end
	elseif mlt.st == 4 and dt >= mlt.t4 + 8 then       -- clients had time to check flags + tips
		give("MLT_GO_P1")
		mlt.st = 5; mlt.t5 = dt
	elseif mlt.st == 5 and dt >= mlt.t5 + 8 then
		local c = count_parts("mutant_dog_part")
		qa.assert("server: P1 got exactly one dog part", c[mlt.pa] == 1 and total(c) == 1, "counts " .. ok_str(c))
		qa.assert("server: dog corpse flag gone after the take", #mutant_loot.parts_on(mlt.list[1].id) == 0, "")
		give("MLT_GO_P2")
		mlt.st = 6; mlt.t6 = dt
	elseif mlt.st == 6 and dt >= mlt.t6 + 8 then
		local c = count_parts("mutant_dog_part")
		qa.assert("server: P2 got nothing, still exactly one dog part (P1's)", c[mlt.pb] == nil and c[mlt.pa] == 1 and total(c) == 1, "counts " .. ok_str(c))
		local seen = {}
		for _, tk in ipairs(mutant_loot.test.takes) do seen[#seen + 1] = string.format("%d:%s:%d:obj%.1f:se%.1f", tk.actor, tk.why, tk.n, tk.dist or -1, tk.dist_se or -1) end
		local p1ok, p2empty = false, false
		for _, tk in ipairs(mutant_loot.test.takes) do
			if tk.actor == mlt.pa and tk.why == "ok" and tk.n == 1 then p1ok = true end
			if tk.actor == mlt.pb and tk.why == "empty" then p2empty = true end
		end
		qa.assert("server: take log shows P1 ok(1) and P2 refused as empty (not as too far)", p1ok and p2empty, table.concat(seen, " "))
		give("MLT_P2_DONE")
		give("MLT_GO_RACE")
		mlt.st = 7; mlt.t7 = dt
	elseif mlt.st == 7 and dt >= mlt.t7 + 10 then
		local c = count_parts("mutant_flesh_part")
		qa.assert("server: race for the flesh part -> exactly one part exists", total(c) == 1, "counts " .. ok_str(c))
		qa.assert("server: flesh corpse flag gone after the race", #mutant_loot.parts_on(mlt.list[2].id) == 0, "")
		mlt.st = 99
	end
end

qa.hooks.mloot = function(t, lo)
	local ok, err = pcall(function()
		if OnServer() then server_hooks(t, lo) else client_hooks(t, lo) end
	end)
	if not ok then tlog("ERR " .. tostring(err)) end
end
