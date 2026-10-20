-- Hook "monolith_join": the join answer through the real RPC -> oso_choice(join) -> end_join movie -> credits request.
-- Disconnects at the end (main_menu step of the credits), so this runs alone. With -Media it plays the real movie:
-- run_scene_test.ps1 -Map coop_l11_control_monolith -Hook monolith_join -Media -Soak 200
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
local STOP = "CON_SMART_TERRAIN_13_ECOLOG_REPRESENTATIVE_AWARENESS_6_DIALOG_STOP_INFO"

local c1
c1 = { name = "oso_choice_join", id = "oso_choice", timeout = 30,
	start = function(lo)
		c1.mark = scn_t.mark()
		coop_scn_monolith.oso_join(lo, lo)               -- what the dialog phrase calls
		coop_scn_monolith._test_answer("refuse", 998)    -- later answer ignored
	end,
	check = function(lo, t)
		if scn_t.has_line("oso_choice", "END n=1", c1.mark) then
			if not ordered("oso_choice", c1.mark, FULL) then return false, "order " .. scn_t.seq("oso_choice", c1.mark) end
			if not scn_t.has_line("oso_choice", "var=join", c1.mark) then return false, "variant is not join" end
			if not any("CHOICE_IGNORED kind=refuse", c1.mark) then return false, "second answer not ignored" end
			if story_flags.has_flag(STOP) then return false, "STOP flag set on join" end
			return true, "seq " .. scn_t.seq("oso_choice", c1.mark)
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c1

local c2
c2 = { name = "end_join_movie", id = "end_join", timeout = 120,
	start = function(lo) c2.mark = c1.mark; c2.tutseen = false end,
	check = function(lo, t)
		if scn_t.has_line("end_join", "CLIENT_START", c2.mark) and game.has_active_tutorial() then c2.tutseen = true end
		if scn_t.has_line("end_join", "END n=1", c2.mark) then
			if not ordered("end_join", c2.mark, FULL) then return false, "order " .. scn_t.seq("end_join", c2.mark) end
			if not c2.tutseen then return false, "tutorial never active" end
			if not coop_scenes.played("end_join") then return false, "PLAYED not set" end
			local ev = scn_t.events("end_join", c2.mark)
			local t0, t1
			for _, e in ipairs(ev) do
				if e.tag == "CLIENT_START" then t0 = e.ms elseif e.tag == "CLIENT_END" then t1 = e.ms end
			end
			return true, string.format("seq %s; movie %.1f s; fallback=%s", scn_t.seq("end_join", c2.mark), ((t1 or 0) - (t0 or 0)) / 1000, tostring(any("FALLBACK", c2.mark) ~= nil))
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c2

local c3
c3 = { name = "end_join_credits_request", timeout = 30,
	start = function(lo) c3.mark = c1.mark end,
	check = function(lo, t)
		local id = (coop_scenes.defs.credits ~= nil) and "credits" or "mono_credits_fb"
		if scn_t.has_line(id, "REQUEST", c3.mark) then
			return true, "requested " .. id .. " after END"
		end
	end }
scn_t.cases[#scn_t.cases + 1] = c3
