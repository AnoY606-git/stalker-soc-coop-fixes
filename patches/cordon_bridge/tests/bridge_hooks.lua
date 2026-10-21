-- Test probes for the Cordon bridge soldiers (patch cordon_bridge). TEST ONLY, never shipped.
-- Needs the live console (tools\stalker_xrmpe\live):
--   start_live.ps1 -Map coop_l01_escape -Owner <you> -Name br -Clients 2 -ExtraDir <stage>\gamedata -Hooks <this file>
--   lua.ps1 -Name br "bp.help()"        (server role S: has alife(); every test below runs there)
-- Every bp.t_* test is ONE command and answers with a first line "PASS bp.t_x: ..." or "FAIL bp.t_x: ..." (details on the lines below).
-- The tests that turn the soldiers hostile (t_hit, t_zone, t_kill, t_save) need a FRESH game each: the order flag and the soldiers' sections
-- cannot be undone. bp.t_soldiers / bp.t_neutral / bp.t_nohit change nothing and can run first, in this order, in the same session.
-- Self-contained: needs only the live table (live_hooks.lua). No coroutines (this engine crashes on them): the tests are frame-stepped.
bp = bp or {}

local FLAG = "ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO"
local VODKA = "ESC_START_5_BOTTLES_OF_VODKA_FOR_KUZNETSOV_QUEST_TASK_INFO"
local ZONE = "esc_the_order_to_attack_the_players_space_restrictor"
local KUZ_SEC = "esc_smart_terrain_7_military_kuznetsov"

-- the SoC posts (see tools\make_paths.py); a soldier counts as "at its post" within POST_TOL m (x/z). Post 4 patrols between a and b.
local CENTER = { 57.0, 1.0, 157.0 }
local POSTS = {
	{ n = 1, a = { 45.5, 2.7, 142.0 } },
	{ n = 2, a = { 63.0, 3.2, 171.7 } },
	{ n = 3, a = { 47.8, 2.7, 174.2 } },
	{ n = 4, a = { 71.5, 2.8, 135.7 }, b = { 70.9, 2.8, 168.4 } },
	{ n = 5, a = { 51.4, 2.3, 178.9 } },
}
local KUZ = { 59.5, 1.9, 130.9 }
local POST_TOL = 5.0
-- the restrictor box in all.spawn: centre (56.86, 0.59, 157.13), size 32.29 x 35.55 x 42.43, axis aligned
local BOX = { x0 = 40.72, x1 = 73.01, z0 = 135.92, z1 = 178.35, y0 = -17.18, y1 = 18.37 }
local SAFE = { 59.5, 1.9, 127.0 }     -- 3.9 m in front of Kuznetsov, 8.9 m outside the south edge of the box
local INSIDE = { 62.9, -0.3, 149.3 }  -- the campfire spot under the bridge, inside the box
local FAR = { -206.0, -19.6, -130.0 } -- Cordon village campfire: bp.go('far') leaves the hostile soldiers behind

local function safe(f, ...)
	local ok, r = pcall(f, ...)
	if ok then return r end
	return nil
end
local function f1(v) return string.format("%.1f", v) end
local function now() return time_global() / 1000 end
local function verdict(ok, name, text) return (ok and "PASS " or "FAIL ") .. name .. ": " .. text end

function bp.flag() return story_flags.has_flag(FLAG) == true end
function bp.vodka() return story_flags.has_flag(VODKA) == true end
function bp.give_vodka() story_flags.give_flag(VODKA) return bp.vodka() end
function bp.help()
	return table.concat({
		"bp.t_soldiers()      5 soldiers + Kuznetsov, one per SoC post, jobs army_1..5            (no change)",
		"bp.t_neutral([60])   a player stands next to Kuznetsov, outside the zone: nobody attacks   (no change)",
		"bp.t_nohit()         a mutant and an NPC hit a soldier: the order must NOT be given        (no change)",
		"bp.t_hit(['qaB'])    that player hits one soldier: flag + every soldier hostile            (FRESH game)",
		"bp.t_kill(['qaB'])   that player kills a soldier of the 2 man squad (no hit): flag + hostile (FRESH game)",
		"bp.t_zone()          player teleports into the bridge zone: flag + every soldier hostile    (FRESH game, vodka quest not taken)",
		"bp.t_save()          after a hostile test: checks and saves.  Then:  live.load_last()  and, when the level is back:  bp.t_load()",
		"bp.report()          one line per soldier, any time",
		"bp.go('safe'|'inside'|'far' [,'qaB'])   teleport the players (snapped to the AI mesh);  bp.god_on() / bp.god_off()   keep the players at full health",
	}, "\n")
end

-- ---------------------------------------------------------------------------------------------------------------- geometry
local function in_box(x, y, z) return x >= BOX.x0 and x <= BOX.x1 and z >= BOX.z0 and z <= BOX.z1 and y >= BOX.y0 and y <= BOX.y1 end

-- engine shape test of the restrictor (only when the zone object is online); nil when it is not
function bp.inside(x, y, z)
	local zn = db.zone_by_name and db.zone_by_name[ZONE]
	if not zn then return nil end
	return zn:inside(vector():set(x, y, z))
end

local function ground(p)
	local v = vector():set(p[1], p[2], p[3])
	local lv = safe(level.vertex_id, v)
	if lv ~= nil and lv < 4000000000 then return level.vertex_position(lv) end
	return v
end

-- bp.go("safe"|"inside"|"far" [, player]) : teleport (default: every player) to a test spot, snapped to the AI mesh. Answers like live.tp.
--   safe   = 3.9 m in front of Kuznetsov, outside the zone      inside = the campfire spot under the bridge, inside the zone
--   far    = the Cordon village campfire (leave the hostile soldiers behind)
function bp.go(where, who)
	local spot = ({ safe = SAFE, inside = INSIDE, far = FAR })[where or "safe"]
	if not spot then error("bp.go: safe, inside or far") end
	local p = ground(spot)
	return live.tp(p.x, p.y, p.z, who)
end

-- bp.god_on() / bp.god_off(): the harness tick tops every player up to full health (best effort; the tests also top up while they run)
bp.god = bp.god or false
function bp.god_on() bp.god = true return "god mode on (players are topped up every tick)" end
function bp.god_off() bp.god = false return "god mode off" end
if qa and qa.hooks then
	qa.hooks.bp_guard = function()
		if not bp.god then return end
		if not (alife and alife() ~= nil) then return end
		for _, p in ipairs(live.players()) do
			if p.alive then
				local h = safe(function() return p.obj.health end)
				if h and h < 0.97 then pcall(function() p.obj.health = 1 - p.obj.health end) end
			end
		end
	end
end

local function dxz(a, b) return math.sqrt((a.x - b[1]) ^ 2 + (a.z - b[3]) ^ 2) end

-- ---------------------------------------------------------------------------------------------------------------- soldiers
local function army(r)
	return r.stalker and (string.find(r.section, "sim_default_military", 1, true) == 1 or r.section == KUZ_SEC)
end

local function players() return live.players() end
local function player_ids()
	local t = {}
	for _, p in ipairs(players()) do t[p.id] = p.name end
	return t
end
local function find_player(who)
	local ps = players()
	if who == nil then
		if live.first_player then return live.first_player() end
		return ps[1]
	end
	for _, p in ipairs(ps) do
		if p.id == who or string.lower(tostring(p.name)) == string.lower(tostring(who)) then return p end
	end
	return nil
end

-- every army NPC around the bridge (server entities, online or offline); online ones also get their active section and best enemy
function bp.soldiers(radius)
	local pids = player_ids()
	local out = {}
	for _, r in ipairs(live.near(CENTER, radius or 70, army)) do
		r.kuz = (r.section == KUZ_SEC)
		local se = safe(function() return alife():object(r.id) end)
		local g = se and se.group_id
		if g and g ~= 65535 then
			local sq = safe(function() return alife():object(g) end)
			r.squad = sq and safe(function() return sq:section_name() end)
			r.squad_n = sq and safe(function() return sq:npc_count() end)
		end
		if r.online and r.alive ~= false then
			local st = db.storage and db.storage[r.id]
			r.sect = st and st.active_section and tostring(st.active_section) or nil
			r.job_n = r.sect and tonumber(string.match(r.sect, "army_(%d+)")) or nil
			r.hostile = r.sect ~= nil and string.find(r.sect, "attack_players", 1, true) ~= nil
			local o = level.object_by_id(r.id)
			local be = o and safe(function() return o:best_enemy() end)
			local bid = be and safe(function() return be:id() end)
			if bid and pids[bid] then r.enemy = pids[bid] end
		end
		out[#out + 1] = r
	end
	return out
end

local function counts(s)
	local c = { n = #s, alive = 0, online = 0, hostile = 0, engaged = 0, dead = 0, soldiers = 0, kuz = 0, names = {} }
	for _, r in ipairs(s) do
		if r.alive == false then
			c.dead = c.dead + 1
		else
			c.alive = c.alive + 1
			if r.kuz then c.kuz = c.kuz + 1 else c.soldiers = c.soldiers + 1 end
			if r.online then
				c.online = c.online + 1
				if r.hostile then c.hostile = c.hostile + 1 end
				if r.enemy then c.engaged = c.engaged + 1 c.names[r.enemy] = true end
			end
		end
	end
	return c
end

local function lines(s)
	local t = {}
	for _, r in ipairs(s) do
		t[#t + 1] = string.format("  #%d %s %s %s (%s,%s,%s) %s sect=%s squad=%s/%s%s", r.id, tostring(r.name), tostring(r.section), r.online and "online" or "offline",
			f1(r.pos.x), f1(r.pos.y), f1(r.pos.z), r.alive == false and "DEAD" or "alive", tostring(r.sect), tostring(r.squad), tostring(r.squad_n),
			r.enemy and (" ENEMY=" .. tostring(r.enemy)) or "")
	end
	return table.concat(t, "\n")
end

function bp.report(radius)
	local s = bp.soldiers(radius)
	local c = counts(s)
	local hp = {}
	for _, p in ipairs(players()) do
		local q = safe(function() return p.obj:position() end)
		hp[#hp + 1] = string.format("%s hp=%s at %s", tostring(p.name), f1(safe(function() return p.obj.health end) or -1), q and ("(" .. f1(q.x) .. "," .. f1(q.y) .. "," .. f1(q.z) .. ")") or "?")
	end
	return string.format("army NPCs=%d (soldiers %d + Kuznetsov %d alive, %d dead) online=%d hostile_section=%d engaging_a_player=%d FLAG=%s VODKA=%s | %s\n%s",
		c.n, c.soldiers, c.kuz, c.dead, c.online, c.hostile, c.engaged, tostring(bp.flag()), tostring(bp.vodka()), table.concat(hp, "; "), lines(s))
end

-- ---------------------------------------------------------------------------------------------------------------- frame-stepped runner
-- a test is a function(c) called every frame; it returns nil to run again, or the final answer string
local function runner(timeout, name, fn)
	local c = { ph = 1, t0 = now(), dmg = 0 }
	return live.async(function()
		local ok, r = pcall(fn, c)
		if not ok then return "FAIL " .. name .. ": script error: " .. tostring(r) end
		return r
	end, timeout)
end

-- top the players up so the soldiers cannot end the test; returns how many frames a player was hurt in
local function guard()
	local n = 0
	for _, p in ipairs(players()) do
		if p.alive then
			local h = safe(function() return p.obj.health end)
			if h and h < 0.97 then
				n = n + 1
				pcall(function() p.obj.health = 1 - p.obj.health end)
			end
		end
	end
	return n
end

-- run a sub-async (live.tp) over several frames; nil while running, then its answer
local function sub(c, key, maker)
	local s = c[key]
	if s == nil then
		local a = maker()
		if type(a) == "table" and type(a.step) == "function" then s = { a = a } else s = { done = true, res = a } end
		c[key] = s
	end
	if s.done then return s.res end
	local r = s.a.step()
	if r ~= nil then s.done = true s.res = r return r end
	return nil
end
local function tp_ok(r) return type(r) == "string" and string.find(r, "moved to", 1, true) ~= nil end
local function tp(c, key, spot, who)
	return sub(c, key, function()
		local p = ground(spot)
		return live.tp(p.x, p.y, p.z, who)
	end)
end

local function make_hit(attacker_obj, power)
	local h = hit()
	h.type = hit.fire_wound
	h.power = power or 0.05
	h.impulse = 0
	h.direction = vector():set(0, 0, 1)
	h.draftsman = attacker_obj
	if not pcall(function() h:bone("bip01_spine1") end) then pcall(function() h.bone = "bip01_spine1" end) end
	return h
end

local function nearest_victim(s, from, want_kuz)
	local best
	for _, r in ipairs(s) do
		if r.online and r.alive ~= false and (r.kuz == (want_kuz == true)) then
			local d = r.pos:distance_to(from)
			if not best or d < best.d then best = { r = r, d = d } end
		end
	end
	return best and best.r
end

-- ---------------------------------------------------------------------------------------------------------------- T1: count and posts
-- 5 army soldiers + Kuznetsov alive; each SoC post has one soldier of its own (greedy match, 5 m); online soldiers hold the jobs army_1..5
function bp.t_soldiers()
	local N = "bp.t_soldiers"
	local s = bp.soldiers(70)
	local c = counts(s)
	local ok = true
	local notes = {}
	if c.soldiers ~= 5 then ok = false notes[#notes + 1] = c.soldiers .. " alive soldiers, expected 5" end
	if c.kuz ~= 1 then ok = false notes[#notes + 1] = c.kuz .. " alive Kuznetsov, expected 1" end
	if c.dead > 0 then notes[#notes + 1] = c.dead .. " dead (a fresh game has none)" end
	-- post matching: distance to the post point, for post 4 to the patrol segment a-b
	local function post_dist(post, pos)
		if not post.b then return dxz(pos, post.a) end
		local ax, az, bx, bz = post.a[1], post.a[3], post.b[1], post.b[3]
		local t = ((pos.x - ax) * (bx - ax) + (pos.z - az) * (bz - az)) / ((bx - ax) ^ 2 + (bz - az) ^ 2)
		t = math.max(0, math.min(1, t))
		return math.sqrt((pos.x - (ax + t * (bx - ax))) ^ 2 + (pos.z - (az + t * (bz - az))) ^ 2)
	end
	local free = {}
	for _, r in ipairs(s) do if r.alive ~= false and not r.kuz then free[#free + 1] = r end end
	local matched = 0
	for _, post in ipairs(POSTS) do
		local bi, bd
		for i, r in ipairs(free) do
			local d = post_dist(post, r.pos)
			if bd == nil or d < bd then bi, bd = i, d end
		end
		if bi and bd <= POST_TOL then
			matched = matched + 1
			table.remove(free, bi)
		else
			notes[#notes + 1] = string.format("post %d: nearest soldier %s m away (limit %s)", post.n, bd and f1(bd) or "none", f1(POST_TOL))
		end
	end
	if matched ~= 5 then ok = false end
	local kd
	for _, r in ipairs(s) do if r.kuz and r.alive ~= false then kd = dxz(r.pos, KUZ) end end
	if kd == nil or kd > POST_TOL then ok = false notes[#notes + 1] = "Kuznetsov is " .. (kd and f1(kd) or "?") .. " m from his post" end
	-- jobs (online soldiers only)
	local jobs, jobn = {}, 0
	for _, r in ipairs(s) do
		if r.online and r.alive ~= false and not r.kuz then
			if r.job_n then
				if jobs[r.job_n] then ok = false notes[#notes + 1] = "job army_" .. r.job_n .. " is held by two soldiers" end
				jobs[r.job_n] = true
				jobn = jobn + 1
			else
				notes[#notes + 1] = "soldier #" .. r.id .. " has no army job yet (section " .. tostring(r.sect) .. ")"
			end
		end
	end
	if c.online == c.alive and jobn == 5 then
		for n = 1, 5 do if not jobs[n] then ok = false notes[#notes + 1] = "no soldier holds army_" .. n end end
	elseif c.online < c.alive then
		notes[#notes + 1] = (c.alive - c.online) .. " soldier(s) offline: positions are the stored ones, jobs not checked; stand within 100 m of the bridge and repeat"
	end
	if c.hostile > 0 or bp.flag() then ok = false notes[#notes + 1] = "already hostile / flag set (not a fresh game)" end
	return verdict(ok, N, string.format("%d soldiers + %d Kuznetsov alive, %d of 5 posts matched, %d online, jobs held %d%s", c.soldiers, c.kuz, matched, c.online, jobn,
		#notes > 0 and ("; " .. table.concat(notes, "; ")) or "")) .. "\n" .. lines(s)
end

-- ---------------------------------------------------------------------------------------------------------------- T2: neutrality
function bp.t_neutral(secs)
	secs = secs or 60
	local N = "bp.t_neutral"
	return runner(secs + 120, N, function(c)
		if c.ph == 1 then
			if bp.flag() then return "FAIL " .. N .. ": the order flag is already set: use a fresh game" end
			local a = bp.inside(SAFE[1], SAFE[2], SAFE[3])
			if in_box(SAFE[1], SAFE[2], SAFE[3]) or a == true then return "FAIL " .. N .. ": test spot is inside the zone (box or engine test): the table SAFE is wrong" end
			c.ph = 2
		end
		if c.ph == 2 then
			local r = tp(c, "tp", SAFE, find_player(nil) and find_player(nil).id)
			if r == nil then return nil end
			if not tp_ok(r) then return "FAIL " .. N .. ": could not move the player: " .. tostring(r) end
			c.t1, c.next, c.maxh, c.maxe, c.minon, c.ph = now(), now(), 0, 0, 99, 3
		end
		if c.ph == 3 then
			c.dmg = c.dmg + guard()
			if bp.flag() then c.flag = true end
			if now() >= c.next then
				c.next = now() + 2
				local k = counts(bp.soldiers(70))
				if k.hostile > c.maxh then c.maxh = k.hostile end
				if k.engaged > c.maxe then c.maxe = k.engaged end
				if k.online < c.minon then c.minon = k.online end
				c.last = k
			end
			if c.flag or now() - c.t1 >= secs then c.ph = 4 else return nil end
		end
		local s = bp.soldiers(70)
		local k = counts(s)
		local ok = (not c.flag) and c.dmg == 0 and c.maxh == 0 and c.maxe == 0 and k.online >= 4
		local why = {}
		if c.flag then why[#why + 1] = "the order flag was given" end
		if c.dmg > 0 then why[#why + 1] = c.dmg .. " frames with a hurt player" end
		if c.maxh > 0 then why[#why + 1] = c.maxh .. " soldiers switched to attack_players" end
		if c.maxe > 0 then why[#why + 1] = c.maxe .. " soldiers had a player as enemy" end
		if k.online < 4 then why[#why + 1] = "only " .. k.online .. " army NPCs online: inconclusive" end
		return verdict(ok, N, string.format("player stood %.0f s next to Kuznetsov outside the zone; flag=%s hurt_frames=%d hostile_max=%d engaged_max=%d online=%d%s", now() - c.t1,
			tostring(bp.flag()), c.dmg, c.maxh, c.maxe, k.online, #why > 0 and ("; " .. table.concat(why, "; ")) or "")) .. "\n" .. lines(s)
	end)
end

-- ---------------------------------------------------------------------------------------------------------------- T3: hits by mutant / NPC must not give the order
function bp.t_nohit()
	local N = "bp.t_nohit"
	return runner(120, N, function(c)
		if c.ph == 1 then
			if bp.flag() then return "FAIL " .. N .. ": the order flag is already set: use a fresh game" end
			local pl = find_player(nil)
			if not pl then return "FAIL " .. N .. ": no player" end
			c.pl = pl
			c.ph = 2
		end
		if c.ph == 2 then
			local r = tp(c, "tp", SAFE, c.pl.id)
			if r == nil then return nil end
			if not tp_ok(r) then return "FAIL " .. N .. ": could not move the player: " .. tostring(r) end
			c.t1, c.ph = now(), 3
		end
		if c.ph == 3 then                           -- let the area settle, then spawn the attackers 3 m from the player
			c.dmg = c.dmg + guard()
			if now() - c.t1 < 3 then return nil end
			local sim = alife()
			local p = ground({ SAFE[1] + 3, SAFE[2], SAFE[3] })
			local lv = level.vertex_id(p)
			local gv = c.pl.obj:game_vertex_id()
			local d = sim:create("dog_weak", p, lv, gv)
			local b = sim:create("sim_default_bandit_1", p, lv, gv)
			c.ids = { d and d.id, b and b.id }
			if not (c.ids[1] and c.ids[2]) then return "FAIL " .. N .. ": could not spawn the attackers" end
			c.t2, c.ph = now(), 4
		end
		if c.ph == 4 then                           -- both online?
			c.dmg = c.dmg + guard()
			local od, ob = level.object_by_id(c.ids[1]), level.object_by_id(c.ids[2])
			if od and ob then
				c.od, c.ob = od, ob
				local v = nearest_victim(bp.soldiers(70), c.pl.obj:position(), false)
				if not v then return "FAIL " .. N .. ": no online soldier near the player" end
				c.vid = v.id
				local vo = level.object_by_id(v.id)
				vo:hit(make_hit(od, 0.03))
				vo:hit(make_hit(ob, 0.03))
				c.t3, c.ph = now(), 5
			elseif now() - c.t2 > 15 then
				return "FAIL " .. N .. ": the spawned attackers did not come online"
			end
			return nil
		end
		if c.ph == 5 then                           -- the hits land on the next frame; release the attackers after 2 s so they cannot kill anybody
			c.dmg = c.dmg + guard()
			if bp.flag() then c.flag = true end
			if now() - c.t3 < 2 then return nil end
			for _, id in ipairs(c.ids) do pcall(function() local se = alife():object(id) if se then alife():release(se, true) end end) end
			c.t4, c.ph = now(), 6
			return nil
		end
		if c.ph == 6 then                           -- 6 more seconds: the order must still be off
			c.dmg = c.dmg + guard()
			if bp.flag() then c.flag = true end
			if not c.flag and now() - c.t4 < 6 then return nil end
			local vo = level.object_by_id(c.vid)
			local hp = vo and safe(function() return vo.health end)
			local k = counts(bp.soldiers(70))
			local ok = (not c.flag) and k.hostile == 0
			return verdict(ok, N, string.format("a mutant (dog_weak) and an NPC (bandit) each hit soldier #%d (health now %s); flag=%s hostile_sections=%d%s", c.vid, hp and f1(hp) or "?",
				tostring(bp.flag()), k.hostile, ok and "" or "; the order must stay off for non-player hits"))
		end
	end)
end

-- ---------------------------------------------------------------------------------------------------------------- hostile checks shared by t_hit / t_kill / t_zone
-- after the trigger: wait for the flag, then for every online alive army NPC to be in an attack_players section
local function hostile_phase(c, N, label, flag_limit, all_limit)
	c.dmg = c.dmg + guard()
	if c.ph == 10 then                                  -- waiting for the flag
		if bp.flag() then c.tflag = now() - c.t_trigger c.ph = 11 c.t_flag_at = now()
		elseif now() - c.t_trigger > flag_limit then
			return "FAIL " .. N .. ": " .. label .. " but the order flag was NOT given within " .. flag_limit .. " s\n" .. lines(bp.soldiers(70))
		else return nil end
	end
	if c.ph == 11 then                                  -- waiting for the soldiers
		local s = bp.soldiers(70)
		local k = counts(s)
		if (k.online > 0 and k.hostile == k.online) or now() - c.t_flag_at > all_limit then
			local ok = k.online >= 5 and k.hostile == k.online
			if k.online >= 5 and k.hostile == k.online then c.tall = now() - c.t_trigger end
			local names = {}
			for n in pairs(k.names) do names[#names + 1] = n end
			table.sort(names)
			local why = ""
			if k.online < 5 then why = "; only " .. k.online .. " army NPCs online: inconclusive" elseif k.hostile ~= k.online then why = "; " .. (k.online - k.hostile) .. " still neutral" end
			return verdict(ok, N, string.format("%s -> flag after %.1f s, %d of %d online army NPCs hostile%s, engaging players: [%s], hurt_frames=%d%s",
				label, c.tflag or -1, k.hostile, k.online, c.tall and string.format(" after %.1f s", c.tall) or "", table.concat(names, ","), c.dmg, why)) .. "\n" .. lines(s)
		end
		return nil
	end
end

-- ---------------------------------------------------------------------------------------------------------------- T4: a player hits one soldier
function bp.t_hit(who)
	local N = "bp.t_hit"
	return runner(150, N, function(c)
		if c.ph == 1 then
			if bp.flag() then return "FAIL " .. N .. ": the order flag is already set: use a fresh game" end
			bp.god = true
			c.pl = find_player(who)
			if not c.pl then return "FAIL " .. N .. ": no player " .. tostring(who) end
			c.ph = 2
		end
		if c.ph == 2 then
			local r = tp(c, "tp", SAFE, nil)              -- everybody to the safe spot (a 2 player run: both stand there)
			if r == nil then return nil end
			if not tp_ok(r) then return "FAIL " .. N .. ": could not move the players: " .. tostring(r) end
			c.t1, c.ph = now(), 3
		end
		if c.ph == 3 then
			c.dmg = c.dmg + guard()
			if now() - c.t1 < 4 then return nil end
			if bp.flag() then return "FAIL " .. N .. ": the flag came before any hit (zone or squad death?)" end
			local v = nearest_victim(bp.soldiers(70), c.pl.obj:position(), false)
			if not v then return "FAIL " .. N .. ": no online soldier near the player" end
			local vo = level.object_by_id(v.id)
			vo:hit(make_hit(c.pl.obj, 0.05))
			c.label = string.format("player %s hit soldier #%d (squad %s) once with 5%% damage", tostring(c.pl.name), v.id, tostring(v.squad))
			c.t_trigger, c.ph = now(), 10
			return nil
		end
		return hostile_phase(c, N, c.label, 10, 30)
	end)
end

-- ---------------------------------------------------------------------------------------------------------------- T5: a player kills a soldier WITHOUT a hit (only the death scheme can give the order)
-- victim: a soldier of the 2 man squad (esc_smart_terrain_7_military_4_squad), so the squad-death flag cannot fire
function bp.t_kill(who)
	local N = "bp.t_kill"
	return runner(150, N, function(c)
		if c.ph == 1 then
			if bp.flag() then return "FAIL " .. N .. ": the order flag is already set: use a fresh game" end
			bp.god = true
			c.pl = find_player(who)
			if not c.pl then return "FAIL " .. N .. ": no player " .. tostring(who) end
			c.ph = 2
		end
		if c.ph == 2 then
			local r = tp(c, "tp", SAFE, nil)
			if r == nil then return nil end
			if not tp_ok(r) then return "FAIL " .. N .. ": could not move the players: " .. tostring(r) end
			c.t1, c.ph = now(), 3
		end
		if c.ph == 3 then
			c.dmg = c.dmg + guard()
			if now() - c.t1 < 4 then return nil end
			local v
			for _, r in ipairs(bp.soldiers(70)) do
				if r.online and r.alive ~= false and not r.kuz and r.squad == "esc_smart_terrain_7_military_4_squad" and (r.squad_n or 0) >= 2 then v = r end
			end
			if not v then return "FAIL " .. N .. ": no online soldier of the 2 man squad 4 (squads: " .. lines(bp.soldiers(70)) .. ")" end
			local vo = level.object_by_id(v.id)
			vo:kill(c.pl.obj)
			c.label = string.format("player %s killed soldier #%d of squad 4 (2 members, no hit)", tostring(c.pl.name), v.id)
			c.t_trigger, c.ph = now(), 10
			return nil
		end
		return hostile_phase(c, N, c.label, 10, 30)
	end)
end

-- ---------------------------------------------------------------------------------------------------------------- T6: entering the bridge zone
function bp.t_zone()
	local N = "bp.t_zone"
	return runner(180, N, function(c)
		if c.ph == 1 then
			if bp.flag() then return "FAIL " .. N .. ": the order flag is already set: use a fresh game" end
			if bp.vodka() then return "FAIL " .. N .. ": the vodka quest is taken: the zone is switched off by design (SoC: Kuznetsov's pass). Use a fresh game." end
			if bp.inside(INSIDE[1], INSIDE[2], INSIDE[3]) == false then return "FAIL " .. N .. ": the engine says the INSIDE spot is not in the zone: table INSIDE is wrong" end
			bp.god = true
			c.ph = 2
		end
		if c.ph == 2 then
			local r = tp(c, "tp", SAFE, nil)
			if r == nil then return nil end
			if not tp_ok(r) then return "FAIL " .. N .. ": could not move the players: " .. tostring(r) end
			c.t1, c.ph = now(), 3
		end
		if c.ph == 3 then                                   -- 8 s outside the zone: still neutral
			c.dmg = c.dmg + guard()
			if now() - c.t1 < 8 then return nil end
			if bp.flag() then return "FAIL " .. N .. ": the flag came while the players stood OUTSIDE the zone" end
			c.ph = 4
		end
		if c.ph == 4 then
			local r = tp(c, "tp2", INSIDE, nil)
			if r == nil then return nil end
			if not tp_ok(r) then return "FAIL " .. N .. ": could not move the players into the zone: " .. tostring(r) end
			c.t_trigger, c.ph = now(), 10
			local e = bp.inside(INSIDE[1], INSIDE[2], INSIDE[3])
			c.label = "players teleported into the zone (engine inside-test: " .. tostring(e) .. ")"
			return nil
		end
		return hostile_phase(c, N, c.label, 20, 30)
	end)
end

-- ---------------------------------------------------------------------------------------------------------------- T7: save / load
function bp.t_save()
	local N = "bp.t_save"
	local s = bp.soldiers(70)
	local k = counts(s)
	if not bp.flag() then return "FAIL " .. N .. ": the order flag is not set: run bp.t_hit / bp.t_zone first" end
	if k.online < 5 or k.hostile ~= k.online then return "FAIL " .. N .. ": soldiers are not all hostile yet (" .. k.hostile .. " of " .. k.online .. " online)\n" .. lines(s) end
	live.save()
	return "PASS " .. N .. ": flag set and " .. k.hostile .. " of " .. k.online .. " online army NPCs hostile; save requested (wait 5 s).\n"
		.. "NEXT: lua.ps1 -Name <n> \"live.load_last()\", wait until live.state() answers on the reloaded level, then lua.ps1 -Name <n> \"bp.t_load()\""
end

-- after live.load_last(): the flag survived and the soldiers are hostile again (they may need up to 60 s to come online and re-run their logic)
function bp.t_load()
	local N = "bp.t_load"
	return runner(150, N, function(c)
		guard()
		local s = bp.soldiers(70)
		local k = counts(s)
		local flag = bp.flag()
		if (k.online >= 5 and k.hostile == k.online and flag) or now() - c.t0 > 100 then
			local ok = flag and k.online >= 5 and k.hostile == k.online
			local why = {}
			if not flag then why[#why + 1] = "flag LOST by the load" end
			if k.online < 5 then why[#why + 1] = "only " .. k.online .. " army NPCs online (stand within 100 m of the bridge)" end
			if k.online >= 5 and k.hostile ~= k.online then why[#why + 1] = (k.online - k.hostile) .. " soldier(s) neutral after the load" end
			return verdict(ok, N, string.format("after load: flag=%s, %d of %d online army NPCs hostile (%d dead)%s", tostring(flag), k.hostile, k.online, k.dead,
				#why > 0 and ("; " .. table.concat(why, "; ")) or "")) .. "\n" .. lines(s)
		end
		return nil
	end)
end
