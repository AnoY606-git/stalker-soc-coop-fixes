-- TEST ONLY: death driver for the live console. Kills the real player again and again with different killers/patterns.
-- Appended after live_hooks.lua (start_live -Hooks). State survives the Lua VM restarts (every player death / load restarts the VM)
-- in $logs$/dd_state.txt, events go to $logs$/dd_events.log (opened/closed per line so a crash loses nothing).
-- Control file $logs$/dd_ctl.txt: "stop" pauses the driver, "run" continues, "only=<scenario>" restricts the scenario, "noload" skips save/load.
if not _G.dd then
_G.dd = { phase = "boot", last = 0 }
local dd = _G.dd

local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function lp(name) return getFS():update_path("$logs$", name) end
local function is_server() return safe(OnServer) == true end

local function ev(msg)
	local f = io.open(lp("dd_events.log"), "a")
	if f then f:write(string.format("[%s g=%.1f] %s\n", os.date("%H:%M:%S"), (safe(time_global) or 0) / 1000, tostring(msg))) f:close() end
end
dd.ev = ev

-- ---- persistent state (key=value lines)
local function st_read()
	local t = {}
	local f = io.open(lp("dd_state.txt"), "r")
	if f then
		for line in f:lines() do
			local k, v = string.match(line, "^([%w_]+)=(.*)$")
			if k then t[k] = v end
		end
		f:close()
	end
	return t
end
local function st_write(t)
	local f = io.open(lp("dd_state.txt"), "w")
	if f then
		local keys = {}
		for k in pairs(t) do keys[#keys + 1] = k end
		table.sort(keys)
		for _, k in ipairs(keys) do f:write(k, "=", tostring(t[k]), "\n") end
		f:close()
	end
end
local role_cfg = nil
local function ctl_read()
	if role_cfg == nil then
		role_cfg = {}
		local rf = io.open(lp("qa_role.txt"), "r")
		if rf then
			for line in rf:lines() do
				local k, v = string.match(line, "^%s*dd_([%w_]+)%s*=%s*(.-)%s*$")
				if k then role_cfg[k] = v end
			end
			rf:close()
		end
	end
	local c = {}
	for k, v in pairs(role_cfg) do c[k] = v end
	local f = io.open(lp("dd_ctl.txt"), "r")
	if not f then return c end
	for line in f:lines() do
		local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
		if k then c[k] = v else c[string.match(line, "^%s*(%S+)") or "?"] = true end
	end
	f:close()
	return c
end
local function num(t, k) return tonumber(t[k] or "0") or 0 end

-- ---- scenarios
-- plain: spawn a bandit, one lethal fire_wound hit with the bandit as draftsman
-- multi: k lethal hits in the same frame (k 2..6), draftsman bandit or self
-- explosion: explosion hits (1..3) in one frame
-- mixed: fire_wound + explosion + strike + wound in one frame
-- ai: 3 enemy bandits kill the player (fallback hits after 60 s)
-- respawn2: lethal hits in the very first tick after the respawn (2 in one frame)
-- killcall: game_object:kill() twice in the same frame
-- killhit: kill() and lethal hits in the same frame
-- selfonly: lethal hits with the player himself as draftsman, no npc
-- savekill: 1 bandit near, game_sv.saveGame, then the lethal hits 0..4 s later (FOSTER: death a few seconds after a quicksave)
-- saveload: 2 enemy bandits near, save, load (the orphan body appears in the next life)
local ORDER = { "plain", "multi", "savekill", "explosion", "mixed", "ai", "respawn2", "killcall", "savekill", "killhit", "selfonly", "saveload", "multi", "ai" }

local function real_player()
	if type(db.mp_actors) ~= "table" then return nil end
	local best
	for id, o in pairs(db.mp_actors) do
		if o ~= nil then
			local nm = safe(function() return string.lower(tostring(o:name())) end)
			local al = safe(function() return o:alive() end)
			local sec = safe(function() return o:section() end)
			if nm and string.find(nm, "^qa[a-d]$") and al and sec ~= "spectator" then best = o end
		end
	end
	return best
end

local function count_bodies()
	local n, names = 0, {}
	if type(db.mp_actors) == "table" then
		for id, o in pairs(db.mp_actors) do
			if o ~= nil and safe(function() return o:alive() end) then n = n + 1; names[#names + 1] = tostring(safe(function() return o:name() end)) .. "#" .. id end
		end
	end
	return n, table.concat(names, ",")
end

dd.powmul = 8
local function mkhit(po, who, htype, power, bone)
	local h = hit()
	h.draftsman = who or po
	h.type = hit[htype] or hit.fire_wound
	h.direction = vector():set(0, 0, 1)
	h:bone(bone or "bip01_spine")
	h.power = (power or 5) * (dd.powmul or 1)
	h.impulse = 10
	return h
end

local function spawn_enemy(po, n)
	local ids = {}
	for k = 1, n do
		local id = safe(function() return live.spawn("sim_default_bandit_1") end)
		if id then ids[#ids + 1] = id end
	end
	return ids
end
local function npc_obj(id) return id and safe(function() return level.object_by_id(id) end) or nil end
local function all_online(ids)
	for _, id in ipairs(ids) do if npc_obj(id) == nil then return false end end
	return #ids > 0
end
local function make_enemy(ids, po)
	for _, id in ipairs(ids) do
		local o = npc_obj(id)
		if o then pcall(function() o:set_relation(game_object.enemy, po) end) end
	end
end

local S = nil -- persistent state table
local V = {}  -- per VM variables

local function init()
	S = st_read()
	V.t0 = time_global()
	local pend = S.pending or ""
	S.vms = num(S, "vms") + 1
	if pend ~= "" then
		if pend == "load" then
			S.loads = num(S, "loads") + 1
			S.after_load = 1
			ev("VM start #" .. S.vms .. " after LOAD (loads=" .. S.loads .. ")")
		elseif pend == "levelchange" then
			ev("VM start #" .. S.vms .. " after level change, level=" .. tostring(safe(level.name)))
		else
			S.deaths = num(S, "deaths") + 1
			ev("VM start #" .. S.vms .. " after DEATH #" .. S.deaths .. " (scenario " .. pend .. ")")
		end
		S.pending = ""
	else
		ev("VM start #" .. S.vms .. " (no pending scenario) level=" .. tostring(safe(level.name)))
	end
	st_write(S)
	dd.S = S
end

local function choose()
	local c = ctl_read()
	if c.stop then return nil end
	local n = num(S, "lives") + 1
	S.lives = n
	local sc
	if c.only and c.only ~= "" then sc = c.only
	elseif num(S, "after_load") == 1 then
		sc = ({ "ai", "plain", "multi", "respawn2" })[(num(S, "loads") % 4) + 1]
		V.after_load = true
		S.after_load = 0
	else
		sc = ORDER[((n - 1) % #ORDER) + 1]
	end
	if sc == "saveload" and (c.noload or num(S, "since_load") < 6) then sc = "multi" end
	if sc == "saveload" then S.since_load = 0 else S.since_load = num(S, "since_load") + 1 end
	return sc
end

local function begin_scenario(po)
	local sc = choose()
	if not sc then return end
	V.sc = sc
	V.po = po
	V.t_sc = time_global()
	math.randomseed((num(S, "lives") * 7919) + 13)
	V.k = math.random(2, 6)
	V.who = (math.random(1, 3) == 1) and "self" or "npc"
	local cc = ctl_read()
	if tonumber(cc.k or "") then V.k = tonumber(cc.k) end
	if cc.who == "self" or cc.who == "npc" then V.who = cc.who end
	if tonumber(cc.powmul or "") then dd.powmul = tonumber(cc.powmul) end
	S.pending = sc
	S["c_" .. sc] = num(S, "c_" .. sc) + 1
	st_write(S)
	local nb, names = count_bodies()
	ev(string.format("LIFE #%d scenario=%s k=%d who=%s after_load=%s bodies_alive=%d [%s] player=%s id=%s hp=%.2f", num(S, "lives"), sc, V.k, V.who, tostring(V.after_load), nb, names,
		tostring(safe(function() return po:name() end)), tostring(safe(function() return po:id() end)), safe(function() return po.health end) or -1))
	if sc == "respawn2" or sc == "selfonly" or sc == "killcall" or sc == "killhit" then V.phase = "act"
	elseif sc == "saveload" then V.ids = spawn_enemy(po, 2); V.phase = "prep"
	elseif sc == "ai" then V.ids = spawn_enemy(po, 3); V.phase = "prep"
	else V.ids = spawn_enemy(po, 1); V.phase = "prep" end
end

local function act(po)
	local sc = V.sc
	local npc = npc_obj(V.ids and V.ids[1])
	local who = (V.who == "npc" and npc) or po
	local hits = 0
	local function H(t, p, w) local ok = pcall(function() po:hit(mkhit(po, w or who, t, p)) end) hits = hits + 1 return ok end
	if sc == "plain" or sc == "savekill" then H("fire_wound", 5)
	elseif sc == "multi" then for i = 1, V.k do H("fire_wound", 5) end
	elseif sc == "explosion" then for i = 1, math.random(1, 3) do H("explosion", 5) end
	elseif sc == "mixed" then H("fire_wound", 5) H("explosion", 5) H("strike", 5) H("wound", 5)
	elseif sc == "respawn2" then H("fire_wound", 5) H("fire_wound", 5)
	elseif sc == "selfonly" then for i = 1, V.k do H("fire_wound", 5, po) end
	elseif sc == "killcall" then
		local w = npc or po
		pcall(function() po:kill(w) end) pcall(function() po:kill(w) end) hits = 2
	elseif sc == "killhit" then
		pcall(function() po:kill(po) end) H("fire_wound", 5, po) H("fire_wound", 5, po) pcall(function() po:kill(po) end)
	else H("fire_wound", 5) end
	ev(string.format("ACT %s: %d call(s) in one frame, player alive_now=%s hp=%.3f", sc, hits, tostring(safe(function() return po:alive() end)), safe(function() return po.health end) or -1))
	V.phase = "wait_death"; V.t_act = time_global()
end

local function tick()
	if not is_server() then return end
	local now = time_global()
	if now - dd.last < 100 then return end
	dd.last = now
	if dd.disabled then return end
	if not S then if now < 4000 then return end init() end
	local c = ctl_read()
	if c.stop then return end
	local po = real_player()
	-- death WITHOUT a Lua VM restart (the dedicated live server keeps its VM): count it, release the test npcs, start the next life
	if V.po and V.sc and V.phase ~= "loadwait" and V.phase ~= "loading" then
		local al = safe(function() return V.po:alive() end)
		local gone = safe(function() return V.po:id() end) == nil
		if not al or gone then
			if not V.dead_t then V.dead_t = now; ev(string.format("player dead (scenario %s, phase %s, %.1f s after the scenario began)", V.sc, tostring(V.phase), (now - V.t_sc) / 1000)) end
			if now - V.dead_t < 2500 then return end
			S.deaths = num(S, "deaths") + 1
			S.pending = ""
			st_write(S)
			for _, id in ipairs(V.ids or {}) do
				pcall(function() local se = alife():object(id) if se then alife():release(se, true) end end)
			end
			ev(string.format("DEATH #%d done (scenario %s, same VM)", S.deaths, V.sc))
			for k in pairs(V) do V[k] = nil end
			V.phase = "boot"
			return
		end
	end
	if V.phase == nil or V.phase == "boot" then
		if po == nil then return end
		if V.t_alive == nil then V.t_alive = now; V.alive_id = safe(function() return po:id() end) end
		-- scenario-specific minimum age of the new body: respawn2 acts at once, the others wait 1.5 .. 4 s so the body is settled
		local age = (now - V.t_alive) / 1000
		math.randomseed(num(S, "lives") * 31 + 5)
		V.minage = V.minage or (tonumber(c.minage or "") or (math.random(15, 40) / 10))
		if age < 0.2 then return end
		local nextsc = (c.only and c.only ~= "" and c.only) or ORDER[((num(S, "lives")) % #ORDER) + 1]
		if nextsc ~= "respawn2" and age < V.minage then return end
		V.phase = "pick"
	end
	if V.phase == "pick" then
		if po == nil then V.phase = "boot"; V.t_alive = nil return end
		begin_scenario(po)
		if V.phase == "pick" then return end
	end
	if V.phase == "prep" then
		po = po or V.po
		if not safe(function() return V.po:alive() end) then V.phase = "wait_death" return end
		local on = all_online(V.ids)
		if not on and (now - V.t_sc) < 20000 then return end
		if V.sc == "ai" or V.sc == "saveload" then make_enemy(V.ids, V.po) end
		if V.sc == "saveload" then
			if (now - V.t_sc) < 6000 then return end
			ev("saveload: bandits online=" .. tostring(on) .. ", saving then loading")
			S.pending = "load"; st_write(S)
			local ok1 = pcall(function() game_sv.saveGame(0) end)
			V.phase = "loadwait"; V.t_save = now
			ev("saveGame called ok=" .. tostring(ok1))
			return
		end
		if V.sc == "savekill" then
			local ok1 = pcall(function() game_sv.saveGame(0) end)
			V.phase = "savewait"; V.t_save = now; V.delay = (V.k - 2) * 1000
			ev("savekill: saveGame ok=" .. tostring(ok1) .. ", lethal hits in " .. V.delay .. " ms")
			return
		end
		if V.sc == "ai" then V.phase = "wait_death"; V.t_act = now; ev("ai: " .. #V.ids .. " enemy bandits online=" .. tostring(on) .. ", waiting for them to kill the player") return end
		V.phase = "act"
	end
	if V.phase == "savewait" then
		if now - V.t_save >= V.delay then V.phase = "act" end
		return
	end
	if V.phase == "loadwait" then
		if now - V.t_save > 3000 then
			local ok2 = pcall(function() game_sv.loadLastSave(0) end)
			ev("loadLastSave called ok=" .. tostring(ok2))
			V.phase = "loading"
		end
		return
	end
	if V.phase == "act" then
		local p2 = V.po
		if not safe(function() return p2:alive() end) then V.phase = "wait_death" return end
		act(p2)
		return
	end
	if V.phase == "wait_death" then
		local alive = safe(function() return V.po:alive() end)
		local waited = (now - (V.t_act or now)) / 1000
		if not alive then
			if not V.logged_dead then V.logged_dead = true; ev(string.format("player dead %.1f s after the act, waiting for the VM restart", waited)) end
			return
		end
		if V.sc == "ai" and waited > 60 and not V.forced then
			V.forced = true
			ev("ai: no kill after 60 s, forcing lethal hits")
			act(V.po)
		elseif waited > 10 and not V.forced and V.sc ~= "ai" then
			V.forced = true
			ev("no death " .. string.format("%.0f", waited) .. " s after the act (" .. V.sc .. "), forcing")
			act(V.po)
		elseif waited > 150 then
			if not V.warned then V.warned = true; ev("WARN: still alive 150 s after the act, health=" .. tostring(safe(function() return V.po.health end))) end
		end
		return
	end
end

do
	local ok, err = pcall(function() level.add_call(tick, function() end) end)
	local f = io.open(getFS():update_path("$logs$", "dd_load.txt"), "a")
	if f then f:write("dd_driver loaded, add_call ", ok and "ok" or tostring(err), "\n") f:close() end
end
end
