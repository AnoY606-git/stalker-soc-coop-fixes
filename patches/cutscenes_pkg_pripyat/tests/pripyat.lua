-- Hook "pripyat": real trigger = walk into the stadium box; flyover with the real pri_fly_to_aes.anm; final teleport.
-- Run: run_scene_test.ps1 -Map coop_l10_pripyat -Hook pripyat -Media -Soak 120
local function ordered(id, from, tags)
	local pos = 1
	for _, e in ipairs(scn_t.events(id, from)) do
		if e.tag == tags[pos] then pos = pos + 1 end
	end
	return pos > #tags
end
local function any(pat, from)
	for i = (from or 1), #cs_bot.lines do
		if string.find(cs_bot.lines[i].s, pat, 1, true) then return cs_bot.lines[i] end
	end
	return nil
end
local FULL = { "REQUEST", "GO", "CLIENT_START", "CLIENT_END", "ACK", "END" }
local EFF = { x = 31.4487648010254, y = 1.5703592300415, z = 279.992431640625 }
local TELE = { x = 33.4589729309082, y = -0.681340217590332, z = 463.037689208984 }
local function dist(p, q) return math.sqrt((p.x - q.x) ^ 2 + (p.y - q.y) ^ 2 + (p.z - q.z) ^ 2) end

-- outside the box: nothing may happen (box z 261.5 .. 271.2; stand 17 m before it)
local c0
c0 = { name = "pri_outside_no_trigger", timeout = 14,
	start = function(lo) c0.mark = scn_t.mark(); scn_t.teleport(31.3, 3.2, 245.0) end,
	check = function(lo, t)
		if scn_t.has_line("pri_stadium_fly", "REQUEST", c0.mark) then return false, "triggered outside the box" end
		if t > 9 then return true, "no request in 9 s outside the box" end
	end }
scn_t.cases[#scn_t.cases + 1] = c0

local c1
c1 = { name = "pri_stadium_fly", id = "pri_stadium_fly", timeout = 120,
	start = function(lo)
		c1.mark = scn_t.mark(); c1.mind = 1e9
		c1.lvl = level.name()
		scn_t.teleport(31.285, 3.1, 266.3)           -- box centre
	end,
	check = function(lo, t)
		if c1.lvl ~= "coop_l10_pripyat" then return false, "wrong level " .. tostring(c1.lvl) end
		if scn_t.has_line("pri_stadium_fly", "CLIENT_START", c1.mark) and not scn_t.has_line("pri_stadium_fly", "CLIENT_END", c1.mark) then
			local d = dist(lo:position(), EFF)
			if d < c1.mind then c1.mind = d end
		end
		if scn_t.has_line("pri_stadium_fly", "END n=1", c1.mark) then
			if not ordered("pri_stadium_fly", c1.mark, FULL) then return false, "order " .. scn_t.seq("pri_stadium_fly", c1.mark) end
			if any("NOCAM", c1.mark) then return false, "pri_fly_to_aes.anm missing" end
			if not coop_scenes.played("pri_stadium_fly") then return false, "PLAYED not set" end
			if c1.mind > 2.5 then return false, string.format("never at eff point (min %.1f m)", c1.mind) end
			local ev = scn_t.events("pri_stadium_fly", c1.mark)
			local t0, t1
			for _, e in ipairs(ev) do
				if e.tag == "CLIENT_START" then t0 = e.ms elseif e.tag == "CLIENT_END" then t1 = e.ms end
			end
			c1.cam = ((t1 or 0) - (t0 or 0)) / 1000
			return true, string.format("seq %s; flight %.1f s; min dist to eff point %.2f", scn_t.seq("pri_stadium_fly", c1.mark), c1.cam, c1.mind)
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c1

local c2
c2 = { name = "pri_final_position_and_input", timeout = 12,
	start = function(lo)
		c2.d = dist(lo:position(), TELE)
		local p = lo:position()
		c2.before = vector():set(p.x, p.y, p.z)
		lo:set_actor_position(vector():set(p.x + 2, p.y + 0.3, p.z))
	end,
	check = function(lo, t)
		if t < 2 then return end
		if c2.d > 3.0 then return false, string.format("ended %.1f m from pri_tele_point", c2.d) end
		if scn_t.moved(lo, c2.before, 1.5) then return true, string.format("ended %.2f m from pri_tele_point; input back", c2.d) end
		return false, "actor did not move"
	end }
scn_t.cases[#scn_t.cases + 1] = c2

-- once: standing in the box again must not replay
local c3
c3 = { name = "pri_no_replay", timeout = 14,
	start = function(lo) c3.mark = scn_t.mark(); scn_t.teleport(31.285, 3.1, 266.3) end,
	check = function(lo, t)
		if scn_t.has_line("pri_stadium_fly", "REQUEST", c3.mark) then return false, "replayed" end
		if t > 9 then return true, "no replay in 9 s" end
	end }
scn_t.cases[#scn_t.cases + 1] = c3
