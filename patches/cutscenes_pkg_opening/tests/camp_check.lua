--@qa_lib
-- Only the story character starts in Sidorovich's bunker; every other player is moved ONCE to the rookie village campfire (test only, never shipped).
-- ONE listen-host run per mode (the host is the only player a single run has):
--   STORY mode (default): the host IS the Marked One (lobby skin 1, section actor_the_main_character): he stays in the bunker, nobody is moved,
--     Sidorovich's intro is requested for him.
--   NON-STORY mode (environment variable CAMP_NONSTORY=1 in the shell that starts run_coop.ps1): the hook gives the test flag COOP_OPEN_TEST_NONSTORY at load,
--     so the host counts as a NON-story player: he must be moved to a campfire spot (3.5 to 5 m from the fire, one of CAMP_SPOTS), get both start tasks,
--     get NO Sidorovich intro / placement, and after his own death + respawn he must NOT be moved again (flag COOP_OPEN_CAMP_<NAME>).
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner campchk -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 120 -ResultDir <dir>
-- Lines in qa_events.log:  CAMPCHK ...  (and BOT SOCOPEN CAMP ... / BOT SCENE opening PENDING ... copied from the scripts' own log calls)
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("CAMPCHK " .. s) end

local NONSTORY = (safe(function() return os.getenv("CAMP_NONSTORY") end) == "1")
local FIRE = { x = -206.9, y = -19.6, z = -140.1 }
local BUNKER = { x = -246.4, y = -24.8, z = -134.4 }

-- the hook is appended to several scripts (each copy has its own locals): share the log list through _G so the copy that checks sees what the last copy's cs_bot recorded
local said = rawget(_G, "__camp_said") or {}
rawset(_G, "__camp_said", said)
rawset(_G, "cs_bot", { log = function(s) said[#said + 1] = s; qa.event("BOT " .. tostring(s)) end })
local function saw(pat)
	for i = 1, #said do if string.find(said[i], pat, 1, true) then return said[i] end end
	return nil
end

local function flat(a, b) return math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2) end

local function report(tag)
	local lo = L.local_player()
	if lo == nil then ev(tag .. " no local player") return nil end
	local p, d = lo:position(), lo:direction()
	local df, db_ = flat(p, FIRE), flat(p, BUNKER)
	local dx, dz = FIRE.x - p.x, FIRE.z - p.z
	local len = math.max(math.sqrt(dx * dx + dz * dz), 0.001)
	local dot = (dx * d.x + dz * d.z) / len / math.max(math.sqrt(d.x * d.x + d.z * d.z), 0.001)
	ev(string.format("%s pos=%.2f,%.2f,%.2f fire_dist=%.2f bunker_dist=%.2f facing_fire_dot=%.2f section=%s", tag, p.x, p.y, p.z, df, db_, dot, tostring(lo:section())))
	return { x = p.x, y = p.y, z = p.z, fire = df, bunker = db_, dot = dot, obj = lo }
end

local function tasks(lo)
	local n = 0
	for _, id in ipairs({ "esc_start_main_quest_task", "esc_start_talk_to_the_sidorovich_quest_task" }) do
		local t = lo and safe(function() return lo:get_task(id, true) end)
		ev("task " .. id .. "=" .. (t ~= nil and "yes" or "no"))
		if t ~= nil then n = n + 1 end
	end
	return n
end

local function camp_flag(lo)
	return "COOP_OPEN_CAMP_" .. string.gsub(string.upper(lo:name()), "[^A-Z0-9]", "_")
end

-- the test flag must exist before the host's first settle (2.5 s after he left the lobby)
if NONSTORY then
	qa.once("camp_flag", function(t, lo)
		if safe(OnServer) then pcall(story_flags.give_flag, "COOP_OPEN_TEST_NONSTORY"); ev("test flag COOP_OPEN_TEST_NONSTORY given (host counts as non-story)") end
	end)
end

qa.once("camp_run", function(t, lo)
	local phase = L.state_get("camp_phase", 1)
	ev("mode=" .. (NONSTORY and "NON-STORY" or "STORY") .. " phase=" .. tostring(phase))
	if phase == 2 then
		-- after the death: the respawn must not move him again
		L.task("camp_phase2", {
			function(c) return L.wait(8) end,
			function(c)
				local r = report("after respawn")
				qa.assert("respawn: NOT moved to the campfire again (still at the bunker spawn points)", r ~= nil and r.bunker < 8 and r.fire > 20, r and string.format("bunker %.1f fire %.1f", r.bunker, r.fire) or "no player")
				qa.assert("respawn: flag still set", r ~= nil and L.flag_has(camp_flag(r.obj)))
				return L.screenshot("camp_after_respawn")
			end,
		})
		return
	end
	L.task("camp_phase1", {
		function(c) return L.wait(NONSTORY and 14 or 10) end,
		function(c)
			local r = report("t+" .. (NONSTORY and 14 or 10))
			if r == nil then return L.now(false) end
			if NONSTORY then
				local moved = saw("CAMP MOVED")
				ev("log: " .. tostring(moved))
				qa.assert("non-story: moved to the campfire (3.5 to 5 m from the fire)", r.fire >= 3.5 and r.fire <= 5.0, string.format("%.2f", r.fire))
				qa.assert("non-story: the CAMP MOVED log line exists", moved ~= nil)
				qa.assert("non-story: floor level of the village (y -20.5 to -19.5)", r.y > -20.6 and r.y < -19.5, string.format("%.2f", r.y))
				qa.assert("non-story: NOT in Sidorovich's bunker", r.bunker > 20, string.format("%.1f", r.bunker))
				qa.assert("non-story: the per player flag is set", L.flag_has(camp_flag(r.obj)))
				qa.assert("non-story: no Sidorovich intro was queued for him (no PENDING line)", saw("PENDING") == nil, tostring(saw("PENDING")))
				qa.assert("non-story: placement into the bunker never ran (no PLACED line)", saw("PLACED") == nil, tostring(saw("PLACED")))
				ev("facing the fire (dot) = " .. string.format("%.2f", r.dot) .. " (turn of a server side set_actor_direction: logged, not asserted)")
			else
				qa.assert("story: still in the room in front of Sidorovich's counter (bunker)", r.bunker < 4.0 and r.fire > 20, string.format("bunker %.1f fire %.1f", r.bunker, r.fire))
				qa.assert("story: nobody was moved (no CAMP MOVED / CAMP MARKED)", saw("CAMP MOVED") == nil and saw("CAMP MARKED") == nil, tostring(saw("CAMP MOVED")))
				qa.assert("story: his Sidorovich intro was queued (PENDING line)", saw("PENDING") ~= nil)
				qa.assert("story: no per player camp flag", not L.flag_has(camp_flag(r.obj)))
			end
			qa.assert("the start tasks are given (per player tick)", tasks(r.obj) >= 1)
			return L.screenshot(NONSTORY and "camp_nonstory" or "camp_story")
		end,
		function(c)
			if not NONSTORY then return L.done(true) end
			-- the death + respawn phase (non-story only): the VM restarts, phase 2 runs in the new VM
			L.state_set("camp_phase", 2)
			return L.kill_player(nil)
		end,
		-- in a listen run the VM does NOT restart on the death (no second INSTALL line), so camp_run never runs again: check here too
		-- (when the VM does restart, this task is gone and phase 2 above does the check instead)
		function(c) return L.wait(14) end,
		function(c)
			local r = report("after respawn")
			local n = 0
			for i = 1, #said do if string.find(said[i], "CAMP MOVED", 1, true) then n = n + 1 end end
			-- the harness respawn puts him back near where he died (the campfire), not at the bunker: so the proof is "no second CAMP MOVED line"
			qa.assert("respawn: NOT moved to the campfire again (exactly one CAMP MOVED line in total)", n == 1, tostring(n) .. " CAMP MOVED lines")
			qa.assert("respawn: flag still set", r ~= nil and L.flag_has(camp_flag(r.obj)))
		end,
	})
end)
