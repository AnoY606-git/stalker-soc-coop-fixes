-- TEST ONLY (never shipped).  repeatable_quests stay-put + border test (FOSTER, v1.4: "all bandits of the repeatable jobs ended up outside the map").
-- Cordon, listen server: accept a bandit job by giving its accept flag (what the dialog does), keep the players at the start (the squad is offline,
-- like in a real game when the job is taken far away), let 180 s run at an accelerated game time, and check at 20 / 90 / 180 s after the accept:
--   every squad member is within 40 m of the site (the spawn spot), alive, and the map spot sits on the squad (level.map_has_object_spot).
-- The border itself is checked offline (tools/check_sites.py); here the site vertex read from the job must lie in the level and the members must still be
-- within 40 m of it, i.e. nothing walked away across a border.
-- run: powershell -NoProfile -ExecutionPolicy Bypass -File <tools>\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner rqstay -Mode listen -Clients 1 -Cfg no_respawn=1 -Cfg rq=rq_wolf_camp1 -Hooks <this file> -ExtraDir <stage>\gamedata -SoakSeconds 10 -CompareTimeout 10 -ResultDir <dir>
-- (stage = python build.py <out>\b.db --skip=soc_levels,weapon_upgrades,npc_attachments,arrival_facing --stage=<out>\stage)
local function cfgs(k, d) local v = qa.cfg and qa.cfg[k]; if v == nil or v == "" then return d end return v end
local function now() return os.time() end
local function sf(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function pth(n) return getFS():update_path("$logs$", n) end
local function wr(line)
	pcall(function() local f = io.open(pth("rq_stay.log"), "a"); if f then f:write(string.format("[%d] %s\n", now(), line)); f:close() end end)
end
local function rdst()
	local ok, r = pcall(function() local f = io.open(pth("rq_stay_state.txt"), "r"); if not f then return nil end local s = f:read("*a"); f:close(); return s end)
	local st = {}
	if ok and r then for k, v in string.gmatch(r, "([%w_]+)=([^\n]*)") do st[k] = tonumber(v) or v end end
	return st
end
local function wst(st)
	pcall(function()
		local f = io.open(pth("rq_stay_state.txt"), "w")
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
local function ids_with(prefix)
	local ids = {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true and string.sub(k, 1, #prefix) == prefix then
			local n = tonumber(string.sub(k, #prefix + 1)); if n then ids[#ids + 1] = n end
		end
	end
	return ids
end
local function dist(a, b) local dx, dz = a.x - b.x, a.z - b.z return math.sqrt(dx * dx + dz * dz) end

local function survey(rq, site)
	local key = "RQ_" .. string.upper(rq)
	local i = { squads = 0, members = 0, alive = 0, maxd = 0, spot_on_squad = 0 }
	for _, sid in ipairs(ids_with(key .. "_S")) do
		local sq = sf(function() return alife():object(sid) end)
		if sq ~= nil then
			i.squads = i.squads + 1
			if sf(function() return level.map_has_object_spot(sid, "red_location") end) ~= nil and sf(function() return level.map_has_object_spot(sid, "red_location") end) ~= 0 then
				i.spot_on_squad = i.spot_on_squad + 1
			end
			sf(function()
				for k in sq:squad_members() do
					local o = alife():object(k.id)
					if o ~= nil then
						i.members = i.members + 1
						if sf(function() return o:alive() end) then i.alive = i.alive + 1 end
						local d = dist(o.position, site)
						if d > i.maxd then i.maxd = d end
					end
				end
			end)
		end
	end
	return i
end

qa.hooks.rq_stay = function(t, lo)
	if not OnServer() then return end
	local A = actors()
	if #A < 1 then return end
	for _, v in ipairs(A) do pcall(function() v.health = 1 end) end
	local rq = cfgs("rq", "rq_wolf_camp1")
	local acc = "RQG_" .. string.upper(rq) .. "_ACC"
	local st = rdst()
	if (st.t0 or 0) == 0 then st.t0 = now(); wst(st); wr("start level " .. tostring(sf(level.name))) return end
	-- the site vertex of the job (read from the shipped ltx, the same way the script does)
	local ini = ini_file("misc\\coop_repeat_quests.ltx")
	local nums = {}
	for w in string.gmatch(ini:r_string(rq, "site"), "[-%d%.]+") do nums[#nums + 1] = tonumber(w) end
	local site = vector():set(nums[1], nums[2], nums[3])
	if (st.acc_t or 0) == 0 then
		if now() - st.t0 >= 20 then
			pcall(function() level.set_time_factor(60) end)   -- accelerated game time (the quest clock itself runs on real time)
			story_flags.give_flag(acc)
			st.acc_t = now(); wst(st)
			wr(string.format("accepted %s site (%.0f %.0f %.0f), player at %.0f %.0f", acc, site.x, site.y, site.z, A[1]:position().x, A[1]:position().z))
			qa.assert("players start more than 100 m from the site (squad stays offline)", dist(A[1]:position(), site) > 100, string.format("%.0f m", dist(A[1]:position(), site)))
		end
		return
	end
	local dt = now() - st.acc_t
	local function check(tag, key, need_spot)
		if (st[key] or 0) ~= 0 then return end
		st[key] = 1; wst(st)
		local i = survey(rq, site)
		wr(string.format("%s squads=%d members=%d alive=%d max_dist_from_site=%.1f spot_on_squad=%d", tag, i.squads, i.members, i.alive, i.maxd, i.spot_on_squad))
		qa.assert(rq .. " " .. tag .. ": squads exist and every member alive", i.squads >= 1 and i.members >= 1 and i.alive == i.members, string.format("squads %d members %d alive %d", i.squads, i.members, i.alive))
		qa.assert(rq .. " " .. tag .. ": every member within 40 m of the spawn spot (inside the border)", i.members >= 1 and i.maxd <= 40, string.format("max %.1f m", i.maxd))
		qa.assert(rq .. " " .. tag .. ": map spot is on the squad", i.spot_on_squad >= 1, string.format("%d squads carry the spot", i.spot_on_squad))
	end
	if dt >= 20 then check("t+20s", "c1") end
	if dt >= 90 then check("t+90s", "c2") end
	if dt >= 180 then check("t+180s", "c3"); st.done = 1; wst(st) end
end
