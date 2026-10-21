-- Technician in the basement (test only, never shipped). Run in LISTEN mode:
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Hooks tech_basement.lua -ExtraDir <stage>\gamedata -SoakSeconds 150
-- Logs "TECH ..." lines (qa_events.log): where he stands (server position and online position), his level vertex and logic scheme, then
-- teleports the player next to him, opens the talk dialog with run_talk_dialog and reports actor:is_talking() / the main input receiver.
local S = { stage = 0 }

local function tech()
	local id = nil
	pcall(function() id = get_story_object_id("esc_rookie_technician") end)
	if id == nil then return nil end
	return id, alife():object(id), level.object_by_id(id)
end

qa.hooks.tech_basement = function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l01_escape" then return end
	for id, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then v.health = 1 end end
	local id, se, o = tech()
	if S.stage == 0 then
		if id ~= nil and se ~= nil and o ~= nil and t >= 20 then
			local p = o:position()
			local sch = "-"
			pcall(function() sch = tostring(db.storage[id].active_section) end)
			qa.event(string.format("TECH online id=%d alive=%s pos=%.2f,%.2f,%.2f lvid=%s gvid=%s scheme=%s", id, tostring(o:alive()), p.x, p.y, p.z, tostring(o:level_vertex_id()), tostring(o:game_vertex_id()), sch))
			qa.event(string.format("TECH server pos=%.2f,%.2f,%.2f", se.position.x, se.position.y, se.position.z))
			local pr, nm = "?", "?"
			pcall(function() pr = o:profile_name() end)
			pcall(function() nm = o:character_name() end)
			qa.event("TECH profile=" .. tostring(pr) .. " name=" .. tostring(nm) .. " talk_enabled=" .. tostring(o:is_talk_enabled()))
			-- teleport the player next to him (node of the bunker, 2 m west) and face him
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
		elseif t >= 20 and (t % 10 == 0) then
			qa.event("TECH waiting id=" .. tostring(id) .. " se=" .. tostring(se ~= nil) .. " online=" .. tostring(o ~= nil))
		end
	elseif S.stage == 1 and t - S.t1 >= 4 then
		local pl = nil
		for pid, v in pairs(db.mp_actors or {}) do if v ~= nil and v:alive() then pl = v end end
		if pl ~= nil and o ~= nil then
			local pp = pl:position()
			qa.event(string.format("TECH player at %.2f,%.2f,%.2f distance to technician %.2f", pp.x, pp.y, pp.z, pp:distance_to(o:position())))
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
		S.stage = 3
	end
end
