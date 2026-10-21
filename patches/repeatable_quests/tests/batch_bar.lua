-- TEST ONLY (never shipped).  repeatable_quests batch test: accepts every generated job of one level one after another (what the dialog does:
-- it gives the job's accept flag) and checks per job: targets / item spawned at the site, map spot, no other NPC within 80 m, no anomaly
-- zone within 15 m, sane y; then 30 s later (player moved next to the site so the targets are online): alive, y sane. Then it removes the
-- targets and goes on with the next job.  Bar: start on Cordon and travel by party vote (the Bar's alife only comes online that way).
local JOBS = {
	{id = "rq_ska_kill", kind = "gen_kill", x = -24.5, y = 1.0, z = 324.8, nx = -0.0, ny = -2.8, nz = 323.4},
	{id = "rq_bar_kill2", kind = "gen_kill", x = -24.5, y = 1.0, z = 324.8, nx = -0.0, ny = -2.8, nz = 323.4},
	{id = "rq_vor_camp1", kind = "gen_camp", x = -24.5, y = 1.0, z = 324.8, nx = -0.0, ny = -2.8, nz = 323.4},
	{id = "rq_bar_defend", kind = "gen_defend", x = -24.5, y = 1.0, z = 324.8, nx = -0.0, ny = -2.8, nz = 323.4},
	{id = "rq_vor_defend", kind = "gen_defend", x = -24.5, y = 1.0, z = 324.8, nx = -0.0, ny = -2.8, nz = 323.4},
	{id = "rq_bar_kill1", kind = "gen_kill", x = 23.1, y = 5.1, z = 360.5, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_pet_kill", kind = "gen_kill", x = 23.1, y = 5.1, z = 360.5, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_vor_camp3", kind = "gen_camp", x = 23.1, y = 5.1, z = 360.5, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_vor_find", kind = "gen_find", x = 23.1, y = 5.1, z = 360.5, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_vor_kill", kind = "gen_kill", x = 75.6, y = 2.7, z = 336.7, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_vor_camp2", kind = "gen_camp", x = 75.6, y = 2.7, z = 336.7, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_inf_kill", kind = "gen_kill", x = 75.6, y = 2.7, z = 336.7, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_inf_find", kind = "gen_find", x = 75.6, y = 2.7, z = 336.7, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_zho_find", kind = "gen_find", x = 75.6, y = 2.7, z = 336.7, nx = 53.2, ny = 3.6, nz = 348.6},
	{id = "rq_inf_camp", kind = "gen_camp", x = 238.7, y = 4.5, z = -156.1, nx = 203.7, ny = 3.4, nz = -144.2},
	{id = "rq_inf_defend", kind = "gen_defend", x = 238.7, y = 4.5, z = -156.1, nx = 203.7, ny = 3.4, nz = -144.2},
	{id = "rq_bar_camp1", kind = "gen_camp", x = 191.1, y = 4.0, z = -144.2, nx = 191.8, ny = 1.8, nz = -121.1},
	{id = "rq_bar_camp2", kind = "gen_camp", x = 2.8, y = -0.1, z = 239.4, nx = 11.9, ny = -1.5, nz = 275.8},
	{id = "rq_hun_camp", kind = "gen_camp", x = 2.8, y = -0.1, z = 239.4, nx = 11.9, ny = -1.5, nz = 275.8},
}
local LVL = "coop_l05_bar"
local TRAVEL = true
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
		story_flags.give_flag(acc)
		wr("JOB " .. job.id .. " accepted " .. acc)
	elseif st.phase == "accepted" and dt >= 6 then
		st.phase = "s1"; wst(st)
		local i = survey(job)
		wr(string.format("S1 %s squads=%d members=%d item=%s maxd=%.1f maxdy=%.1f other=%.0f (%s) zone=%.0f (%s) spot=%s", job.id, i.n_squads, i.members, tostring(i.item), i.maxd, i.maxdy, i.mind_other, i.other, i.zone, i.zname, tostring(i.spot)))
		if job.kind == "gen_find" then
			check(job, "item spawned at the site", i.item and i.maxd < 3, string.format("item %s dist %.1f", tostring(i.item), i.maxd))
		else
			check(job, "targets spawned at the site", i.n_squads >= 1 and i.members >= 1 and i.maxd < 5, string.format("squads %d members %d dist %.1f", i.n_squads, i.members, i.maxd))
		end
		check(job, "map spot on the target", i.spot, tostring(i.spot))
		check(job, "no other NPC within 80 m", i.mind_other >= 80, string.format("%.0f (%s)", i.mind_other, i.other))
		check(job, "no anomaly zone within 15 m", i.zone >= 15, string.format("%.0f (%s)", i.zone, i.zname))
		check(job, "y sane vs the site (server)", i.maxdy < 3, string.format("max dy %.1f", i.maxdy))
	elseif st.phase == "s1" and dt >= 7 then
		st.phase = "moved"; wst(st)
		local ok = sf(function() lo:set_actor_position(vector():set(job.nx, job.ny + 0.3, job.nz)) return true end)
		wr("player moved near " .. job.id .. " " .. tostring(ok))
	elseif st.phase == "moved" and dt >= 12 and (st.on1 or 0) == 0 then
		-- first look right after the player arrived: the targets came online at their spawn place (before they run at the player)
		local i = survey(job)
		if i.online >= 1 or i.item_on or dt >= 22 then
			st.on1 = 1; wst(st)
			wr(string.format("ON1 %s online=%d item_on=%s maxdy_on=%.1f", job.id, i.online, tostring(i.item_on), i.maxdy_on))
			if job.kind == "gen_find" then
				check(job, "item y sane when online (not below / inside geometry)", i.item_on and i.maxdy_on < 4, string.format("on %s dy %.1f", tostring(i.item_on), i.maxdy_on))
			else
				check(job, "targets y sane when they come online (not below / inside geometry)", i.online >= 1 and i.maxdy_on < 4, string.format("online %d max dy %.1f", i.online, i.maxdy_on))
			end
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
