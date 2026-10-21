--@qa_lib
-- TEST ONLY (never shipped): knife hits-to-kill + Clear Sky vest visuals.  One listen-host run on Cordon:
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner knife -Hooks <this file> -DbFile <db> -SoakSeconds 200 -CompareTimeout 10
-- Part A  the knife in slot 1 of the player (the coop game gives wpn_knife, NOT mp_wpn_knife as default_items says) has the live ini values
--         hit_power 2.6 / hit_power_2 4.2 / hit_type_2 wound; both [wpn_knife] and [mp_wpn_knife] are logged.
-- Part B  KNIFE lines: for sim_default_bandit_0 and sim_default_bandit_3, one NPC at a time on a quiet spot, scripted wound hits from the
--         player (draftsman = player, bone bip01_spine1, one per second) with power hit_power (LMB) and hit_power_2 (RMB), counting hits
--         until not alive().  The hit goes through n:hit(), so coop_balance.on_npc_hit (player_damage_mult) applies like a real strike.
--         A REAL strike cannot be made: this engine build has no level.press_action / hold_action and the harness only has screenshot/console.
-- Part C  VEST lines: cs_heavy / cs_light / cs_mid / exo outfit created in the player inventory one at a time (the first outfit into an
--         empty slot is auto-equipped), live actor visual read with get_visual_name and from the ini; the client logs what it sees (CLVIS).
local L = qa_lib
local function ev(m) qa.event(m) end
local function norm(s) return string.lower(string.gsub(tostring(s), "/", "\\")) end

-- ---------------------------------------------------------------- client side: what the other player sees of every actor
local cl_seen = {}
local cl_next = 0
qa.hooks.knife_cl = function(t, lo)
	if L.on_server() or lo == nil then return end
	if t < cl_next then return end
	cl_next = t + 4
	for id = 1, 40000 do
		local ok, o = pcall(level.object_by_id, id)
		if ok and o ~= nil then
			local ok2, sec = pcall(function() return o:section() end)
			if ok2 and sec ~= nil and string.find(sec, "^actor") and sec ~= "actor_spectator" then
				local okv, vis = pcall(function() return o:get_visual_name() end)
				local oko, out = pcall(function() local w = o:get_current_outfit() return w and w:section() or "none" end)
				local key = tostring(vis) .. "|" .. tostring(out)
				if cl_seen[id] ~= key then
					cl_seen[id] = key
					ev(string.format("CLVIS t=%d id=%d name=%s section=%s visual=%s outfit=%s", t, id, tostring(o:name()), sec, tostring(vis), tostring(out)))
				end
			end
		end
	end
end

-- ---------------------------------------------------------------- helpers
local function find_quiet(lo)
	local lv = lo:level_vertex_id()
	local npcs = {}
	for id = 1, 65534 do
		local o = level.object_by_id(id)
		if o ~= nil and o:id() ~= lo:id() and (IsStalker(o) or IsMonster(o)) then npcs[#npcs + 1] = o:position() end
	end
	ev("KNIFE npc count " .. #npcs)
	local best, bestd = nil, -1
	for a = 0, 15 do
		local ang = a * math.pi / 8
		local dir = vector():set(math.sin(ang), 0, math.cos(ang))
		for _, dist in ipairs({ 30, 60, 90 }) do
			local v = level.vertex_in_direction(lv, dir, dist)
			if v ~= nil and v ~= 4294967295 then
				local pos = level.vertex_position(v)
				local md = 1e9
				if math.abs(pos.y - lo:position().y) > 3 then md = -1 end
				for _, q in ipairs(npcs) do
					local d = q:distance_to(pos)
					if d < md then md = d end
				end
				if md > bestd and md >= 0 then bestd = md; best = { pos = pos, v = v } end
			end
		end
	end
	if best then ev(string.format("KNIFE quiet spot %.1f,%.1f,%.1f clearance %.1f m", best.pos.x, best.pos.y, best.pos.z, bestd)) end
	return best
end

-- one NPC, hits one per second until dead.  Result: { hits, dead, hp0, hp[] }
local function knife_case(label, section, power)
	local res = { hits = 0, hp = {}, label = label }
	local id, tries = nil, 0
	return L.seq({
		"spawn",
		function()
			L.god(true)
			local se, sid = L.spawn_npc(section, { offset = { 4, 0, 0 }, relation = "neutral" })
			if se == nil then ev("KNIFE " .. label .. " spawn failed " .. tostring(sid)) return L.done(nil, "spawn failed") end
			id = sid
			return L.wait_for(function() return L.online(id) ~= nil end, 40)
		end,
		function(c, up)
			if not up then ev("KNIFE " .. label .. " NPC never came online") return L.done(nil, "never online") end
			return L.wait(5)
		end,
		function()
			local n = L.online(id)
			if n == nil then return L.done(nil, "went offline") end
			res.hp0 = n.health
			if res.hp0 < 0.99 or not n:alive() then
				tries = tries + 1
				ev(string.format("KNIFE %s target already hurt (hp %.2f), respawn %d/3", label, res.hp0, tries))
				L.remove(id)
				if tries >= 3 then return L.done(nil, "target keeps getting hurt") end
				return L.wait(3)
			end
			res.visual = n:get_visual_name()
			ev(string.format("KNIFE %s online name=%s visual=%s hp=%.3f power=%.2f mult=%s", label, tostring(n:name()), tostring(res.visual), res.hp0, power, tostring(coop_balance.cfg().player_damage_mult)))
			res.ready = true
		end,
		function()
			if not res.ready then return L.jump("spawn") end
		end,
		function()  -- one hit per pass
			local n = L.online(id)
			if n == nil or not n:alive() or res.hits >= 12 then return end
			local before, after = L.hit(n, { type = hit.wound, bone = "bip01_spine1", power = power, impulse = 75 })
			res.hits = res.hits + 1
			res.hp[#res.hp + 1] = after
			ev(string.format("KNIFE %s hit %d power=%.2f hp %.4f -> %.4f", label, res.hits, power, before, after))
			return L.again(1.0)
		end,
		function()
			local n = L.online(id)
			res.dead = (n == nil) or (not n:alive())
			res.hp_end = n and n.health or nil
			ev(string.format("KNIFE %s RESULT hits=%d dead=%s hp_end=%s", label, res.hits, tostring(res.dead), tostring(res.hp_end)))
			return L.wait(2)
		end,
		function()
			L.remove(id)
			return L.done(res)
		end,
	}, "knife_" .. label)
end

local function vis_now(p)
	local ok, v = pcall(function() return p:get_visual_name() end)
	return ok and v or ("ERR " .. tostring(v))
end
local function outfit_now(p)
	local ok, w = pcall(function() return p:get_current_outfit() end)
	if ok and w then return w:section() end
	return "none"
end

-- "false" when the outfit blocks the helmet slot (helmet_avaliable = false, the engine's own spelling), "unset" when the key is absent
local function helmet_flag(sec)
	local ok, v = pcall(function()
		local ini = system_ini()
		if not ini:line_exist(sec, "helmet_avaliable") then return "unset" end
		return tostring(ini:r_bool(sec, "helmet_avaliable"))
	end)
	return ok and v or ("ERR " .. tostring(v))
end

local function vest_case(sec)
	local r = { sec = sec }
	return L.seq({
		function()
			local p = L.player(nil)
			r.before = vis_now(p)
			local ids, err = L.give_item(nil, sec, 1)
			r.id = ids and ids[1]
			ev(string.format("VEST %s give id=%s err=%s visual before=%s", sec, tostring(r.id), tostring(err), tostring(r.before)))
			return L.wait(6)
		end,
		function()
			local p = L.player(nil)
			r.out = outfit_now(p)
			r.vis = vis_now(p)
			local ok, ini = pcall(function() return system_ini():r_string(sec, "actor_visual") end)
			r.ini = ok and ini or ("ERR " .. tostring(ini))
			r.helm = helmet_flag(sec)
			ev(string.format("VEST %s worn=%s live_visual=%s ini_actor_visual=%s", sec, r.out, tostring(r.vis), tostring(r.ini)))
			return L.wait(2)
		end,
		function()
			if r.id then L.remove(r.id) end
			return L.wait(5)
		end,
		function()
			local p = L.player(nil)
			r.after = vis_now(p)
			ev(string.format("VEST %s removed: worn=%s visual=%s", sec, outfit_now(p), tostring(r.after)))
			return L.done(r)
		end,
	}, "vest_" .. sec)
end

local function vest_check(tag, r, sec, want)
	qa.assert("VEST " .. tag .. " ini actor_visual is " .. want, r ~= nil and string.find(norm(r.ini), norm(want), 1, true) ~= nil, tostring(r and r.ini))
	qa.assert("VEST " .. tag .. " worn", r ~= nil and r.out == sec, tostring(r and r.out))
	qa.assert("VEST " .. tag .. " live visual is " .. want, r ~= nil and string.find(norm(r.vis), norm(want), 1, true) ~= nil, tostring(r and r.vis))
end

-- ---------------------------------------------------------------- the test
qa.once("knife_vest_main", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	L.task("knife_vest", {
		function(c) L.god(true) return L.wait(12) end,
		function(c)
			-- Part A
			local p = L.player(nil)
			local knife = nil
			for s = 0, 7 do
				local ok, it = pcall(function() return p:item_in_slot(s) end)
				if ok and it ~= nil then
					ev(string.format("KNIFE slot %d = %s", s, tostring(it:section())))
					if it:section() == "mp_wpn_knife" and knife == nil then knife = s end
				end
			end
			local ok1, it1 = pcall(function() return p:item_in_slot(1) end)
			c.ksec = (ok1 and it1 ~= nil) and it1:section() or "mp_wpn_knife"
			qa.assert("KNIFE player slot 1 is a knife (mp_wpn_knife expected, wpn_knife is what the coop game really gives)", c.ksec == "mp_wpn_knife" or c.ksec == "wpn_knife", "slot1=" .. tostring(c.ksec))
			ev("KNIFE real knife section of the player = " .. tostring(c.ksec))
			local ini = system_ini()
			for _, sec in ipairs({ "wpn_knife", "mp_wpn_knife" }) do
				ev(string.format("KNIFE ini [%s] hit_power=%s hit_power_2=%s hit_type=%s hit_type_2=%s", sec, tostring(ini:r_float(sec, "hit_power")), tostring(ini:r_float(sec, "hit_power_2")), tostring(ini:r_string(sec, "hit_type")), tostring(ini:r_string(sec, "hit_type_2"))))
			end
			c.hp1 = ini:r_float(c.ksec, "hit_power")
			c.hp2 = ini:r_float(c.ksec, "hit_power_2")
			c.ht = ini:r_string(c.ksec, "hit_type")
			c.ht2 = ini:r_string(c.ksec, "hit_type_2")
			qa.assert("KNIFE ini [" .. c.ksec .. "] hit_power 2.6", math.abs(c.hp1 - 2.6) < 0.001, tostring(c.hp1))
			qa.assert("KNIFE ini [" .. c.ksec .. "] hit_power_2 4.2", math.abs(c.hp2 - 4.2) < 0.001, tostring(c.hp2))
			qa.assert("KNIFE ini [" .. c.ksec .. "] hit_type_2 wound", c.ht2 == "wound", tostring(c.ht2))
			local okm, mult = pcall(function() return coop_balance.cfg().player_damage_mult end)
			ev("KNIFE host player_damage_mult = " .. tostring(okm and mult or ("ERR " .. tostring(mult))))
			-- Part B: quiet spot
			c.q = find_quiet(p)
			if c.q then return L.teleport(nil, c.q.pos) end
			return L.now(false, "no quiet spot")
		end,
		function(c, ok, how)
			ev("KNIFE teleport ok=" .. tostring(ok) .. " how=" .. tostring(how))
			return L.wait(8)
		end,
		function(c) return knife_case("bandit0_LMB", "sim_default_bandit_0", c.hp1) end,
		function(c, r) c.r1 = r return knife_case("bandit0_RMB", "sim_default_bandit_0", c.hp2) end,
		function(c, r) c.r2 = r return knife_case("bandit3_LMB", "sim_default_bandit_3", c.hp1) end,
		function(c, r) c.r3 = r return knife_case("bandit3_RMB", "sim_default_bandit_3", c.hp2) end,
		function(c, r)
			c.r4 = r
			local function rep(label, rr, want)
				local h = rr and rr.hits or -1
				ev(string.format("KNIFE SUMMARY %s hits=%s expected=%d dead=%s", label, tostring(h), want, tostring(rr and rr.dead)))
				qa.assert("KNIFE " .. label .. " kills in " .. want .. " hit(s)", rr ~= nil and rr.dead == true and rr.hits == want, "hits=" .. tostring(h) .. " dead=" .. tostring(rr and rr.dead))
			end
			rep("bandit0 LMB", c.r1, 2)
			rep("bandit0 RMB", c.r2, 1)
			rep("bandit3 LMB", c.r3, 2)
			rep("bandit3 RMB", c.r4, 1)
			return L.wait(2)
		end,
		-- Part C: vests.  Clear Sky outfits wear the Clear Sky fighter bodies of xrMPE (actors\stalker_mp\stalker_nebo_1/2/3); exo is the SoC control.
		function(c) return vest_case("cs_heavy_outfit") end,
		function(c, r) c.v1 = r vest_check("cs_heavy", r, "cs_heavy_outfit", "actors\\stalker_mp\\stalker_nebo_2") return vest_case("cs_light_outfit") end,
		function(c, r) c.v2 = r vest_check("cs_light", r, "cs_light_outfit", "actors\\stalker_mp\\stalker_nebo_1") return vest_case("cs_mid_outfit") end,
		function(c, r)
			c.v3 = r
			vest_check("cs_mid", r, "cs_mid_outfit", "actors\\stalker_mp\\stalker_nebo_3")
			-- the nebo_3 body has a helmet: the helmet slot is locked (FOSTER); the two Clear Sky suits with a bare head stay open
			qa.assert("VEST cs_mid helmet_avaliable is false (helmet slot locked)", r ~= nil and r.helm == "false", tostring(r and r.helm))
			qa.assert("VEST cs_light helmet slot open", c.v2 ~= nil and c.v2.helm ~= "false", tostring(c.v2 and c.v2.helm))
			qa.assert("VEST cs_heavy helmet slot open", c.v1 ~= nil and c.v1.helm ~= "false", tostring(c.v1 and c.v1.helm))
			for _, sec in ipairs({ "military_outfit", "specops_outfit", "specops_outfit_therapeutic", "soldier_outfit", "black_coat_outfit", "merc_outfit", "exo_outfit", "scientific_outfit" }) do
				qa.assert("HELM " .. sec .. " helmet_avaliable is false", helmet_flag(sec) == "false", helmet_flag(sec))
			end
			return vest_case("exo_outfit")
		end,
		function(c, r)
			c.v4 = r
			local function differs(a, b) return a ~= nil and b ~= nil and norm(a.ini) ~= norm(b.ini) end
			qa.assert("VEST cs_heavy differs from exo (ini)", differs(c.v1, c.v4), "")
			qa.assert("VEST cs_heavy differs from cs_light (ini)", differs(c.v1, c.v2), "")
			qa.assert("VEST cs_heavy differs from cs_mid (ini)", differs(c.v1, c.v3), "")
			qa.assert("VEST cs_heavy is not a SoC hero mesh (marked_one)", c.v1 ~= nil and string.find(norm(c.v1.ini), "marked_one", 1, true) == nil, tostring(c.v1 and c.v1.ini))
			qa.assert("VEST exo ini is stalker_exoskeleton", c.v4 ~= nil and string.find(norm(c.v4.ini), "stalker_exoskeleton", 1, true) ~= nil, tostring(c.v4 and c.v4.ini))
			return L.wait(6)  -- the client logs CLVIS lines meanwhile
		end,
		function(c) qa.assert("knife_vest run finished", true, "") return L.done() end,
	})
end)
