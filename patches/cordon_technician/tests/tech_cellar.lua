-- Technician in the village cellar (test only, replaces tech_basement.lua). Run in LISTEN mode, ONE game process:
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner techcellar -Hooks tech_cellar.lua -ExtraDir <stage>\gamedata -SoakSeconds 150 -ResultDir <dir>
-- Lines "TECH ..." in qa_events.log (asserts in client_A\qa_assert.log): where he stands (online position, level vertex, direction), that it is the cellar floor
-- and not the bunker / the house above, his logic scheme, then the player is put 1.5 m in front of him and the talk window is opened.
-- Cellar (cform + level.ai of the mod Cordon): room x -215.7..-211.0, z -127.7..-120.4, floor y -23.2; the entrance is the gap in its south wall at
-- x -212.0..-210.9, z -127.7; the guide sits at the north end (cover esc_smart_terrain_1_animpoint_4, -213.1, -23.2, -121.9).
local S = { stage = 0 }
local ROOM = { x1 = -215.7, x2 = -211.0, z1 = -127.7, z2 = -120.4, y1 = -23.8, y2 = -22.6 }

local function tech()
	local id = nil
	pcall(function() id = get_story_object_id("esc_rookie_technician") end)
	if id == nil then return nil end
	return id, alife():object(id), level.object_by_id(id)
end

local function guide()
	local g = nil
	pcall(function()
		local gid = get_story_object_id("esc_smart_terrain_1_stalker_guide")
		if gid ~= nil then g = level.object_by_id(gid) end
	end)
	return g
end

qa.hooks.tech_cellar = function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l01_escape" then return end
	for id, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then v.health = 1 end end
	local id, se, o = tech()
	if S.stage == 0 then
		if id ~= nil and se ~= nil and o ~= nil and t >= 25 then
			local p = o:position()
			local d = o:direction()
			local sch = "-"
			pcall(function() sch = tostring(db.storage[id].active_section) end)
			qa.event(string.format("TECH online id=%d alive=%s pos=%.2f,%.2f,%.2f dir=%.2f,%.2f lvid=%s gvid=%s scheme=%s", id, tostring(o:alive()), p.x, p.y, p.z, d.x, d.z, tostring(o:level_vertex_id()), tostring(o:game_vertex_id()), sch))
			local in_cellar = p.x > ROOM.x1 and p.x < ROOM.x2 and p.z > ROOM.z1 and p.z < ROOM.z2 and p.y > ROOM.y1 and p.y < ROOM.y2
			qa.assert("technician stands in the village cellar (x -215.7..-211.0, z -127.7..-120.4, floor y -23.2), not in the bunker or the house above", in_cellar, string.format("%.2f %.2f %.2f", p.x, p.y, p.z))
			qa.assert("technician logic is the remark scheme", string.find(sch, "remark@esc_rookie_technician", 1, true) ~= nil, sch)
			-- standing: the animation state of the remark scheme (ward_noweap) is a standing pose; the body state name is logged when the engine gives it
			local bs = "?"
			pcall(function() bs = tostring(state_mgr.get_state and state_mgr.get_state(o) or "n/a") end)
			qa.event("TECH body_state=" .. bs)
			-- facing: toward the entrance gap in the south wall (direction z negative; the look point is esc_smart_terrain_1_guard_6_walk, 11 m south)
			qa.event(string.format("TECH facing south: dir.z=%.2f (want < -0.5 once the remark scheme turned him)", d.z))
			S.face_t = t
			local g = guide()
			if g ~= nil then
				local gp = g:position()
				qa.event(string.format("TECH guide online pos=%.2f,%.2f,%.2f distance to technician %.2f", gp.x, gp.y, gp.z, gp:distance_to(p)))
			else
				qa.event("TECH guide not online (he only exists after his quest / is offline here)")
			end
			qa.event(string.format("TECH server pos=%.2f,%.2f,%.2f", se.position.x, se.position.y, se.position.z))
			local pr, nm = "?", "?"
			pcall(function() pr = o:profile_name() end)
			pcall(function() nm = o:character_name() end)
			qa.event("TECH profile=" .. tostring(pr) .. " name=" .. tostring(nm) .. " talk_enabled=" .. tostring(o:is_talk_enabled()))
			qa.assert("technician talk enabled", o:is_talk_enabled() == true)
			-- teleport the player 1.5 m in front of him (west, he is in the open middle of the room) and face him
			for pid, v in pairs(db.mp_actors or {}) do
				if v ~= nil and v:alive() then
					local tx, ty, tz = p.x - 1.5, p.y + 0.3, p.z
					local ok, err = pcall(function() v:set_actor_position(vector():set(tx, ty, tz)) end)
					pcall(function() v:set_actor_direction(-math.atan2(p.x - tx, p.z - tz)) end)
					qa.event("TECH teleport player " .. tostring(ok) .. " " .. tostring(err))
				end
			end
			S.stage = 1
			S.t1 = t
		elseif t >= 25 and (t % 10 == 0) then
			qa.event("TECH waiting id=" .. tostring(id) .. " se=" .. tostring(se ~= nil) .. " online=" .. tostring(o ~= nil))
		end
	elseif S.stage == 1 and t - S.t1 >= 6 then
		local pl = nil
		for pid, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then pl = v end end
		if pl ~= nil and o ~= nil then
			local pp, tp = pl:position(), o:position()
			local d = o:direction()
			qa.event(string.format("TECH player at %.2f,%.2f,%.2f distance to technician %.2f; technician dir=%.2f,%.2f now", pp.x, pp.y, pp.z, pp:distance_to(tp), d.x, d.z))
			qa.assert("technician faces the entrance (south, direction z < -0.5)", d.z < -0.5, string.format("%.2f", d.z))
			local ok, err = pcall(function() pl:run_talk_dialog(o, false) end)
			qa.event("TECH run_talk_dialog " .. tostring(ok) .. " " .. tostring(err))
		end
		S.stage = 2
		S.t2 = t
	elseif S.stage == 2 and t - S.t2 >= 3 then
		local pl = nil
		for pid, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then pl = v end end
		local talking, recv = "?", "?"
		if pl ~= nil then
			pcall(function() talking = tostring(pl:is_talking()) end)
			pcall(function() recv = tostring(level.main_input_receiver()) end)
		end
		qa.event("TECH is_talking=" .. talking .. " main_input_receiver=" .. recv)
		qa.assert("talk window opened with the technician in the cellar", talking == "true", talking)
		S.stage = 3
	end
end
