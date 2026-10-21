-- TEST ONLY (never shipped).  repeatable_quests map spots on a dedicated server with two real clients (run_coop -Clients 2, dedicated):
-- for each job the server accepts it, the clients must show a map spot (level.map_has_object_spot) and, after the job ended in a given
-- way, no spot any more.  Ends: 1 targets removed (killed by others), 2 hand-in (done flag), 3 cancel (fail flag).
local SC = {
	{ id = "rq_sid_kill",   typ = "red_location",   how = "targets killed by others" },
	{ id = "rq_shu_find",   typ = "green_location", how = "hand-in (done flag)" },
	{ id = "rq_wolf_camp1", typ = "red_location",   how = "cancel (fail flag)" },
}
local function now() return os.time() end
local function sf(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function pth(n) return getFS():update_path("$logs$", n) end
local function wr(line)
	pcall(function() local f = io.open(pth("rq_spot.log"), "a"); if f then f:write(string.format("[%d] %s\n", now(), line)); f:close() end end)
end
local function rdst()
	local ok, r = pcall(function() local f = io.open(pth("rq_sstate.txt"), "r"); if not f then return nil end local s = f:read("*a"); f:close(); return s end)
	local st = {}
	if ok and r then for k, v in string.gmatch(r, "([%w_]+)=([^\n]*)") do st[k] = tonumber(v) or v end end
	return st
end
local function wst(st)
	pcall(function() local f = io.open(pth("rq_sstate.txt"), "w"); if f then for k, v in pairs(st) do f:write(k, "=", tostring(v), "\n") end f:close() end end)
end
local function flag(n) return sf(story_flags.has_flag, n) == true end
local function ids_with(prefix)
	local ids = {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true and string.sub(k, 1, #prefix) == prefix then
			local n = tonumber(string.sub(k, #prefix + 1)); if n then ids[#ids + 1] = n end
		end
	end
	return ids
end
local function has_spot(id, typ) return (sf(level.map_has_object_spot, id, typ) or 0) ~= 0 end
local function actors()
	local out = {}
	if type(db.mp_actors) == "table" then
		for id, v in pairs(db.mp_actors) do if v ~= nil and sf(function() return v:alive() end) then out[#out + 1] = v end end
	end
	return out
end

-- read back the hint the engine is given for a spot (server side)
if not _G.rq_spot_wrapped then
	_G.rq_spot_wrapped = true
	pcall(function()
		local orig = level.map_add_object_spot_ser
		level.map_add_object_spot_ser = function(id, typ, hint)
			wr("ADD_SPOT obj=" .. tostring(id) .. " type=" .. tostring(typ) .. " hint=[" .. string.gsub(tostring(hint), string.char(10), " | ") .. "]")
			return orig(id, typ, hint)
		end
	end)
end
local C = _G.rq_spot_client or { cache = {}, t = {} }
_G.rq_spot_client = C

qa.hooks.rq_spot = function(t, lo)
	local role = tostring(qa.cfg.role)
	if OnServer() then
		-- ---------------- server: drives the scenarios
		local A = actors()
		if #A < 1 then return end
		for _, v in ipairs(A) do pcall(function() v.health = 1 end) end
		local st = rdst()
		if (st.arrive or 0) == 0 then st.arrive = now(); wst(st); return end
		if now() - st.arrive < 25 then return end
		st.k = st.k or 1
		local sc = SC[st.k]
		if sc == nil then
			if (st.fin or 0) == 0 then st.fin = 1; wst(st); wr("SERVER done") end
			return
		end
		local key = "RQ_" .. string.upper(sc.id)
		local p = "RQG_" .. string.upper(sc.id)
		st.phase = st.phase or "start"
		local dt = now() - (st.t0 or now())
		if st.phase == "start" then
			st.phase = "acc"; st.t0 = now(); wst(st)
			story_flags.give_flag(p .. "_ACC")
			wr(string.format("SC%d %s accepted", st.k, sc.id))
		elseif st.phase == "acc" and dt >= 10 then
			st.phase = "before"; wst(st)
			local ids = ids_with(key .. "_P")
			local srv = {}
			for _, id in ipairs(ids) do srv[#srv + 1] = id .. ":" .. tostring(has_spot(id, sc.typ)) end
			wr(string.format("SC%d spot ids %s (server has_spot: %s)", st.k, table.concat(sf(function() local o = {} for _, i in ipairs(ids) do o[#o + 1] = tostring(i) end return o end) or {}, ","), table.concat(srv, ",")))
			story_flags.give_flag("QA_RQS_B" .. st.k)
		elseif st.phase == "before" and dt >= 30 then
			st.phase = "end"; wst(st)
			if st.k == 1 then
				for _, sid in ipairs(ids_with(key .. "_S")) do
					local sq = sf(function() return alife():object(sid) end)
					if sq ~= nil then sf(function() sim_board.get_sim_board():remove_squad(sq) end) end
				end
			elseif st.k == 2 then
				story_flags.give_flag(p .. "_DONE")
			else
				story_flags.give_flag(p .. "_FAIL")
			end
			wr(string.format("SC%d ended: %s", st.k, sc.how))
		elseif st.phase == "end" and dt >= 45 then
			st.phase = "after"; wst(st)
			local left = {}
			for _, id in ipairs(C.sids or {}) do left[#left + 1] = tostring(id) .. ":" .. tostring(has_spot(id, sc.typ)) end
			wr(string.format("SC%d server after: P flags left %d, spots %s", st.k, #ids_with(key .. "_P"), table.concat(left, ",")))
			story_flags.give_flag("QA_RQS_A" .. st.k)
		elseif st.phase == "after" and dt >= 75 then
			st.k = st.k + 1; st.phase = "start"; wst(st)
		end
		-- remember the spot objects for the "after" printout
		local ids = ids_with(key .. "_P")
		if #ids > 0 then C.sids = ids end
		return
	end
	-- ---------------- client: own checks of what it sees
	if lo == nil then return end
	for k, sc in ipairs(SC) do
		local key = "RQ_" .. string.upper(sc.id)
		if flag("QA_RQS_B" .. k) and not C["b" .. k] then
			local ids = ids_with(key .. "_P")
			C.t["b" .. k] = C.t["b" .. k] or now()
			local seen = false
			for _, id in ipairs(ids) do
				C.cache[k] = C.cache[k] or {}
				C.cache[k][id] = true
				if has_spot(id, sc.typ) then seen = true end
			end
			if seen then
				C["b" .. k] = true
				qa.assert(string.format("SC%d %s: client shows the map spot", k, sc.id), true, "spot objects " .. #ids .. " after " .. (now() - C.t["b" .. k]) .. " s")
			elseif now() - C.t["b" .. k] > 25 then
				C["b" .. k] = true
				qa.assert(string.format("SC%d %s: client shows the map spot", k, sc.id), false, "P flags " .. #ids .. " has_spot never true")
			end
		end
		if flag("QA_RQS_A" .. k) and not C["a" .. k] then
			C.t["a" .. k] = C.t["a" .. k] or now()
			local any = false
			local n = 0
			for id in pairs(C.cache[k] or {}) do n = n + 1; if has_spot(id, sc.typ) then any = true end end
			if not any and n > 0 then
				C["a" .. k] = true
				qa.assert(string.format("SC%d %s: spot gone on the client after %s", k, sc.id, sc.how), true, "checked " .. n .. " spot object(s)")
			elseif now() - C.t["a" .. k] > 20 then
				C["a" .. k] = true
				qa.assert(string.format("SC%d %s: spot gone on the client after %s", k, sc.id, sc.how), false, "cached " .. n .. " still has spot=" .. tostring(any))
			end
		end
	end
end
