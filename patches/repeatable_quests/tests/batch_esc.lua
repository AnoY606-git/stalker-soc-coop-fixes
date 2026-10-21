-- TEST ONLY (never shipped).  repeatable_quests batch test: accepts every generated job of one level one after another (what the dialog does:
-- it gives the job's accept flag) and checks per job: targets / item spawned at the site, map spot, no other NPC within 80 m, no anomaly
-- zone within 15 m, sane y; then 30 s later (player moved next to the site so the targets are online): alive, y sane. Then it removes the
-- targets and goes on with the next job.  Bar: start on Cordon and travel by party vote (the Bar's alife only comes online that way).
local JOBS = {
	{id = "rq_wolf_camp2", kind = "gen_camp", x = -60.2, y = 0.4, z = 216.3, nx = -36.4, ny = 2.8, nz = 252.7},
	{id = "rq_sid_camp", kind = "gen_camp", x = 96.6, y = 13.1, z = 612.5, nx = 120.4, ny = 16.2, nz = 600.6},
	{id = "rq_sid_kill", kind = "gen_kill", x = -124.6, y = -26.3, z = -467.6, nx = -108.5, ny = -27.3, nz = -503.3},
	{id = "rq_sid_defend", kind = "gen_defend", x = -264.6, y = -12.0, z = -252.0, nx = -276.5, ny = -8.5, nz = -216.3},
	{id = "rq_wolf_camp1", kind = "gen_camp", x = -180.6, y = 31.9, z = 191.8, nx = -204.4, ny = 30.3, nz = 203.7},
	{id = "rq_shu_find", kind = "gen_find", x = -71.4, y = -23.2, z = -251.3, nx = -59.5, ny = -19.5, nz = -215.6},
}
local LVL = "coop_l01_escape"
local TRAVEL = false
local function now() return os.time() end
local function sf(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function pth(n) return getFS():update_path("$logs$", n) end
local function wr(line)
	pcall(function() local f = io.open(pth("rq_batch.log"), "a"); if f then f:write(string.format("[%d] %s\n", now(), line)); f:close() end end)
end
local function rdst()
	local ok, r = pcall(function() local f = io.open(pth("rq_bstate.txt"), "r"); if not f then return nil end local s = f:read("*a"); f:close(); return s end)
	local st = {}
	if ok and r then for k, v in string.gmatch(r, "([%w_]+)=([^\n]*)") do st[k] = tonumber(v) or v end end
	return st
end
local function wst(st)
	pcall(function()
		local f = io.open(pth("rq_bstate.txt"), "w")
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
local function d2(a, b) local dx, dz = a.x - b.x, a.z - b.z return math.sqrt(dx * dx + dz * dz) end
local function ids_with(prefix)
	local ids = {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true and string.sub(k, 1, #prefix) == prefix then
			local n = tonumber(string.sub(k, #prefix + 1)); if n then ids[#ids + 1] = n end
		end
	end
	return ids
end

local my_lid = nil
local function level_id_of(o) return sf(function() return game_graph():vertex(o.m_game_vertex_id):level_id() end) end

-- one survey of a running job: members / item, spot flag, nearest other NPC, nearest anomaly zone, y sanity (server and online objects)
local function survey(job)
	local site = vector():set(job.x, job.y, job.z)
	local key = "RQ_" .. string.upper(job.id)
	local i = { n_squads = 0, members = 0, alive = 0, online = 0, maxd = 0, maxdy = 0, maxdy_on = 0, mind_other = 9999, other = "-", zone = 9999, zname = "-", item = false, item_on = false }
	local mids = {}
	for _, sid in ipairs(ids_with(key .. "_S")) do
		local sq = sf(function() return alife():object(sid) end)
		if sq ~= nil then
			i.n_squads = i.n_squads + 1
			sf(function()
				for k in sq:squad_members() do
					mids[k.id] = true
					local o = alife():object(k.id)
					if o ~= nil then
						i.members = i.members + 1
						if sf(function() return o:alive() end) then i.alive = i.alive + 1 end
						local dd = d2(o.position, site); if dd > i.maxd then i.maxd = dd end
						local dy = math.abs(o.position.y - job.y); if dy > i.maxdy then i.maxdy = dy end
						local lo = sf(function() return level.object_by_id(k.id) end)
						if lo ~= nil then
							i.online = i.online + 1
							local py = sf(function() return lo:position().y end)
							if py ~= nil then local dyo = math.abs(py - job.y); if dyo > i.maxdy_on then i.maxdy_on = dyo end end
						end
					end
				end
			end)
		end
	end
	for _, iid in ipairs(ids_with(key .. "_I")) do
		local so = sf(function() return alife():object(iid) end)
		if so ~= nil then
			i.item = true; i.item_id = iid
			i.maxd = d2(so.position, site); i.maxdy = math.abs(so.position.y - job.y)
			local lo = sf(function() return level.object_by_id(iid) end)
			if lo ~= nil then
				i.item_on = true
				local py = sf(function() return lo:position().y end)
				if py ~= nil then i.maxdy_on = math.abs(py - job.y) end
			end
		end
	end
	for id = 1, 65534 do
		local o = sf(function() return alife():object(id) end)
		if o ~= nil and level_id_of(o) == my_lid then
			local sec = sf(function() return o:section_name() end) or ""
			if string.sub(sec, 1, 5) == "zone_" then
				local dd = d2(o.position, site)
				if dd < i.zone then i.zone = dd; i.zname = tostring(o:name()) end
			elseif not mids[id] and sf(function() return o:clsid() == clsid.script_stalker end) and sf(function() return o:alive() end) then
				local dd = d2(o.position, site)
				if dd < i.mind_other then i.mind_other = dd; i.other = tostring(o:name()) end
			end
		end
	end
	i.spot = #ids_with(key .. "_P") > 0
	return i
end

local function cleanup(job)
	local key = "RQ_" .. string.upper(job.id)
	for _, sid in ipairs(ids_with(key .. "_S")) do
		local sq = sf(function() return alife():object(sid) end)
		if sq ~= nil then
			if not sf(function() sim_board.get_sim_board():remove_squad(sq) return true end) then
				sf(function() for k in sq:squad_members() do local o = alife():object(k.id); if o then alife():release(o, true) end end end)
			end
		end
	end
	for _, iid in ipairs(ids_with(key .. "_I")) do
		local so = sf(function() return alife():object(iid) end)
		if so ~= nil then sf(function() alife():release(so, true) end) end
	end
end

-- first-look trackers (measured at the moment that matters, not seconds later when the targets have already walked):
--  SPAWN: distance of the new members / item from the site on the first tick after the job spawned them (server positions)
--  FIRST: per member / item, the first tick it exists as an online object: height vs the site, horizontal distance, height vs its own AI node
local SPAWN, FIRST = nil, {}
local function job_objects(job)
	local key = "RQ_" .. string.upper(job.id)
	local objs = {}
	for _, sid in ipairs(ids_with(key .. "_S")) do
		local sq = sf(function() return alife():object(sid) end)
		if sq ~= nil then sf(function() for k in sq:squad_members() do objs[#objs + 1] = k.id end end) end
	end
	for _, iid in ipairs(ids_with(key .. "_I")) do objs[#objs + 1] = iid end
	return objs
end
local function spawn_probe(job)
	if SPAWN ~= nil then return end
	local site = vector():set(job.x, job.y, job.z)
	local objs = job_objects(job)
	if #objs == 0 then return end
	local n, maxd, maxdy = 0, 0, 0
	for _, id in ipairs(objs) do
		local o = sf(function() return alife():object(id) end)
		if o ~= nil then
			n = n + 1
			local dd = d2(o.position, site); if dd > maxd then maxd = dd end
			local dy = math.abs(o.position.y - job.y); if dy > maxdy then maxdy = dy end
		end
	end
	if n > 0 then SPAWN = {n = n, maxd = maxd, maxdy = maxdy, t = now()} end
end
local function track_first(job)
	local site = vector():set(job.x, job.y, job.z)
	for _, id in ipairs(job_objects(job)) do
		if FIRST[id] == nil then
			local lo = sf(function() return level.object_by_id(id) end)
			local p = lo ~= nil and sf(function() return lo:position() end) or nil
			if p ~= nil then
				local ny = sf(function() return level.vertex_position(lo:level_vertex_id()).y end)
				FIRST[id] = {dy = math.abs(p.y - job.y), dxz = d2(p, site), dn = ny and math.abs(p.y - ny) or 0}
			end
		end
	end
end
local function first_summary()
	local n, maxdy, maxdxz, maxdn = 0, 0, 0, 0
	for _, f in pairs(FIRST) do
		n = n + 1
		if f.dy > maxdy then maxdy = f.dy end
		if f.dxz > maxdxz then maxdxz = f.dxz end
		if f.dn > maxdn then maxdn = f.dn end
	end
	return n, maxdy, maxdxz, maxdn
end

local RESULTS = {}
local function check(job, name, ok, detail)
	qa.assert(job.id .. ": " .. name, ok, detail)
	RESULTS[#RESULTS + 1] = (ok and "PASS " or "FAIL ") .. job.id .. " " .. name .. " | " .. tostring(detail)
end

qa.hooks.rq_batch = function(t, lo)
	if not OnServer() then return end
	local A = actors()
	if #A < 1 then return end
	for _, v in ipairs(A) do pcall(function() v.health = 1 end) end
	if (rdst().god or 0) == 0 then local s0 = rdst(); s0.god = 1; wst(s0); pcall(function() get_console():execute("g_god on") end); wr("g_god on") end
	local lvl = tostring(sf(level.name))
	local st = rdst()
	local on_target = string.find(lvl, LVL, 1, true) ~= nil
	if now() - (st.hb or 0) >= 15 then st.hb = now(); wr("HB lvl=" .. lvl .. " job=" .. tostring(st.job) .. " phase=" .. tostring(st.phase)); wst(st) end
	if not on_target then
		if not TRAVEL then return end
		if (st.travel_t or 0) == 0 then st.travel_t = now(); wst(st) end
		if now() - st.travel_t > 14 and (st.vote_t or 0) == 0 then
			story_flags.give_flag("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_BAR_INFO"); st.vote_t = now(); wst(st); wr("guide flag given")
		elseif (st.vote_t or 0) > 0 and now() - st.vote_t > 3 and now() - (st.last_vote or 0) > 8 then
			st.last_vote = now(); wst(st)
			for _, v in ipairs(A) do pcall(function() coop_map_vote.on_yes(v:id()) end) end
			wr("vote yes")
			if now() - st.vote_t > 40 and (st.fb or 0) == 0 then
				st.fb = 1; wst(st); wr("fallback teleport")
				pcall(function() xr_effects.xrmpe_teleport_actors(nil, nil, { "esc_smart_terrain_1_guide_temp_6_walk", "esc_smart_terrain_1_guide_temp_6_look" }) end)
			end
		end
		return
	end
	if (st.arrive_t or 0) == 0 then st.arrive_t = now(); wst(st); wr("arrived on " .. lvl) return end
	if my_lid == nil then my_lid = sf(function() return game_graph():vertex(alife():actor().m_game_vertex_id):level_id() end) end
	if now() - st.arrive_t < 30 then return end
	st.job = st.job or 1
	local job = JOBS[st.job]
	if job == nil then
		if (st.fin or 0) == 0 then
			st.fin = 1; wst(st)
			local p, f = 0, 0
			for _, r in ipairs(RESULTS) do if string.sub(r, 1, 4) == "PASS" then p = p + 1 else f = f + 1 end end
			wr("BATCH DONE jobs=" .. #JOBS .. " checks pass=" .. p .. " fail=" .. f)
		end
		return
	end
	local acc = "RQG_" .. string.upper(job.id) .. "_ACC"
	local dt = now() - (st.job_t or now())
	if (st.phase or "start") == "start" then
		st.phase = "accepted"; st.job_t = now(); st.on1 = 0; wst(st)
		SPAWN = nil; FIRST = {}
		story_flags.give_flag(acc)
		wr("JOB " .. job.id .. " accepted " .. acc)
	elseif st.phase == "accepted" and dt < 6 then
		spawn_probe(job)
	elseif st.phase == "accepted" and dt >= 6 then
		st.phase = "s1"; wst(st)
		spawn_probe(job)
		local i = survey(job)
		wr(string.format("S1 %s squads=%d members=%d item=%s maxd=%.1f maxdy=%.1f other=%.0f (%s) zone=%.0f (%s) spot=%s", job.id, i.n_squads, i.members, tostring(i.item), i.maxd, i.maxdy, i.mind_other, i.other, i.zone, i.zname, tostring(i.spot)))
		if job.kind == "gen_find" then
			check(job, "item spawned at the site", i.item and SPAWN ~= nil and SPAWN.maxd < 3, string.format("item %s dist %.1f at spawn (now %.1f)", tostring(i.item), SPAWN and SPAWN.maxd or -1, i.maxd))
		else
			check(job, "targets spawned at the site (measured on the tick they were created)", i.n_squads >= 1 and i.members >= 1 and SPAWN ~= nil and SPAWN.maxd < 5, string.format("squads %d members %d dist %.1f at spawn (%.1f 6 s later)", i.n_squads, i.members, SPAWN and SPAWN.maxd or -1, i.maxd))
		end
		check(job, "map spot on the target", i.spot, tostring(i.spot))
		check(job, "no other NPC within 80 m", i.mind_other >= 80, string.format("%.0f (%s)", i.mind_other, i.other))
		check(job, "no anomaly zone within 15 m", i.zone >= 15, string.format("%.0f (%s)", i.zone, i.zname))
		check(job, "y sane vs the site (server, at spawn)", SPAWN ~= nil and SPAWN.maxdy < 3, string.format("max dy %.1f at spawn (%.1f 6 s later)", SPAWN and SPAWN.maxdy or -1, i.maxdy))
	elseif st.phase == "s1" and dt >= 7 then
		st.phase = "moved"; wst(st)
		local ok = sf(function() lo:set_actor_position(vector():set(job.nx, job.ny + 0.3, job.nz)) return true end)
		wr("player moved near " .. job.id .. " " .. tostring(ok))
	elseif st.phase == "moved" and dt < 13 and (st.on1 or 0) == 0 then
		track_first(job)
	elseif st.phase == "moved" and dt >= 13 and (st.on1 or 0) == 0 then
		-- every target / the item was looked at on the first tick it existed online (track_first); judged here, 5 s after the player arrived
		track_first(job)
		local n, maxdy, maxdxz, maxdn = first_summary()
		st.on1 = 1; wst(st)
		wr(string.format("ON1 %s first-online objects=%d max dy vs site=%.1f max horizontal=%.1f max dy vs own AI node=%.2f", job.id, n, maxdy, maxdxz, maxdn))
		if job.kind == "gen_find" then
			check(job, "item y sane when it comes online (not below / inside geometry)", n >= 1 and maxdy < 4, string.format("on %d dy %.1f", n, maxdy))
		else
			check(job, "targets y sane on their first online tick (not below / inside geometry)", n >= 1 and maxdy < 4, string.format("online %d max dy %.1f (horizontal %.1f)", n, maxdy, maxdxz))
			check(job, "targets stand on the AI mesh on their first online tick", n >= 1 and maxdn < 1.5, string.format("max dy vs own node %.2f", maxdn))
		end
	elseif st.phase == "moved" and dt >= 38 then
		st.phase = "s2"; wst(st)
		local i = survey(job)
		local fin = flag("RQG_" .. string.upper(job.id) .. "_DONE") or flag("RQG_" .. string.upper(job.id) .. "_FAIL")
		wr(string.format("S2 %s members=%d alive=%d online=%d item=%s item_on=%s maxdy_on=%.1f maxdy=%.1f finished=%s", job.id, i.members, i.alive, i.online, tostring(i.item), tostring(i.item_on), i.maxdy_on, i.maxdy, tostring(fin)))
		if job.kind == "gen_find" then
			check(job, "item still there after 30 s", i.item and not fin, string.format("item %s", tostring(i.item)))
		else
			check(job, "targets alive after 30 s (online)", i.members >= 1 and i.alive == i.members and i.online >= 1 and not fin, string.format("alive %d/%d online %d finished %s", i.alive, i.members, i.online, tostring(fin)))
		end
	elseif st.phase == "s2" and dt >= 40 then
		st.phase = "clean"; wst(st)
		cleanup(job)
		wr("cleanup " .. job.id)
	elseif st.phase == "clean" and dt >= 48 then
		st.job = st.job + 1; st.phase = "start"; wst(st)
	end
end
