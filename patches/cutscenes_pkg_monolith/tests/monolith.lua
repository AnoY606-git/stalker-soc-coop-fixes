-- Hook "monolith": generators -> monolith_off -> oso_arrival (real triggers), then the refuse answer through the real RPC.
-- Run: run_scene_test.ps1 -Map coop_l11_control_monolith -Hook monolith -Media -Soak 150
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
local OSO = { x = 17.8031311035156, y = -43.6672286987305, z = 31.2826137542725 }
local LOOK = { x = 17.454776763916, y = -41.4733619689941, z = 25.9469795227051 }
local STOP = "CON_SMART_TERRAIN_13_ECOLOG_REPRESENTATIVE_AWARENESS_6_DIALOG_STOP_INFO"

-- 1. the real trigger: all six generator flags
local c1
c1 = { name = "monolith_off_trigger", id = "monolith_off", timeout = 90,
	start = function(lo)
		c1.mark = scn_t.mark()
		c1.lvl = level.name()
		for i = 1, 6 do scn_t.give_flag("CON_MONOLITH_GENERATOR_" .. i .. "_INFO") end
	end,
	check = function(lo, t)
		if c1.lvl ~= "coop_l11_control_monolith" then return false, "wrong level " .. tostring(c1.lvl) end
		if scn_t.has_line("monolith_off", "END n=1", c1.mark) then
			if not ordered("monolith_off", c1.mark, FULL) then return false, "order " .. scn_t.seq("monolith_off", c1.mark) end
			if not coop_scenes.played("monolith_off") then return false, "PLAYED not set" end
			if any("NOPPE", c1.mark) then return false, "monolith_off.ppe missing" end
			if any("NOSND", c1.mark) then return false, "sound missing: " .. any("NOSND", c1.mark).s end
			local ev = scn_t.events("monolith_off", c1.mark)
			local t0, t1
			for _, e in ipairs(ev) do
				if e.tag == "CLIENT_START" then t0 = e.ms elseif e.tag == "CLIENT_END" then t1 = e.ms end
			end
			return true, string.format("seq %s; %.1f s", scn_t.seq("monolith_off", c1.mark), ((t1 or 0) - (t0 or 0)) / 1000)
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c1

-- 2. arrival camera starts by itself after monolith_off END
local c2
c2 = { name = "oso_arrival_chain", id = "oso_arrival", timeout = 90,
	start = function(lo) c2.mark = scn_t.mark(); c2.mind = 1e9; c2.dotmax = -1 end,
	check = function(lo, t)
		if scn_t.has_line("oso_arrival", "CLIENT_START", c2.mark) and not scn_t.has_line("oso_arrival", "CLIENT_END", c2.mark) then
			local p = lo:position()
			local d = math.sqrt((p.x - OSO.x) ^ 2 + (p.y - OSO.y) ^ 2 + (p.z - OSO.z) ^ 2)
			if d < c2.mind then c2.mind = d end
			local dir = lo:direction()
			local lx, lz = LOOK.x - OSO.x, LOOK.z - OSO.z
			local ll = math.sqrt(lx * lx + lz * lz)
			local dl = math.sqrt(dir.x * dir.x + dir.z * dir.z)
			if dl > 0 then
				local dot = (dir.x * lx + dir.z * lz) / (ll * dl)
				if dot > c2.dotmax then c2.dotmax = dot end
			end
		end
		if scn_t.has_line("oso_arrival", "END n=1", c2.mark) then
			if not ordered("oso_arrival", c2.mark, FULL) then return false, "order " .. scn_t.seq("oso_arrival", c2.mark) end
			if any("NOCAM", c2.mark) then return false, "oso_cam.anm missing" end
			if c2.mind > 2.5 then return false, string.format("never near oso_actor_walk (min %.1f m)", c2.mind) end
			local ev = scn_t.events("oso_arrival", c2.mark)
			local t0, t1
			for _, e in ipairs(ev) do
				if e.tag == "CLIENT_START" then t0 = e.ms elseif e.tag == "CLIENT_END" then t1 = e.ms end
			end
			return true, string.format("seq %s; cam %.1f s; min dist %.2f m; look dot %.3f", scn_t.seq("oso_arrival", c2.mark), ((t1 or 0) - (t0 or 0)) / 1000, c2.mind, c2.dotmax)
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c2

-- 3. input is back
local c3
c3 = { name = "monolith_input_back", timeout = 12,
	start = function(lo)
		local p = lo:position()
		c3.before = vector():set(p.x, p.y, p.z)
		lo:set_actor_position(vector():set(p.x + 2, p.y + 0.3, p.z))
		c3.tut = game.has_active_tutorial()
	end,
	check = function(lo, t)
		if t < 2 then return end
		if c3.tut then return false, "tutorial still active" end
		if scn_t.moved(lo, c3.before, 1.5) then return true, "moved" end
		return false, "actor did not move"
	end }
scn_t.cases[#scn_t.cases + 1] = c3

-- 4. refuse through the real RPC (client phrase action -> server): one variant for everyone, STOP flag by the server
local c4
c4 = { name = "oso_choice_refuse", id = "oso_choice", timeout = 40,
	start = function(lo)
		c4.mark = scn_t.mark()
		c4.flag0 = story_flags.has_flag(STOP)
		coop_scn_monolith.oso_refuse(lo, lo)                 -- what the dialog phrase calls
		coop_scn_monolith._test_answer("join", 999)          -- a second, later answer must be ignored
	end,
	check = function(lo, t)
		if scn_t.has_line("oso_choice", "END n=1", c4.mark) then
			if c4.flag0 then return false, "STOP flag was already set before the answer" end
			if not ordered("oso_choice", c4.mark, FULL) then return false, "order " .. scn_t.seq("oso_choice", c4.mark) end
			if not scn_t.has_line("oso_choice", "var=refuse", c4.mark) then return false, "variant is not refuse" end
			if coop_scenes.variant("oso_choice") ~= "refuse" then return false, "variant flag " .. tostring(coop_scenes.variant("oso_choice")) end
			if not any("CHOICE_IGNORED kind=join", c4.mark) then return false, "second answer not ignored" end
			if not any("CHOICE_SEEN var=refuse", c4.mark) then return false, "client did not see the variant" end
			if story_flags.has_flag(STOP) then
				if scn_t.has_line("end_join", "REQUEST", c4.mark) then return false, "end_join requested after refuse" end
				return true, "seq " .. scn_t.seq("oso_choice", c4.mark) .. "; STOP flag set by server; no end_join"
			end
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c4
