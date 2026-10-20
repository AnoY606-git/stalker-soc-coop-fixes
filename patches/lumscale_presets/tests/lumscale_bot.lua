-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): in-game bot for patches/lumscale_presets. Appended to xr_conditions.dscript of a TEST addon copy.
-- Listen server + one local player. Spawns hands-free (game.respawn_dead_players), then for every spot (village day, Sidorovich's
-- bunker, village night) teleports the player, sets the game time, applies every preset through lumscale_presets.apply(), reads the
-- console variables back, and takes an engine screenshot. Everything goes to $logs$\lum_bot.log (PASS/FAIL/SHOT lines).
-- Plan comes from $app_data_root$\lum_plan.txt (key = value): presets=default,soc,bright  spots=village,bunker,night  tag=r4
-------------------------------------------------------------------------------------------------------
lum_bot = lum_bot or {}
local B = lum_bot
B.t0 = nil
B.last = 0
B.respawn_at = 0
B.spawned_at = nil
B.tl = nil
B.idx = 1
B.cfg = { presets = "default,soc,bright", spots = "village,bunker,night", tag = "x", hours = "12,1" }
B.pos = {}

local function now_s() return (time_global() - (B.t0 or time_global())) / 1000 end

function B.log(s)
	pcall(function()
		local f = io.open(getFS():update_path("$logs$", "lum_bot.log"), "a")
		if f then
			f:write(string.format("[%6.1f] %s\n", now_s(), tostring(s)))
			f:close()
		end
	end)
end

local function read_cfg()
	pcall(function()
		local f = nil
		for _, root in ipairs({"$app_data_root$", "$logs$"}) do
			local pth = getFS():update_path(root, "lum_plan.txt")
			f = io.open(pth, "r")
			B.log("PLANPATH " .. tostring(pth) .. " open=" .. tostring(f ~= nil))
			if f then break end
		end
		if not f then B.log("PLAN file not found") return end
		for line in f:lines() do
			local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
			if k then B.cfg[k] = v end
		end
		f:close()
	end)
end

local function split(s)
	local out = {}
	for w in string.gmatch(s, "[^,]+") do out[#out + 1] = w end
	return out
end

local function local_object()
	local ok, lo = pcall(function() return level.object_by_id(LocalActor()) end)
	return ok and lo or nil
end

local function cvar_line()
	local names = { "r2_sun_lumscale", "r2_sun_lumscale_amb", "r2_sun_lumscale_hemi", "r2_tonemap", "r2_tonemap_middlegray",
	                "r2_tonemap_adaptation", "r2_tonemap_lowlum", "r2_tonemap_amount" }
	local parts = {}
	for _, n in ipairs(names) do
		parts[#parts + 1] = n .. "=" .. tostring(lumscale_presets.get_cvar(n))
	end
	return table.concat(parts, " ")
end

local function find_trader()
	local best = nil
	pcall(function()
		for id, st in pairs(db.storage) do
			local o = st.object
			if o ~= nil then
				local n = o:name()
				if string.find(n, "trader", 1, true) then
					local p = o:position()
					B.log(string.format("TRADER-CAND %s id=%d pos=%.2f,%.2f,%.2f", n, id, p.x, p.y, p.z))
					if string.find(n, "sidorovich", 1, true) then best = o end
				end
			end
		end
	end)
	return best
end

local function teleport(lo, x, y, z, dir)
	local p = vector():set(x, y, z)
	local ok, err = pcall(function()
		local vid = level.vertex_id(p)
		lo:set_actor_position(level.vertex_position(vid))
	end)
	B.log(string.format("TELEPORT %.1f,%.1f,%.1f %s", x, y, z, ok and "ok" or tostring(err)))
	if dir ~= nil then
		pcall(function() lo:set_actor_direction(dir) end)
	end
end

local function set_hour(h)
	local cur = level.get_time_hours()
	local d = (h - cur) % 24
	pcall(function() level.set_time_factor(0.0) end)
	pcall(function() level.change_game_time(0, d, 0) end)
	local okw, w = pcall(function() return level.get_weather() end)
	B.log(string.format("TIME was %d now %d (wanted %d) weather=%s", cur, level.get_time_hours(), h, tostring(w)))
end

local function shot(tag)
	pcall(function() get_console():execute("screenshot") end)
	pcall(function() get_console():execute("flush") end)
	B.log("SHOT " .. tag)
end

local function build_timeline(lo)
	local tl = {}
	local t = 0
	local presets = split(B.cfg.presets)
	local spots = split(B.cfg.spots)
	local hours = split(B.cfg.hours)
	local tag = B.cfg.tag
	local sp = lo:position()
	local vd = lo:direction()
	B.pos.village = { sp.x, sp.y, sp.z, math.atan2(-vd.x, vd.z) }
	local trader = find_trader()
	if trader ~= nil then
		local p = trader:position()
		local d = trader:direction()
		B.log(string.format("SIDOR dir=%.2f,%.2f,%.2f", d.x, d.y, d.z))
		local dist = tonumber(B.cfg.bdist or "2.5")
		B.pos.bunker = { p.x + d.x * dist, p.y, p.z + d.z * dist, math.atan2(d.x, -d.z) }
	end
	B.log(string.format("BASE village=%.1f,%.1f,%.1f dir=%.3f", sp.x, sp.y, sp.z, B.pos.village[4]))
	-- startup check: the game_cl.dscript hook must have applied the choice from lumscale_preset.txt at game start
	tl[#tl + 1] = { t = 1, fn = function()
		B.log("START-STATE " .. cvar_line())
		B.log("START-CHOICE " .. tostring(lumscale_presets.read_choice()))
		pcall(function() get_console():execute("hud_draw off") end)
		pcall(function() get_console():execute("hud_weapon off") end)
	end }
	t = 2
	for _, spot in ipairs(spots) do
		local P = B.pos[spot == "night" and "village" or spot]
		local hour = (spot == "night") and tonumber(hours[2] or 1) or tonumber(hours[1] or 12)
		if P ~= nil then
			local tt = t
			tl[#tl + 1] = { t = tt, fn = function()
				teleport(lo, P[1], P[2], P[3], B.dir and B.dir[spot] or P[4])
				if spot == "bunker" then
					-- Sidorovich's bunker: stand next to him, look at him
				end
				set_hour(hour)
			end }
			t = t + 12
			for _, pr in ipairs(presets) do
				local ttt = t
				tl[#tl + 1] = { t = ttt, fn = function()
					local ok = lumscale_presets.apply(pr, false)
					B.log("APPLY " .. pr .. " ret=" .. tostring(ok))
				end }
				t = t + 7
				tl[#tl + 1] = { t = t, fn = function()
					B.log(string.format("READBACK spot=%s preset=%s %s", spot, pr, cvar_line()))
					shot(string.format("%s_%s_%s", tag, spot, pr))
				end }
				t = t + 2
			end
		else
			B.log("SKIP spot " .. spot .. " (no position)")
		end
	end
	-- "off" must change nothing: set a marker value, apply off, value must stay
	tl[#tl + 1] = { t = t, fn = function()
		get_console():execute("r2_sun_lumscale 0.5")
		lumscale_presets.apply("off", false)
		local v = lumscale_presets.get_cvar("r2_sun_lumscale")
		B.log((tonumber(v) == 0.5 and "PASS" or "FAIL") .. " off-keeps-user-value r2_sun_lumscale=" .. tostring(v))
		lumscale_presets.apply("default", false)
		local v2 = lumscale_presets.get_cvar("r2_sun_lumscale")
		B.log((tonumber(v2) == 1.0 and "PASS" or "FAIL") .. " default-restores r2_sun_lumscale=" .. tostring(v2))
		lumscale_presets.apply("nonsense", false)
		B.log("PASS unknown-preset-no-crash")
		B.log("DONE")
	end }
	return tl
end

local function lum_bot_tick()
	local now = time_global()
	if B.t0 == nil then
		B.t0 = now
		read_cfg()
		B.log("BOT start dedicated=" .. tostring(IsDedicatedServer()) .. " cfg tag=" .. B.cfg.tag .. " presets=" .. B.cfg.presets .. " spots=" .. B.cfg.spots)
	end
	if now - B.last < 1000 then return false end
	B.last = now
	pcall(function() get_console():execute("flush") end)
	local lo = local_object()
	if lo == nil or lo:section() == "spectator" then
		if now_s() > 8 and now > B.respawn_at then
			B.respawn_at = now + 10000
			local ok, err = pcall(function() game.respawn_dead_players() end)
			B.log("spectator -> respawn_dead_players " .. (ok and "called" or tostring(err)))
		end
		return false
	end
	if B.spawned_at == nil then
		B.spawned_at = now
		local p = lo:position()
		local okr, rn = pcall(function() return get_console():get_string("renderer") end)
		B.log(string.format("SPAWNED level=%s pos=%.1f,%.1f,%.1f renderer=%s", level.name(), p.x, p.y, p.z, tostring(rn)))
		return false
	end
	local ts = (now - B.spawned_at) / 1000
	if ts < 15 then return false end   -- let the level settle
	if B.tl == nil then
		B.t_tl = ts
		B.tl = build_timeline(lo)
		B.log("TIMELINE steps=" .. #B.tl)
	end
	local rel = ts - B.t_tl
	while B.tl[B.idx] ~= nil and B.tl[B.idx].t <= rel do
		local step = B.tl[B.idx]
		B.idx = B.idx + 1
		local ok, err = pcall(step.fn)
		if not ok then B.log("FAIL step error " .. tostring(err)) end
	end
	return false
end

do
	local ok, err = pcall(function() level.add_call(lum_bot_tick, function() end) end)
	B.log("lum_bot loaded add_call " .. (ok and "ok" or tostring(err)))
end
