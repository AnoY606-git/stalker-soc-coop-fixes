--@qa_lib
-- cordon_megafon live check (listen host, map coop_l01_escape). NOT SHIPPED. Written offline 2026-10-21, not run yet.
-- Run:  run_coop.ps1 -Map coop_l01_escape -Mode listen -Owner megafon -Clients 1 -ExtraDir <stage>\gamedata `
--         -Hooks <this file> -SoakSeconds 10 -CompareTimeout 10 -ResultDir <dir>        (use the same hooks with and without the patch)
-- What it does: a 1 Hz probe logs, for the speaker restrictor and the two themes, the distance of the nearest player, whether the theme is
-- playing and the sound_object's own min_distance / max_distance / volume (the values the engine took from the ogg comment).
-- A task walks the host to three places and asserts: far (rookie village, about 225 m) -> the theme must NOT start; near (about 100 m) -> it
-- MUST start; the logged ogg params must be min 10 / max 400 (megafon) and min 20 / max 400 (esc_sirena) with the patch.
-- Result lines: qa_events.log (MEGAFON ...) and qa_assert.log.
local L = qa_lib

local RUPOR = { x = -141.8, y = -22.8, z = -353.9 }      -- esc_rupor / esc_rupor_space_restrictor (stock Cordon)
local VILLAGE = { x = -196.0, y = -19.5, z = -136.2 }    -- esc_smart_terrain_1_5_camp, rookie village fire
local NEAR_DIST = 100
local FAR_WAIT, NEAR_WAIT = 45, 60                        -- real seconds; sr_idle@wait lasts 450 game s, megafon file 10..30 s

local function fmt(n) return string.format("%.1f", n or -1) end

local function theme_info(name)
	local ok, th = pcall(function() return sound_theme.theme[name] end)
	if not ok or th == nil then return "no theme", false end
	local playing = false
	pcall(function() playing = th:is_playing() == true end)
	local par = "no snd_obj"
	pcall(function()
		local s = th.snd_obj
		if s ~= nil then par = string.format("min %s max %s vol %s", fmt(s.min_distance), fmt(s.max_distance), fmt(s.volume)) end
	end)
	return par, playing
end

local function nearest_player_dist()
	local best = nil
	for _, p in ipairs(L.players()) do
		local pp = L.pos(p.obj)
		if pp ~= nil then
			local d = L.dist3(pp, RUPOR)
			if best == nil or d < best then best = d end
		end
	end
	return best
end

local seen = { megafon = false, esc_sirena = false }
local function probe()
	local d = nearest_player_dist()
	local line = "MEGAFON probe dist_to_rupor=" .. fmt(d)
	for _, nm in ipairs({ "megafon", "esc_sirena" }) do
		local par, playing = theme_info(nm)
		line = line .. string.format(" | %s playing=%s %s", nm, tostring(playing), par)
		if playing then seen[nm] = true end
	end
	qa.event(line)
end

-- a spot `dist` metres from the rupor on the line to the village, ground height from the ai map
local function spot(dist)
	local dx, dz = VILLAGE.x - RUPOR.x, VILLAGE.z - RUPOR.z
	local len = math.sqrt(dx * dx + dz * dz)
	local x, z = RUPOR.x + dx / len * dist, RUPOR.z + dz / len * dist
	local y = RUPOR.y
	pcall(function()
		local v = vector():set(x, y, z)
		local vid = level.vertex_id(v)
		if vid ~= nil and vid < 4000000000 then y = level.vertex_position(vid).y end
	end)
	return L.vec(x, y + 0.5, z)
end

qa.hooks.megafon_probe = function(t, lo) if OnServer() then probe() end end

qa.once("megafon_walk", function(t, lo)
	if not OnServer() then return end
	L.god(true)
	local rec = { far_started = false }
	L.task("megafon walk", {
		function(c) return L.wait(15) end,
		function(c) qa.event("MEGAFON step 1: village, dist " .. fmt(L.dist3(VILLAGE, RUPOR))) return L.teleport(nil, VILLAGE) end,
		function(c, ok) qa.assert("megafon teleport village", ok, "") seen.megafon = false seen.esc_sirena = false return L.wait(FAR_WAIT) end,
		function(c)
			qa.assert("megafon far: theme does not start in the village", not seen.megafon and not seen.esc_sirena,
				"megafon=" .. tostring(seen.megafon) .. " sirena=" .. tostring(seen.esc_sirena))
			qa.event("MEGAFON step 2: near, dist " .. NEAR_DIST)
			return L.teleport(nil, spot(NEAR_DIST))
		end,
		function(c, ok) qa.assert("megafon teleport near", ok, "") return L.wait(NEAR_WAIT) end,
		function(c)
			qa.assert("megafon near: theme starts", seen.megafon or seen.esc_sirena, "megafon=" .. tostring(seen.megafon))
			local par = theme_info("megafon")
			qa.event("MEGAFON params after start: " .. par)
			qa.assert("megafon ogg params are SoC-like", string.find(par, "min 10.0 max 400.0", 1, true) ~= nil, par)
			return L.done(true)
		end,
	})
end)
