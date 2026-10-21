-- TEST ONLY (dmg3)
qa.cfg.scen = "A9s,B9s,A9b,B9b"
qa.cfg.probe = "0"
qa.cfg.sect = "dog_normal"
-- TEST ONLY: damage probe 2.  Quiet spot, one bandit at a time, scripted PM-sized hits from the player.
-- Samples the bandit health every frame (level.add_call) so regen / health-setter behaviour is visible.
-- -Cfg scen=A1,B1  (letters: mult 1.0 / 1.5 ; digit: number of body hits 1..4)   -Cfg power=0.5518
local D = { phase = "wait", t_phase = 0, idx = 0, wrapped = false, samples = nil, seq = 0, quiet = nil }
local function ev(m) qa.event("DMG " .. tostring(m)) end

local function wrap()
	if D.wrapped then return true end
	local ok, err = pcall(function() coop_balance.cfg() end)
	if not ok then ev("coop_balance missing (stock mod): " .. tostring(err)) D.wrapped = true D.nobal = true return true end
	local orig = coop_balance.on_npc_hit
	coop_balance.on_npc_hit = function(obj, amount, who, bone_index)
		local hp0 = obj.health
		local isp = (who ~= nil and db.mp_actors ~= nil and db.mp_actors[who:id()] ~= nil)
		local inv = false
		pcall(function() inv = obj:invulnerable() end)
		orig(obj, amount, who, bone_index)
		local hp1 = obj.health
		D.seq = D.seq + 1
		if D.npc_id and obj:id() == D.npc_id then
			ev(string.format("CB #%d amount=%s bone=%s who=%s player=%s invuln=%s alive=%s hp_at_cb=%.4f hp_after_mult=%.4f mult=%.2f",
				D.seq, tostring(amount), tostring(bone_index), who and tostring(who:name()) or "nil", tostring(isp), tostring(inv), tostring(obj:alive()), hp0, hp1,
				coop_balance.cfg().player_damage_mult))
		end
	end
	D.wrapped = true
	return true
end

-- per frame sampler
local sampler_on = false
local t_start = 0
local function sampler()
	if D.npc_id and D.sampling then
		local n = level.object_by_id(D.npc_id)
		if n then
			local hp = n.health
			local tt = (time_global() - D.sample_t0) / 1000
			if D.last_logged == nil or math.abs(hp - D.last_logged) > 0.0005 or tt - (D.last_tt or -9) >= 1 then
				ev(string.format("S %.2f hp=%.4f", tt, hp))
				D.last_logged = hp; D.last_tt = tt
			end
		end
	end
	return false
end

local function find_quiet(lo)
	local p = lo:position()
	local lv = lo:level_vertex_id()
	local pts = {}
	local n = 0
	-- positions of all NPCs / monsters
	local npcs = {}
	for id = 1, 65534 do
		local o = level.object_by_id(id)
		if o ~= nil and o:id() ~= lo:id() and (IsStalker(o) or IsMonster(o)) then npcs[#npcs + 1] = o:position() end
	end
	ev("npc count " .. #npcs)
	local best, bestd = nil, -1
	for a = 0, 15 do
		local ang = a * math.pi / 8
		local dir = vector():set(math.sin(ang), 0, math.cos(ang))
		for _, dist in ipairs({ 60, 120, 200, 300 }) do
			local v = level.vertex_in_direction(lv, dir, dist)
			if v ~= nil and v ~= 4294967295 then
				local pos = level.vertex_position(v)
				local md = 1e9
				for _, q in ipairs(npcs) do
					local d = q:distance_to(pos)
					if d < md then md = d end
				end
				if md > bestd then bestd = md; best = { pos = pos, v = v } end
			end
		end
	end
	if best then ev(string.format("quiet spot %.1f,%.1f,%.1f clearance %.1f m", best.pos.x, best.pos.y, best.pos.z, bestd)) end
	return best
end

local scens = nil
local function parse()
	local t = {}
	local MM = { A = 1.0, B = 1.5, C = 2.0, D = 1.25 }
	local BB = { s = "bip01_spine", b = "bip01_spine1", p = "bip01_pelvis", h = "bip01_head", c = "bip01_l_hand", a = "bip01_l_upperarm", l = "bip01_l_calf" }
	for tok in string.gmatch(qa.cfg.scen or "A1,B1,A3,B3", "[^,]+") do
		local mc, hits, bc = string.match(tok, "^(%a)(%d)(%a?)$")
		if mc then
			t[#t + 1] = { mult = MM[mc] or 1.0, hits = tonumber(hits), name = tok, bone = BB[bc ~= "" and bc or "b"] or "bip01_spine1" }
		end
	end
	return t
end

qa.hooks.dmg3 = function(t, lo)
	if not OnServer() then return end
	if lo == nil or lo:section() == "spectator" or not lo:alive() then return end
	lo.health = 1
	if not wrap() then return end
	if scens == nil then
		scens = parse()
		pcall(function() level.add_call(sampler, function() end) end)
		ev("scenarios " .. (qa.cfg.scen or "default"))
	end
	local power = tonumber(qa.cfg.power or "0.5518")
	local ph = D.phase
	if ph == "wait" then
		if t < 15 then return end
		if D.quiet == nil then
			D.quiet = find_quiet(lo) or false
			if D.quiet then
				local dir = vector():set(0, 0, 1)
				pcall(function() teleport_local_actor(D.quiet.pos, dir) end)
				ev("teleported")
				D.t_tp = t
			end
			return
		end
		if D.t_tp and t - D.t_tp < 6 then return end
		D.idx = D.idx + 1
		local sc = scens[D.idx]
		if not sc then D.phase = "done"; qa.assert("dmg2 finished", true, "") return end
		D.sc = sc
		if not D.nobal then coop_balance.cfg().player_damage_mult = sc.mult end
		local q = lo:position()
		local pos = vector():set(q.x + 4, q.y, q.z)
		local v = level.vertex_id(pos)
		if v == nil or v == 4294967295 then pos = vector():set(q.x, q.y, q.z); v = lo:level_vertex_id() end
		local ok, se = pcall(function() return alife():create(qa.cfg.sect or "sim_default_bandit_0", pos, v, lo:game_vertex_id()) end)
		ev(string.format("scenario %s mult=%.1f hits=%d create ok=%s id=%s", sc.name, sc.mult, sc.hits, tostring(ok), tostring(ok and se and se.id or se)))
		if not ok or not se then return end
		D.npc_id = se.id; D.phase = "online"; D.t_phase = t
	elseif ph == "online" then
		local n = level.object_by_id(D.npc_id)
		if n == nil then if t - D.t_phase > 40 then D.phase = "done"; qa.assert("npc online", false, "timeout") end return end
		if t - D.t_phase < 5 then return end
		local inv = false
		pcall(function() inv = n:invulnerable() end)
		ev(string.format("online name=%s visual=%s hp=%.4f alive=%s invuln=%s", n:name(), tostring(n:get_visual_name()), n.health, tostring(n:alive()), tostring(inv)))
		if qa.cfg.probe == "1" and not D.probed then
			D.probed = true
			ev("PROBE set health=-0.2 (relative?) hp before=" .. string.format("%.4f", n.health))
			n.health = -0.2
			D.probe_t = t
		end
		if n.health < 0.99 or not n:alive() then
			ev("bandit already hurt by others (hp " .. string.format("%.2f", n.health) .. "), redo scenario")
			local se0 = alife():object(D.npc_id)
			if se0 then pcall(function() alife():release(se0, true) end) end
			D.idx = D.idx - 1; D.npc_id = nil; D.phase = "wait"; D.t_tp = t - 3
			return
		end
		D.npc = n; D.nhit = 0; D.sampling = true; D.sample_t0 = time_global(); D.last_logged = nil
		D.phase = "hitting"; D.t_phase = t
	elseif ph == "hitting" then
		local n = level.object_by_id(D.npc_id)
		if n == nil then D.phase = "wait"; return end
		if D.nhit < D.sc.hits and (t - D.t_phase) >= (1 + D.nhit * 1.0) then
			local h = hit()
			h.draftsman = lo; h.type = hit.fire_wound
			h.direction = n:position():sub(lo:position())
			h.power = power; h.impulse = 75
			h:bone(D.sc.bone)
			local before = n.health
			D.nhit = D.nhit + 1
			n:hit(h)
			ev(string.format("HIT %d: hp before=%.4f after-same-frame=%.4f alive=%s", D.nhit, before, n.health, tostring(n:alive())))
		end
		if (t - D.t_phase) >= (D.sc.hits + 8) or not n:alive() then
			if not n:alive() then ev("npc dead after " .. D.nhit .. " hits") end
			qa.assert("RESULT " .. D.sc.name, true, string.format("mult=%.2f bone=%s hits_applied=%d dead=%s hp_end=%.3f", D.sc.mult, tostring(D.sc.bone), D.nhit, tostring(not n:alive()), n.health))
			D.sampling = false
			D.phase = "cleanup"; D.t_phase = t
		end
	elseif ph == "cleanup" then
		if t - D.t_phase < 3 then return end
		local se = alife():object(D.npc_id)
		if se then pcall(function() alife():release(se, true) end) end
		D.npc_id = nil
		D.phase = "wait"
	end
end
