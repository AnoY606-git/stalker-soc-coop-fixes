-- TEST ONLY (never shipped).  repeatable_quests spawn-site test: start on Cordon, travel to the Bar through the guide + party vote
-- (the Bar's alife only comes online that way), accept one generated job by giving its accept flag (what the dialog does),
-- then check where the targets are, that they live for 60 s and that the map spot is on them.
-- run_coop -Mode listen -Clients 1 -Cfg no_respawn=1 -Cfg rq=rq_ska_kill -Cfg gv=1224 -Cfg lvl=l05_bar
local function cfgs(k, d) local v = qa.cfg and qa.cfg[k]; if v == nil or v == "" then return d end return v end
local function now() return os.time() end
local function sf(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function pth(n) return getFS():update_path("$logs$", n) end
local function wr(line)
	pcall(function() local f = io.open(pth("rq_spawn.log"), "a"); if f then f:write(string.format("[%d] %s\n", now(), line)); f:close() end end)
end
local function rdst()
	local ok, r = pcall(function() local f = io.open(pth("rq_state.txt"), "r"); if not f then return nil end local s = f:read("*a"); f:close(); return s end)
	local st = {}
	if ok and r then for k, v in string.gmatch(r, "([%w_]+)=([^\n]*)") do st[k] = tonumber(v) or v end end
	return st
end
local function wst(st)
	pcall(function()
		local f = io.open(pth("rq_state.txt"), "w")
		if f then for k, v in pairs(st) do f:write(k, "=", tostring(v), "\n") end f:close() end
	end)
end
local function actors()
	local out = {}
	if type(db.mp_actors) == "table" then
		for id, v in pairs(db.mp_actors) do if v ~= nil and sf(function() return v:alive() end) then out[#out + 1] = v end end
	end
	return out
end
local function flag(n) return sf(story_flags.has_flag, n) == true end
local function dist(a, b) local dx, dz = a.x - b.x, a.z - b.z return math.sqrt(dx * dx + dz * dz) end

local function squads_of(prefix)
	local ids = {}
	local sfl = story_flags.story_flags
	for k, v in pairs(sfl) do
		if v == true and string.sub(k, 1, #prefix) == prefix then
			local n = tonumber(string.sub(k, #prefix + 1)); if n then ids[#ids + 1] = n end
		end
	end
	return ids
end

local function survey(rq, site)
	local my_lid = sf(function() return game_graph():vertex(tonumber("@GV@")):level_id() end)
	local key = "RQ_" .. string.upper(rq)
	local info = { n_squads = 0, members = 0, alive = 0, maxd = 0, mind_other = 9999, other = "-" }
	local member_ids = {}
	for _, sid in ipairs(squads_of(key .. "_S")) do
		local sq = sf(function() return alife():object(sid) end)
		if sq ~= nil then
			info.n_squads = info.n_squads + 1
			sf(function()
				for k in sq:squad_members() do
					member_ids[k.id] = true
					local o = alife():object(k.id)
					if o ~= nil then
						info.members = info.members + 1
						if sf(function() return o:alive() end) then info.alive = info.alive + 1 end
						if sf(function() return level.object_by_id(k.id) end) ~= nil then info.online = (info.online or 0) + 1 end
						local d = dist(o.position, site)
						if d > info.maxd then info.maxd = d end
					end
				end
			end)
		end
	end
	for id = 1, 65534 do
		local o = sf(function() return alife():object(id) end)
		if o ~= nil and not member_ids[id] and sf(function() return o:clsid() == clsid.script_stalker end) and sf(function() return o:alive() end) and sf(function() return game_graph():vertex(o.m_game_vertex_id):level_id() end) == my_lid then
			local d = dist(o.position, site)
			if d < info.mind_other then info.mind_other = d; info.other = tostring(o:name()) end
		end
	end
	local spot = false
	for _, sid in ipairs(squads_of(key .. "_P")) do spot = true; info.spot_obj = sid end
	info.spot = spot
	return info
end

qa.hooks.rq_spawn = function(t, lo)
	if not OnServer() then return end
	local A = actors()
	if #A < 1 then return end
	for _, v in ipairs(A) do pcall(function() v.health = 1 end) end
	local lvl = tostring(sf(level.name))
	local rq = "@RQ@"
	local want_lvl = cfgs("lvl", "l05_bar")
	local acc = "RQG_" .. string.upper(rq) .. "_ACC"
	local st = rdst()
	local on_target = string.find(lvl, want_lvl, 1, true) ~= nil
	if now() - (st.hb or 0) >= 10 then st.hb = now(); wr("HB lvl=" .. lvl .. " stage=" .. tostring(st.stage) .. " actors=" .. #A); wst(st) end
	if not on_target then
		-- travel
		if (st.travel_t or 0) == 0 then
			st.travel_t = now(); wst(st)
		end
		if now() - st.travel_t > 14 and (st.vote_t or 0) == 0 then
			story_flags.give_flag("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_BAR_INFO")
			st.vote_t = now(); wst(st)
			wr("guide flag given")
		elseif (st.vote_t or 0) > 0 and now() - st.vote_t > 3 and now() - (st.last_vote or 0) > 8 then
			st.last_vote = now(); wst(st)
			for _, v in ipairs(A) do pcall(function() coop_map_vote.on_yes(v:id()) end) end
			wr("vote yes")
			if now() - st.vote_t > 40 and (st.fb or 0) == 0 then
				st.fb = 1; wst(st)
				wr("fallback teleport")
				pcall(function() xr_effects.xrmpe_teleport_actors(nil, nil, { "esc_smart_terrain_1_guide_temp_6_walk", "esc_smart_terrain_1_guide_temp_6_look" }) end)
			end
		end
		return
	end
	-- on the target level
	if (st.arrive_t or 0) == 0 then st.arrive_t = now(); wst(st); wr("arrived on " .. lvl) return end
	local gv = tonumber("@GV@")
	local site = nil
	local okv, v = pcall(function() return game_graph():vertex(gv):level_point() end)
	if okv then site = v end
	if site == nil then qa.assert("site vertex readable", false, "gv " .. tostring(gv)) return end
	if (st.acc_t or 0) == 0 then
		if now() - st.arrive_t >= 30 then
			story_flags.give_flag(acc)
			st.acc_t = now(); wst(st)
			wr("accepted " .. acc .. " site gv " .. gv .. string.format(" (%.0f %.0f %.0f)", site.x, site.y, site.z))
			local a = A[1]
			qa.event(string.format("actor at %.0f %.0f %.0f", a:position().x, a:position().y, a:position().z))
		end
		return
	end
	local dt = now() - st.acc_t
	if dt >= 10 and (st.s1 or 0) == 0 then
		st.s1 = 1; wst(st)
		local i = survey(rq, site)
		wr(string.format("S1 squads=%d members=%d alive=%d max_dist_from_site=%.1f nearest_other_npc=%.0f (%s) spot=%s spot_obj=%s", i.n_squads, i.members, i.alive, i.maxd, i.mind_other, i.other, tostring(i.spot), tostring(i.spot_obj)))
		qa.assert(rq .. ": targets spawned at the site", i.n_squads >= 1 and i.members >= 1 and i.maxd < 40, string.format("squads %d members %d max dist from site %.1f", i.n_squads, i.members, i.maxd))
		qa.assert(rq .. ": no other NPC within 80 m of the targets", i.mind_other >= 80, string.format("nearest %.0f (%s)", i.mind_other, i.other))
		qa.assert(rq .. ": map spot set on the targets", i.spot, tostring(i.spot_obj))
		if i.spot_obj then
			local so = sf(function() return alife():object(i.spot_obj) end)
			if so ~= nil then wr(string.format("spot object %s at %.0f %.0f %.0f", tostring(so:name()), so.position.x, so.position.y, so.position.z)) end
		end
	end
	if dt >= 12 and (st.tp or 0) == 0 and lo ~= nil then
		-- walk the player to the targets: they come online (the Bar NPCs and the targets can meet only if they were placed badly)
		st.tp = 1; wst(st)
		local okn, np = pcall(function() return game_graph():vertex(tonumber("@NEAR@")):level_point() end)
		if okn then
			local ok2, e2 = pcall(function() lo:set_actor_position(vector():set(np.x, np.y + 0.3, np.z)) end)
			wr(string.format("teleported player to near vertex @NEAR@ (%.0f %.0f %.0f) %s %s", np.x, np.y, np.z, tostring(ok2), tostring(e2)))
		end
	end
	if dt >= 34 and (st.s3 or 0) == 0 then
		st.s3 = 1; wst(st)
		local i = survey(rq, site)
		wr(string.format("S3 (player near) squads=%d members=%d alive=%d online=%s max_dist_from_site=%.1f nearest_other_npc=%.0f (%s)", i.n_squads, i.members, i.alive, tostring(i.online), i.maxd, i.mind_other, i.other))
		qa.assert(rq .. ": targets online and alive with the player nearby", (i.online or 0) >= 1 and i.alive == i.members, string.format("online %s alive %d/%d", tostring(i.online), i.alive, i.members))
		pcall(function() get_console():execute("screenshot jpg") end)
	end
	if dt >= 70 and (st.s2 or 0) == 0 then
		st.s2 = 1; wst(st)
		local i = survey(rq, site)
		local fin = flag("RQG_" .. string.upper(rq) .. "_DONE") or flag("RQG_" .. string.upper(rq) .. "_FAIL")
		wr(string.format("S2 squads=%d members=%d alive=%d max_dist_from_site=%.1f nearest_other_npc=%.0f (%s) finished=%s", i.n_squads, i.members, i.alive, i.maxd, i.mind_other, i.other, tostring(fin)))
		qa.assert(rq .. ": targets alive after 60 s", i.alive >= 1 and i.alive == i.members and not fin, string.format("alive %d/%d finished %s", i.alive, i.members, tostring(fin)))
		qa.assert(rq .. ": targets stayed near the site", i.maxd < 80, string.format("max dist %.1f", i.maxd))
		pcall(function() get_console():execute("screenshot jpg") end)
		st.done = 1; wst(st)
	end
end
