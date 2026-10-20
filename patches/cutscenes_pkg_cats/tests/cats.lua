-- Test hook "cats": scenes cats_agroprom / cats_bar_arena / cats_rostok (package cutscenes_pkg_cats).
-- Run once per level (the hook picks the scene by level.name()):
--   run_scene_test.ps1 -Map coop_l03_agroprom -Hook cats -Scene cats_agroprom -Soak 220
--   run_scene_test.ps1 -Map coop_l05_bar      -Hook cats -Scene cats_bar_arena -Soak 220
--   run_scene_test.ps1 -Map coop_l06_rostok   -Hook cats -Scene cats_rostok -Soak 220
-- The trigger flags are given with story_flags.give_flag (what the arena / dialog logic does); the scene must be
-- REQUESTED BY ITS OWN TRIGGER (never by this hook, except the explicit skip / timeout cases, which re-run it).

local CFG = {
	coop_l03_agroprom = {
		id = "cats_agroprom", zone = "agr_actor_cat_scene_space_restrictor", once = true,
		walk = "agr_actor_cat_scene_1_walk", flags = { "AGR_STALKER_HELP_1_INFO" },
		given = { "AGR_THE_ORDER_TO_KILL_STALKER_SPACE_RESTRICTOR_INFO", "AGR_INVULNERABLE_OFF_INFO" },
		end_section = "sr_idle@nil", hold_ms = 15000, pos = { x = 174.345, y = 1.268, z = 10.579 },
	},
	coop_l05_bar = {
		id = "cats_bar_arena", zone = "bar_actor_cat_scene_space_restrictor", once = false,
		walk = "bar_smart_terrain_6_arena_spawn_players_1_walk", flags = { "BAR_ARNY_ARENA_SMART_TERRAIN_START_CAT_SCENE_INFO" },
		given = { "BAR_ARNY_ARENA_SMART_TERRAIN_START_ARENA_GO" },
		end_section = "sr_idle@idle_start_cat_scene_dead_mutant_idle", hold_ms = 5000, pos = { x = 151.906, y = -21.058, z = 74.876 },
	},
	coop_l06_rostok = {
		id = "cats_rostok", zone = "ros_actor_cat_scene_space_restrictor", once = true,
		walk = "ros_actor_cat_scene_1_walk", flags = { "ROS_SNIPER_SPACE_RESTRICTOR_INFO" },
		given = { "ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_INFO" },
		end_section = "sr_idle@nil", hold_ms = 15000, pos = { x = -209.320, y = 1.400, z = 119.025 },
	},
}

local C = nil   -- chosen lazily: level.name() is not valid while the script is loading

local SHOT_DIR = (os.getenv("USERPROFILE") or "C:") .. "\\Downloads\\SoC_COOP_cutscenes\\tests\\runs\\cats_shots\\"
local EXPECT = "REQUEST,GO,CLIENT_START,CLIENT_END,ACK,END"
local ERR_PATS = { "STEPERR", "PPERR", "CAMERR", "SNDERR", "TUTERR", "HOOKERR", "FNERR", "PKGERR", "TICKERR", "NOCAM" }

local ui = nil
local function ui_wrap()
	if ui then return end
	ui = { off = 0, on = 0, last = "none" }
	local o_off, o_on = xr_effects.disable_ui, xr_effects.enable_ui
	xr_effects.disable_ui = function(a, n) ui.off = ui.off + 1; ui.last = "off"; return o_off(a, n) end
	xr_effects.enable_ui = function(a, n) ui.on = ui.on + 1; ui.last = "on"; return o_on(a, n) end
end

local function errors_since(m)
	local out = {}
	for i = m, #cs_bot.lines do
		local s = cs_bot.lines[i].s
		for _, p in ipairs(ERR_PATS) do
			if string.find(s, p, 1, true) then out[#out + 1] = s end
		end
	end
	return table.concat(out, " | ")
end

local shot_pending = nil
local function shot(tag)
	local ok = pcall(function() get_console():execute("screenshot") end)
	cs_bot.log("SHOT requested " .. tag .. " ok=" .. tostring(ok))
	shot_pending = { tag = tag, at = time_global() + 2500 }
end
cs_bot.hooks.shot_cats = function(t, lo)
	if not shot_pending or time_global() < shot_pending.at then return end
	local sp = shot_pending
	shot_pending = nil
	local ok, err = pcall(function()
		local fl = getFS():file_list_open("$screenshots$", 1)
		local best = nil
		if fl then
			for i = 0, fl:Size() - 1 do best = tostring(fl:GetAt(i)) end
			fl:Free()
		end
		if best == nil then cs_bot.log("SHOT none found"); return end
		local src = io.open(getFS():update_path("$screenshots$", best), "rb")
		if not src then cs_bot.log("SHOT cannot open " .. best); return end
		local data = src:read("*a")
		src:close()
		local dst = io.open(SHOT_DIR .. sp.tag .. "_" .. best, "wb")
		if not dst then cs_bot.log("SHOT cannot write"); return end
		dst:write(data)
		dst:close()
		cs_bot.log("SHOT saved " .. sp.tag .. "_" .. best .. " bytes=" .. #data)
	end)
	if not ok then cs_bot.log("SHOT error " .. tostring(err)) end
end

local function zone() return db.zone_by_name and db.zone_by_name[C.zone] end
local function into_zone(lo)
	-- restrictor objects are only online near a player: go to the spawn position of the restrictor first
	lo:set_actor_position(vector():set(C.pos.x, C.pos.y, C.pos.z))
	local z = zone()
	return z and z:position() or vector():set(C.pos.x, C.pos.y, C.pos.z)
end
local function dist(a, b) return a:distance_to(b) end
local function case(c) scn_t.cases[#scn_t.cases + 1] = c; return c end

local function build()
	local ID = C.id

	-- 0. negative: without the trigger flag nothing may be requested (agro / rostok: standing inside the zone)
	local neg
	neg = case{ name = ID .. "_neg_no_flag", timeout = 20,
		start = function(lo)
			neg.m = scn_t.mark()
			if C.once then into_zone(lo) end   -- bar: the ltx would disable the UI on entering (original behaviour), stay out
		end,
		check = function(lo, t)
			if t < 9 then return end
			if scn_t.has_line(ID, "REQUEST", neg.m) then return false, "requested without the flag" end
			return true, "no REQUEST for 9 s without the flag"
		end }

	-- 1. party hold, tested on the trigger function with a fake 2 player context (one inside, one far away)
	local hd
	hd = case{ name = ID .. "_party_hold", timeout = 10,
		start = function(lo)
			into_zone(lo)
			hd.t_start = time_global()
			hd.res = nil
		end,
		check = function(lo, t)
			if hd.res == nil then
				if zone() == nil then
					if t > 8 then return false, "restrictor object never came online at its spawn position" end
					return
				end
				if not zone():inside(lo:position()) then
					if t > 8 then return false, "player not inside the restrictor at its spawn position" end
					return
				end
				hd.res = {}
				hd.run()
			end
			return hd.finish()
		end }
	hd.run = function()
		local lo = cs_bot.local_object()
		do
			local far = vector():set(0, -500, 0)
			local fake = { position = function(self) return far end }
			local def = coop_scenes.defs[ID]
			local flags = {}
			for _, f in ipairs(C.flags) do flags[f] = true end
			local t0 = time_global()
			local function ctx(now, two)
				return {
					now = now,
					players = function() if two then return { lo, fake } else return { lo } end end,
					flag = function(n) return flags[n] == true end,
				}
			end
			hd.res.alone = def.trigger(ctx(t0, false))        -- everybody inside: immediately
			hd.res.two_t0 = def.trigger(ctx(t0, true))        -- one of two inside: held
			hd.res.two_mid = def.trigger(ctx(t0 + C.hold_ms - 1000, true))
			hd.res.two_end = def.trigger(ctx(t0 + C.hold_ms + 100, true))
			-- leave the hold state clean for the real run (nobody inside)
			local nobody = { now = t0, players = function() return { fake } end, flag = function(n) return flags[n] == true end }
			def.trigger(nobody)
		end
	end
	hd.finish = function()
		do
			local r = hd.res
			if r.alone ~= true then return false, "trigger not true with everybody inside" end
			if r.two_t0 ~= false then return false, "trigger true at t0 with 1 of 2 inside" end
			if r.two_mid ~= false then return false, "trigger true before the hold time" end
			if r.two_end ~= true then return false, "trigger not true after the hold time" end
			return true, string.format("1 of 2 inside: held, released after %d ms; all inside: immediate", C.hold_ms)
		end
	end

	-- 2. positive: real flags + a player inside the real restrictor start the scene through the director's trigger
	local pos
	pos = case{ name = ID, timeout = 140,
		start = function(lo)
			ui_wrap()
			pos.m = scn_t.mark()
			pos.ui0 = { off = ui.off, on = ui.on }
			pos.shot = false
			pos.checked_pos = false
			for _, f in ipairs(C.flags) do story_flags.give_flag(f) end
			pos.zpos = into_zone(lo)
		end,
		check = function(lo, t)
			if pos.z_id == nil and zone() then pos.z_id = zone():id() end
			local cs = scn_t.has_line(ID, "CLIENT_START", pos.m)
			if cs and not pos.checked_pos and time_global() - cs.ms >= 1000 then
				pos.checked_pos = true
				local ok, wp = pcall(function() return patrol(C.walk):point(0) end)
				if ok then pos.dwalk = dist(lo:position(), wp) end
			end
			if cs and not pos.shot and (time_global() - cs.ms) >= 4000 then
				pos.shot = true
				shot(ID)
			end
			if not scn_t.has_line(ID, "END n=1", pos.m) then return end
			local seq = scn_t.seq(ID, pos.m)
			local e = errors_since(pos.m)
			if e ~= "" then return false, "errors: " .. e end
			if seq ~= EXPECT then return false, "sequence " .. seq end
			if not scn_t.has_line(ID, "END n=1 reason=all_acked", pos.m) then return false, "END reason not all_acked" end
			if not coop_scenes.played(ID) then return false, "PLAYED not set" end
			if ui.last ~= "on" then return false, "ui left off" end
			if ui.off - pos.ui0.off < 1 or ui.on - pos.ui0.on < 1 then return false, "ui_off/ui_on not both called" end
			if pos.dwalk == nil then return false, "walk point path not readable" end
			if pos.dwalk > 3.5 then return false, string.format("player %.1f m from the walk point during the flight", pos.dwalk) end
			local ev = scn_t.events(ID, pos.m)
			local t0, t1
			for _, x in ipairs(ev) do
				if x.tag == "CLIENT_START" then t0 = x.ms elseif x.tag == "CLIENT_END" then t1 = x.ms end
			end
			pos.len = ((t1 or 0) - (t0 or 0)) / 1000
			pos.stage = 1
			pos.t_end = time_global()
			return nil
		end,
		-- phase 2 handled in "after" cases below; this case finishes when phase 1 is verified
	}
	-- the above returns nil forever after END (stage=1); wrap check so it finishes after the ltx / flag checks
	local base_check = pos.check
	pos.check = function(lo, t)
		if pos.stage == nil then return base_check(lo, t) end
		if time_global() - pos.t_end < 3000 then return end   -- let the ltx see PLAYED
		for _, f in ipairs(C.given) do
			if not story_flags.has_flag(f) then return false, "flag not given: " .. f end
		end
		local st = db.storage[pos.z_id]
		local sec = st and st.active_section
		if sec ~= C.end_section then return false, "restrictor logic is in " .. tostring(sec) .. ", expected " .. C.end_section end
		return true, string.format("seq=%s camera %.1f s; %.1f m from walk point; flags %s given; ltx section %s; ui off=%d on=%d",
			EXPECT, pos.len, pos.dwalk, table.concat(C.given, ","), sec, ui.off - pos.ui0.off, ui.on - pos.ui0.on)
	end

	-- 3. no replay of a finished once scene / re-arm of the repeatable arena
	local nr
	if C.once then
		nr = case{ name = ID .. "_no_replay", timeout = 20,
			start = function(lo)
				nr.m = scn_t.mark()
				nr.refused = (coop_scenes.request(ID) == false)
				into_zone(lo)
			end,
			check = function(lo, t)
				if t < 8 then return end
				if scn_t.has_line(ID, "REQUEST", nr.m) or scn_t.has_line(ID, "GO n=2", nr.m) then return false, "scene replayed" end
				if not nr.refused then return false, "request() accepted after PLAYED" end
				return true, "no second REQUEST/GO in 8 s, flag still set, player inside, request() refused"
			end }
	else
		nr = case{ name = ID .. "_no_replay_until_rearm", timeout = 20,
			start = function(lo) nr.m = scn_t.mark(); into_zone(lo) end,
			check = function(lo, t)
				if t < 8 then return end
				if scn_t.has_line(ID, "REQUEST", nr.m) then return false, "scene replayed while START_ARENA_GO is set" end
				return true, "no second REQUEST in 8 s while START_ARENA_GO is set"
			end }
		local rr
		rr = case{ name = ID .. "_second_round", timeout = 120,
			start = function(lo)
				rr.m = scn_t.mark()
				-- what the arena logic does when a fight is over, then the next fight announces the cat scene again
				story_flags.disable_flag("BAR_ARNY_ARENA_SMART_TERRAIN_START_ARENA_GO")
				story_flags.disable_flag("BAR_ARNY_ARENA_SMART_TERRAIN_START_CAT_SCENE_INFO")
				rr.armed = time_global() + 1500
			end,
			check = function(lo, t)
				if rr.armed and time_global() >= rr.armed then
					rr.armed = nil
					story_flags.give_flag("BAR_ARNY_ARENA_SMART_TERRAIN_START_CAT_SCENE_INFO")
				end
				if scn_t.has_line(ID, "END n=2", rr.m) then
					local seq = scn_t.seq(ID, rr.m)
					if seq ~= EXPECT then return false, "sequence " .. seq end
					if not story_flags.has_flag("BAR_ARNY_ARENA_SMART_TERRAIN_START_ARENA_GO") then return false, "ARENA_GO not given after round 2" end
					return true, "second round played by the trigger (n=2): " .. seq
				end
			end }
	end

	-- 4. late joiner / reload baseline
	local lj
	lj = case{ name = ID .. "_late_join", timeout = 20,
		start = function(lo)
			lj.m = scn_t.mark()
			coop_scenes._debug_reset_baseline()
		end,
		check = function(lo, t)
			if t < 5 then return end
			if scn_t.has_line(ID, "CLIENT_START", lj.m) then return false, "client replayed after baseline reset" end
			return true, "no CLIENT_START after baseline reset (" .. scn_t.seq(ID, lj.m) .. ")"
		end }

	-- 5. input back
	local mv
	mv = case{ name = ID .. "_input_back", timeout = 10,
		start = function(lo)
			local p = lo:position()
			mv.before = vector():set(p.x, p.y, p.z)
			lo:set_actor_position(vector():set(p.x + 2, p.y + 0.3, p.z))
		end,
		check = function(lo, t)
			if t < 2 then return end
			if ui.last ~= "on" then return false, "ui not on" end
			if scn_t.moved(lo, mv.before, 1.5) then return true, "moved 2 m, ui on" end
			return false, "actor did not move"
		end }

	-- 6. skip by anyone: a second run is ended at once (test-only: once=false to allow a re-run)
	local sk
	sk = case{ name = ID .. "_skip_any", timeout = 60,
		start = function(lo)
			sk.m = scn_t.mark()
			sk.sent = false
			sk.shot = false
			sk.keep = coop_scenes.defs[ID].once
			coop_scenes.defs[ID].once = false
			-- the arena trigger would also re-fire by itself; the hook request is the explicit second run
			sk.req = coop_scenes.request(ID)
			if not sk.req then error("second request refused") end
		end,
		check = function(lo, t)
			local go = scn_t.has_line(ID, "GO n=", sk.m)
			if go and scn_t.has_line(ID, "CLIENT_START", sk.m) and not sk.sent then
				if time_global() - go.ms < 3000 then return end
				sk.sent = true
				sk.sent_at = time_global()
				coop_scenes.skip_local()
				return
			end
			local en = scn_t.has_line(ID, "END n=", sk.m)
			if en then
				coop_scenes.defs[ID].once = sk.keep
				if not string.find(en.line, "reason=skipped", 1, true) then return false, "not skipped: " .. en.line end
				local ms = en.ms - (sk.sent_at or en.ms)
				if ms > 3000 then return false, "skip took " .. ms .. " ms" end
				if not scn_t.has_line(ID, "CLIENT_END actor=" .. tostring(LocalActor()) .. " reason=skip", sk.m) then return false, "client did not end with reason=skip: " .. scn_t.seq(ID, sk.m) end
				if scn_t.has_line(ID, "SKIP_VOTE", sk.m) == nil then return false, "no SKIP_VOTE line" end
				return true, "skip by one player ended the scene on all machines in " .. ms .. " ms; " .. scn_t.seq(ID, sk.m)
			end
			if t > 50 then coop_scenes.defs[ID].once = sk.keep end
		end,
	}

	-- 7. wait-for-all with a timeout: acks blocked -> END reason=timeout at the deadline, game continues
	local to
	to = case{ name = ID .. "_timeout", timeout = 60,
		start = function(lo)
			to.m = scn_t.mark()
			local d = coop_scenes.defs[ID]
			to.keep = { once = d.once, length_ms = d.length_ms, grace_ms = d.grace_ms }
			d.once = false; d.length_ms = 2500; d.grace_ms = 2500
			coop_scenes.dbg.no_ack = true
			if not coop_scenes.request(ID) then error("request refused") end
			to.t0 = time_global()
		end,
		check = function(lo, t)
			local en = scn_t.has_line(ID, "END n=", to.m)
			if not en then return end
			local d = coop_scenes.defs[ID]
			d.once = to.keep.once; d.length_ms = to.keep.length_ms; d.grace_ms = to.keep.grace_ms
			coop_scenes.dbg.no_ack = false
			if not string.find(en.line, "reason=timeout", 1, true) then return false, "not timeout: " .. en.line end
			local dt = (en.ms - to.t0) / 1000
			if dt < 4.0 or dt > 8.0 then return false, string.format("timeout after %.1f s, expected ~5 s", dt) end
			return true, string.format("END reason=timeout after %.1f s with the ack blocked", dt)
		end }
end

cs_bot.hooks.cats_build = function(t, lo)
	cs_bot.hooks.cats_build = nil
	C = CFG[level.name()]
	if C == nil then
		cs_bot.log("cats hook: level " .. tostring(level.name()) .. " is not one of the cats levels")
		return
	end
	cs_bot.log("cats hook: building cases for " .. C.id)
	build()
end
