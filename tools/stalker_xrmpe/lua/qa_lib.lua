-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): qa_lib, a library of test-bot helpers for Shadow of COOP on xrMPE 0.9.
-- Docs: lua\QA_LIB.md.  Proven by lua\qa_lib_smoke.lua (one Cordon listen-mode run, PASS lines in QA_LIB.md).
--
-- LOAD IT (appended after qa_harness.lua, before your hooks), either way:
--   1. first line of your hooks file:   --@qa_lib      (qa_build.py then appends qa_lib.lua before your file; opt-in, nothing else changes)
--   2. or pass it yourself first:       run_coop.ps1 -Hooks "C:\...\lua\qa_lib.lua,C:\...\my_hooks.lua"
-- Then use the global  qa_lib  (alias  qa.lib):   local L = qa_lib
--
-- RULES THAT MATTER
--   * A level change restarts the Lua VM (harness and hooks reload, "previous nil" in qa_events.log).  Anything that must survive
--     a level change goes into the persisted state: L.state_set / L.state_get (file $logs$\qa_lib_state.txt).
--   * Functions that need game time to pass (travel, wait, hits_to_kill, open_talk, screenshot, save ...) return an ACTION.  Run
--     them as steps of  L.task("name", { function(c) return L.travel("gar") end, function(c, ok, why) ... end }).  No coroutines:
--     they do not work in xrMPE 0.9 (see "actions, sequences, tasks" below).  They are marked ACTION in the comments.
--   * The engine's Lua health setter is RELATIVE: obj.health = x ADDS x.  Use L.set_health(obj, value).
--   * Do not call OnServer()/getFS() at file top level; this file only defines functions at load time.
--   * Server-side functions (spawn, give_item, hit, kill, save ...) need to run where alife() exists: the listen host or the dedicated
--     server role (role S).  Client-side ones (open_talk, screenshot, local_player) run on a client.
-- Every function logs a "LIB ..." line into qa_events.log.  Functions return a value, or nil/false plus an error string.
-------------------------------------------------------------------------------------------------------
if not _G.qa_lib then
local L = { version = "1.2" }
_G.qa_lib = L
if _G.qa then _G.qa.lib = L end

-- ---------------------------------------------------------------------------------------------------- basics
local function try(f, ...)
	local ok, a, b, c = pcall(f, ...)
	if ok then return true, a, b, c end
	return false, a
end
L.try = try

local function ev(msg)
	if _G.qa and qa.event then qa.event("LIB " .. tostring(msg)) end
end
L.ev = ev

-- qa.once de-duplication.  run_coop appends the hooks file to THREE shipped scripts (xr_conditions, game_cl, bind_stalker), and those scripts are
-- loaded at different times, so one file runs its top-level qa.once("x", ...) up to three times in the same Lua VM: if the first copy already
-- fired, the next load registers it AGAIN and the body ran a second time about a second later (duplicate teleports, spawns, asserts: seen
-- 2026-10-21).  With qa_lib loaded, a second qa.once with the same name in the same VM is ignored (a new VM, after a level change or a
-- player death, starts with an empty list, so the body still runs once per VM, as before).  L.once(name, fn) is the same function.
L._once_seen = {}
if _G.qa and type(qa.once) == "function" and not qa._once_wrapped then
	local orig_once = qa.once
	qa._once_wrapped = true
	qa.once = function(name, fn)
		if L._once_seen[name] then
			ev("once " .. tostring(name) .. ": duplicate registration ignored (hooks file loaded by another script)")
			return
		end
		L._once_seen[name] = true
		return orig_once(name, fn)
	end
end
function L.once(name, fn) return qa.once(name, fn) end

local function fmt_pos(p)
	if p == nil then return "nil" end
	return string.format("%.1f,%.1f,%.1f", p.x, p.y, p.z)
end
L.fmt_pos = fmt_pos

function L.now_ms() return time_global() end

function L.vec(x, y, z)
	if type(x) == "table" then x, y, z = x.x or x[1], x.y or x[2], x.z or x[3] end
	return vector():set(x, y, z)
end

function L.on_server() local ok, r = try(OnServer) return ok and r == true end
function L.is_dedicated() local ok, r = try(IsDedicatedServer) return ok and r == true end
function L.level_name() local ok, r = try(level.name) if ok then return r end return nil end

-- Known spots (x, y, z) so a test does not have to hunt for coordinates.  Pass them to L.teleport / L.spawn / L.npcs_near / L.dump_npcs.
L.PLACES = {
	cordon_fire = { -206.9, -19.6, -140.1 },       -- the rookie village campfire (esc_campfire), about 10 stalkers sit and walk around it
	cordon_trader_bunker = { -243.0, -24.2, -135.0 },  -- Sidorovich's bunker (used by qa_lib_smoke.lua)
}

function L.dist3(a, b) local dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z return math.sqrt(dx * dx + dy * dy + dz * dz) end
function L.dist2(a, b) local dx, dz = a.x - b.x, a.z - b.z return math.sqrt(dx * dx + dz * dz) end

-- ---------------------------------------------------------------------------------------------------- persisted state
-- key=value lines in $logs$\qa_lib_state.txt.  Values are strings (numbers come back as numbers when they look like one).
local STATE_FILE = "qa_lib_state.txt"
local function state_path() return getFS():update_path("$logs$", STATE_FILE) end

function L.state()
	local st = {}
	local ok = pcall(function()
		local f = io.open(state_path(), "r")
		if not f then return end
		for line in f:lines() do
			local k, v = string.match(line, "^([%w_%.%-]+)=(.*)$")
			if k then st[k] = tonumber(v) or v end
		end
		f:close()
	end)
	return st
end

local function state_write(st)
	pcall(function()
		local f = io.open(state_path(), "w")
		if not f then return end
		local keys = {}
		for k in pairs(st) do keys[#keys + 1] = k end
		table.sort(keys)
		for _, k in ipairs(keys) do f:write(k, "=", tostring(st[k]), "\n") end
		f:close()
	end)
end

function L.state_get(key, default)
	local v = L.state()[key]
	if v == nil then return default end
	return v
end

function L.state_set(key, value)
	local st = L.state()
	if value == nil then st[key] = nil else st[key] = string.gsub(tostring(value), "[\r\n]", " ") end
	state_write(st)
end

function L.state_clear() state_write({}) end

-- ---------------------------------------------------------------------------------------------------- actions, sequences, tasks
-- NO COROUTINES: in xrMPE 0.9's LuaJIT a coroutine body never runs (coroutine.resume returns "attempt to call a nil value") or the
-- engine crashes in lua_getinfo (both seen 2026-10-20).  Time is handled with ACTIONS instead:
--   an action is a table { tick = function(self, now_ms) return done, results... end }.  L.wait / L.wait_for / L.seq make them, and every
--   library function that needs game time to pass (travel, hits_to_kill, teleport, save, open_talk, screenshot, kill_player) RETURNS one.
--   L.seq{ step, step, "label", step ... } runs steps one after another.  A step is function(c, ...) where c is a table shared by the
--   steps of that sequence and ... are the results of the action the previous step returned.  What a step returns decides what happens:
--     an action            -> it is ticked until done, its results go to the next step
--     L.again(sec)         -> run this same step again after sec seconds (loops)
--     L.jump("label")      -> continue at the step after that label string
--     L.done(...)          -> end the sequence; ... are its results
--     anything else        -> passed as arguments to the next step, which runs at once (same tick)
--   L.task(name, steps_or_action) ticks it once a second (harness tick) and turns an error into a FAIL assert.
local tasks = {}

local function pack(...) return { n = select("#", ...), ... } end
L.pack = pack

local function is_action(a) return type(a) == "table" and type(a.tick) == "function" end
L.is_action = is_action

function L.action(tick_fn, name) return { tick = tick_fn, name = name or "action" } end

-- L.wait(sec): action, done after sec seconds (resolution: the harness tick, 1 s).  Result: true.
function L.wait(sec)
	return L.action(function(self, now)
		if self.t == nil then self.t = now + (sec or 1) * 1000 end
		if now >= self.t then return true, true end
		return false
	end, "wait")
end

-- L.wait_for(cond_fn, timeout_s): action, polls cond_fn() each tick.  Result: true when it returned true, false on timeout.
function L.wait_for(cond, timeout_s)
	return L.action(function(self, now)
		if self.dl == nil then self.dl = now + (timeout_s or 30) * 1000 end
		local ok, r = pcall(cond)
		if ok and r then return true, true end
		if now >= self.dl then return true, false end
		return false
	end, "wait_for")
end

-- L.now(...): action that is done at once with the given results (lets a step return either an action or a ready answer)
function L.now(...)
	local r = pack(...)
	return L.action(function() return true, unpack(r, 1, r.n) end, "now")
end

function L.done(...) return { __ctl = "done", r = pack(...) } end
function L.jump(label) return { __ctl = "jump", label = label } end
function L.again(sec) return { __ctl = "again", sec = sec or 0 } end

local function seq_tick(self, now)
	for _ = 1, 200 do
		if self.sub ~= nil then
			local r = pack(self.sub.tick(self.sub, now))
			if not r[1] then return false end
			self.sub = nil
			if self.drop then self.drop = false self.args = pack() else self.args = pack(unpack(r, 2, r.n)) end
		end
		if self.i > #self.list then return true, unpack(self.ret, 1, self.ret.n) end
		local cur = self.i
		self.i = cur + 1
		local args = self.args
		self.args = pack()
		local res = pack(self.list[cur](self.ctx, unpack(args, 1, args.n)))
		local a = res[1]
		if is_action(a) then
			self.sub = a
		elseif type(a) == "table" and a.__ctl == "done" then
			self.ret = a.r
			self.i = #self.list + 1
		elseif type(a) == "table" and a.__ctl == "jump" then
			local to = self.labels[a.label]
			if to == nil then error("qa_lib.seq " .. self.name .. ": no label " .. tostring(a.label)) end
			self.i = to
		elseif type(a) == "table" and a.__ctl == "again" then
			self.i = cur
			if a.sec > 0 then self.sub = L.wait(a.sec) self.drop = true else return false end
		else
			self.args = res
		end
	end
	return false
end

-- L.seq(steps [, name]) -> action.  steps: list of step functions and label strings (see above).  A single function is a one-step list.
function L.seq(steps, name)
	if type(steps) == "function" then steps = { steps } end
	local list, labels = {}, {}
	for _, s in ipairs(steps) do
		if type(s) == "string" then labels[s] = #list + 1 else list[#list + 1] = s end
	end
	return { tick = seq_tick, name = name or "seq", list = list, labels = labels, i = 1, args = pack(), ret = pack(), ctx = {} }
end

-- L.protect(action, name) -> action.  An error inside it becomes one FAIL assert "<name> finished without error" and the action ends
-- with (nil, err) instead of killing the whole task (use it for independent parts of a long test).
function L.protect(act, name)
	if type(act) == "table" and not is_action(act) then act = L.seq(act, name) end
	return L.action(function(self, now)
		local r = pack(pcall(act.tick, act, now))
		if not r[1] then
			ev("PROTECT " .. tostring(name) .. " ERROR " .. tostring(r[2]))
			if qa and qa.assert then qa.assert(tostring(name) .. " finished without error", false, tostring(r[2])) end
			return true, nil, r[2]
		end
		return unpack(r, 2, r.n)
	end, "protect")
end

local function task_fail(tk, err)
	ev("TASK " .. tk.name .. " ERROR " .. tostring(err))
	if qa and qa.assert then qa.assert("task " .. tk.name .. " finished without error", false, tostring(err)) end
end

local function task_tick(tk)
	local r = pack(pcall(tk.act.tick, tk.act, time_global()))
	if not r[1] then
		tk.dead = true
		task_fail(tk, r[2])
	elseif r[2] then
		tk.dead = true
		tk.result = pack(unpack(r, 3, r.n))
		ev("TASK " .. tk.name .. " done")
	end
end

-- L.task(name, steps_or_action) -> task table { name, dead, result }.  The first slice runs at once, then once per harness tick.
function L.task(name, steps)
	local act = is_action(steps) and steps or L.seq(steps, name)
	local tk = { name = tostring(name), act = act }
	tasks[#tasks + 1] = tk
	ev("TASK " .. tk.name .. " start")
	task_tick(tk)
	return tk
end

local function sched()
	for i = #tasks, 1, -1 do
		local tk = tasks[i]
		if tk.dead then table.remove(tasks, i) else task_tick(tk) end
	end
end
L._sched = sched
qa.hooks.qa_lib_sched = function(t, lo)
	local ok, err = pcall(sched)
	if not ok then ev("scheduler error " .. tostring(err)) end
end

-- ---------------------------------------------------------------------------------------------------- players
local function obj_alive(o) local ok, r = try(function() return o:alive() end) return ok and r == true end

-- L.players([include_dead]) -> { {id=, obj=, name=}, ... } sorted by id  (db.mp_actors: every player the server/host knows)
function L.players(include_dead)
	local r = {}
	if type(db.mp_actors) == "table" then
		for id, o in pairs(db.mp_actors) do
			if o ~= nil and (include_dead or obj_alive(o)) then
				local _, nm = try(function() return o:name() end)
				r[#r + 1] = { id = id, obj = o, name = nm }
			end
		end
	end
	table.sort(r, function(a, b) return a.id < b.id end)
	return r
end

function L.local_player()
	if _G.qa and qa.local_object then return qa.local_object() end
	local ok, id = try(LocalActor)
	if ok and id and id ~= 0 then local ok2, o = try(level.object_by_id, id) if ok2 then return o end end
	return nil
end

-- L.player(spec) -> game_object, id.   spec: nil (local player on a client, first player on the server), number id,
-- string (player name, case-insensitive: "qaa"), a game_object, or {obj=..}.
function L.player(spec)
	if spec == nil then
		local lo = (not L.is_dedicated()) and L.local_player() or nil
		if lo ~= nil then
			local ok, id = try(function() return lo:id() end)
			-- prefer the server-side object of the same player if known
			if ok and type(db.mp_actors) == "table" and db.mp_actors[id] ~= nil and L.on_server() then return db.mp_actors[id], id end
			if ok then return lo, id end
		end
		local p = L.players()[1]
		if p then return p.obj, p.id end
		return nil, nil
	end
	if type(spec) == "number" then
		if type(db.mp_actors) == "table" and db.mp_actors[spec] ~= nil then return db.mp_actors[spec], spec end
		local ok, o = try(level.object_by_id, spec)
		if ok and o ~= nil then return o, spec end
		return nil, nil
	end
	if type(spec) == "string" then
		local want = string.lower(spec)
		for _, p in ipairs(L.players(true)) do
			if p.name and string.lower(tostring(p.name)) == want then return p.obj, p.id end
		end
		return nil, nil
	end
	if type(spec) == "table" and spec.obj ~= nil then return spec.obj, spec.id end
	local ok, id = try(function() return spec:id() end)
	if ok then return spec, id end
	return nil, nil
end

-- position of anything: vector, {x,y,z}, game_object, server object, object id
function L.pos(spec)
	if spec == nil then return nil end
	if type(spec) == "number" then
		local ok, se = try(function() return alife():object(spec) end)
		if ok and se ~= nil then return se.position end
		local ok2, o = try(level.object_by_id, spec)
		if ok2 and o ~= nil then return o:position() end
		return nil
	end
	local okx, x = try(function() return spec.x end)
	if okx and type(x) == "number" then return spec end
	if type(spec) == "table" and spec[1] ~= nil then return L.vec(spec[1], spec[2], spec[3]) end
	local ok, p = try(function() return spec:position() end)
	if ok and p ~= nil then return p end
	local ok2, p2 = try(function() return spec.position end)
	if ok2 and p2 ~= nil then return p2 end
	return nil
end

-- ---------------------------------------------------------------------------------------------------- health (relative setter!)
-- L.set_health(obj, value) -> health after.  obj.health = x adds x, so this adds (value - current).
-- The engine applies the change on the next frame: the value returned here is still the old one; read obj.health a second later.
function L.set_health(obj, value)
	local cur = obj.health
	obj.health = value - cur
	return obj.health
end

function L.heal(obj) return L.set_health(obj, 1) end

-- L.god(true|false): from now on every tick tops every alive player up to full health (the defaults of the probes: a stray
-- bandit must not end a test).  Server role / listen host only.
local god_on = false
function L.god(on) god_on = on ~= false ev("god " .. tostring(god_on)) end
qa.hooks.qa_lib_god = function(t, lo)
	if not god_on or not L.on_server() then return end
	for _, p in ipairs(L.players()) do
		local ok, h = try(function() return p.obj.health end)
		if ok and h < 0.98 then pcall(L.set_health, p.obj, 1) end
	end
end

-- ---------------------------------------------------------------------------------------------------- info portions and story flags
-- Story flags are the mod's SHARED state (synced to every client, saved): L.flag_*.
-- Info portions are the engine's per-player state (actor:give_info_portion): L.info_*.  Names of both are plain strings.
function L.flag_give(name) story_flags.give_flag(name) return story_flags.has_flag(string.upper(name)) end
function L.flag_clear(name) story_flags.disable_flag(name) return not story_flags.has_flag(string.upper(name)) end
function L.flag_has(name) return story_flags.has_flag(string.upper(name)) == true end

-- target: nil = every alive player, else a player spec
local function targets(spec)
	if spec == nil then
		local r = {}
		for _, p in ipairs(L.players()) do r[#r + 1] = p.obj end
		return r
	end
	local o = L.player(spec)
	return { o }
end

function L.info_give(name, player)
	local n = 0
	for _, o in ipairs(targets(player)) do if try(function() o:give_info_portion(name) end) then n = n + 1 end end
	ev("info_give " .. name .. " to " .. n .. " player(s)")
	return n
end

function L.info_clear(name, player)
	local n = 0
	for _, o in ipairs(targets(player)) do if try(function() o:disable_info_portion(name) end) then n = n + 1 end end
	ev("info_clear " .. name .. " from " .. n .. " player(s)")
	return n
end

function L.info_has(name, player)
	local o = L.player(player)
	if o == nil then return false end
	local ok, r = try(function() return o:has_info(name) end)
	return ok and r == true
end

-- ---------------------------------------------------------------------------------------------------- money and items
function L.money(player)
	local o = L.player(player)
	if o == nil then return nil end
	local ok, m = try(function() return o:money() end)
	if ok then return m end
	return nil
end

-- give_money is a delta in the engine; L.give_money adds n (negative takes), L.set_money sets the balance.
function L.give_money(player, n)
	local o = L.player(player)
	if o == nil then return nil, "no player" end
	local ok, err = try(function() o:give_money(n) end)
	if not ok then return nil, err end
	return L.money(player)
end

function L.set_money(player, n)
	local cur = L.money(player)
	if cur == nil then return nil, "no money" end
	return L.give_money(player, n - cur)
end

local function place_near(player_spec, offset)
	local _, pid = L.player(player_spec)
	if pid == nil then return nil, "no player" end
	local ok, se = try(function() return alife():object(pid) end)
	if not ok or se == nil then return nil, "player has no server object" end
	offset = offset or { 3, 0, 0 }
	local pos = vector():set(se.position.x + offset[1], se.position.y + offset[2], se.position.z + offset[3])
	local lv, gv = se.m_level_vertex_id, se.m_game_vertex_id
	if math.abs(offset[1]) + math.abs(offset[3]) > 6 then
		local ok2, v = try(level.vertex_id, pos)
		if ok2 and v ~= nil and v ~= 4294967295 then lv = v end
	end
	return pos, lv, gv, pid
end

-- L.spawn(section, where [, opts]) -> server object, id     (server side)
--   where : position spec (vector / {x,y,z} / object), or nil together with opts.near
--   opts.near   player spec: spawn beside that player (opts.offset = {dx,dy,dz}, default {3,0,0})
--   opts.parent object id to put the item into (inventory)
function L.spawn(section, where, opts)
	opts = opts or {}
	local pos, lv, gv
	if opts.near ~= nil or where == nil then
		pos, lv, gv = place_near(opts.near, opts.offset)
		if pos == nil then return nil, lv end
	else
		pos = L.pos(where)
		if pos == nil then return nil, "bad position" end
		local ok, v = try(level.vertex_id, pos)
		lv = (ok and v ~= nil and v ~= 4294967295) and v or opts.lv
		local _, _, pgv = place_near(nil, { 0, 0, 0 })
		gv = opts.gv or pgv
		if lv == nil then local _, plv = place_near(nil, { 0, 0, 0 }) lv = plv end
	end
	local ok, se
	if opts.parent then
		ok, se = try(function() return alife():create(section, pos, lv, gv, opts.parent) end)
	else
		ok, se = try(function() return alife():create(section, pos, lv, gv) end)
	end
	if not ok or se == nil then ev("spawn " .. section .. " FAILED " .. tostring(se)) return nil, tostring(se) end
	ev(string.format("spawn %s id=%s at %s", section, tostring(se.id), fmt_pos(pos)))
	return se, se.id
end

local function is_ammo(section) return string.find(section, "^ammo_") ~= nil end

-- L.give_item(player, section [, n]) -> list of created server object ids   (items go into the player's inventory)
-- Ammo sections are created as one stack of n rounds.
function L.give_item(player, section, n)
	n = n or 1
	local o, pid = L.player(player)
	if pid == nil then return nil, "no player" end
	local ok, se = try(function() return alife():object(pid) end)
	if not ok or se == nil then return nil, "player has no server object" end
	local ids = {}
	if is_ammo(section) then
		local mk = _G.create_ammo
		local okc, a = false, nil
		if type(mk) == "function" then
			okc, a = try(mk, section, se.position, se.m_level_vertex_id, se.m_game_vertex_id, pid, n)
		end
		if not okc then okc, a = try(function() return alife():create_ammo(section, se.position, se.m_level_vertex_id, se.m_game_vertex_id, pid, n) end) end
		if not okc then return nil, tostring(a) end
		ids[1] = (type(a) == "table" or type(a) == "userdata") and a.id or a
	else
		for i = 1, n do
			local okc, c = try(function() return alife():create(section, se.position, se.m_level_vertex_id, se.m_game_vertex_id, pid) end)
			if not okc or c == nil then return ids, tostring(c) end
			ids[#ids + 1] = c.id
		end
	end
	ev("give_item " .. section .. " x" .. n .. " to player " .. tostring(pid))
	return ids
end

-- ---------------------------------------------------------------------------------------------------- inventory
-- L.inventory(player [, source]) -> list { {id=, section=, slot=} ... }, source_used
--   source "online": walk the online game object (iterate_inventory) and find the equipped slot with item_in_slot (client / listen host);
--   source "server": every server object whose parent is the player (works on the dedicated server; slot is -1, it is client state).
--   Default: online, falling back to server when online gave nothing.   slot 0 = carried (backpack / belt), 1.. = equipped slot
local function inv_online(o)
	local list, slotof = {}, {}
	for s = 1, 12 do
		local ok, it = try(function() return o:item_in_slot(s) end)
		if ok and it ~= nil then
			local okid, iid = try(function() return it:id() end)
			if okid then slotof[iid] = s end
		end
	end
	local ok = try(function()
		o:iterate_inventory(function(owner, it)
			local iid = it:id()
			list[#list + 1] = { id = iid, section = it:section(), slot = slotof[iid] or 0 }
		end, o)
	end)
	if not ok then return nil end
	return list
end

local function inv_server(pid)
	local list = {}
	local sim = alife()
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil and se.parent_id == pid then list[#list + 1] = { id = id, section = se:section_name(), slot = -1 } end
	end
	return list
end

function L.inventory(player, source)
	local o, pid = L.player(player)
	if o == nil then return nil, "no player" end
	local list
	if source ~= "server" then list = inv_online(o) end
	if source == "online" then return list or {}, "online" end
	if list ~= nil and #list > 0 then table.sort(list, function(a, b) return a.id < b.id end) return list, "online" end
	local ok, l2 = try(inv_server, pid)
	if not ok then return list or {}, "online" end
	table.sort(l2, function(a, b) return a.id < b.id end)
	return l2, "server"
end

function L.count_item(player, section, source)
	local list = L.inventory(player, source)
	local n = 0
	for _, it in ipairs(list or {}) do if it.section == section then n = n + 1 end end
	return n
end

-- L.dump_inventory(player, tag [, source]) -> list, source.  One qa_events.log line per item:  LIB INV tag side=server|client source=.. id= section= slot=
function L.dump_inventory(player, tag, source)
	local list, src = L.inventory(player, source)
	if list == nil then ev("INV " .. tostring(tag) .. " no inventory: " .. tostring(src)) return nil, src end
	local side = L.on_server() and (L.is_dedicated() and "dedicated" or "host") or "client"
	local _, pid = L.player(player)
	ev(string.format("INV %s side=%s source=%s player=%s items=%d", tostring(tag), side, src, tostring(pid), #list))
	for _, it in ipairs(list) do ev(string.format("INV %s id=%d section=%s slot=%d", tostring(tag), it.id, it.section, it.slot)) end
	return list, src
end

-- ---------------------------------------------------------------------------------------------------- online objects
function L.online(id) local ok, o = try(level.object_by_id, id) if ok then return o end return nil end

-- L.find_online(name_substring) -> game_object (first match by object name), scans the level
function L.find_online(sub)
	for id = 1, 65534 do
		local o = L.online(id)
		if o ~= nil then
			local ok, nm = try(function() return o:name() end)
			if ok and nm and string.find(nm, sub, 1, true) then return o end
		end
	end
	return nil
end

-- ---------------------------------------------------------------------------------------------------- NPCs: spawn and relation
local REL = { friend = 0, neutral = 1, enemy = 2 }
local REL_NAME = { [0] = "friend", [1] = "neutral", [2] = "enemy" }
L.REL = REL

-- npc argument of set_relation / get_relation: a game_object or an object id (it is looked up among the online objects)
local function as_npc(n)
	if type(n) == "number" then return L.online(n) end
	return n
end

-- L.set_relation(npc_obj_or_id, "friend"|"neutral"|"enemy", player) -> true | false, err ;  npc must be ONLINE
function L.set_relation(npc, rel, player)
	npc = as_npc(npc)
	local o = L.player(player)
	if npc == nil or o == nil then return false, "npc or player missing" end
	local v = REL[rel]
	if v == nil then return false, "relation must be friend|neutral|enemy" end
	local ok, err = try(function() npc:set_relation(v, o) end)
	if not ok then return false, tostring(err) end
	-- set_relation only changes the PERSONAL goodwill; relation() also adds the community relation (bandit vs stalker = enemy), so it still read
	-- "enemy" after set_relation(friend) (smoke run 2026-10-21).  force_set_goodwill moves the combined value: friend 1000, neutral 0, enemy -1000.
	pcall(function() npc:force_set_goodwill(({ friend = 1000, neutral = 0, enemy = -1000 })[rel], o) end)
	return true
end

-- L.get_relation(npc_obj, player) -> "friend"|"neutral"|"enemy"|number
function L.get_relation(npc, player)
	npc = as_npc(npc)
	if npc == nil then return nil, "npc not online" end
	local o = L.player(player)
	local ok, r = try(function() return npc:relation(o) end)
	if not ok then return nil, tostring(r) end
	return REL_NAME[r] or r
end

-- L.spawn_npc(section, opts) -> server object, id ;  opts.near = player spec (default: first player), opts.offset = {dx,dy,dz},
-- opts.relation = "friend"|"neutral"|"enemy" (applied as soon as the NPC is online, inside a background job)
-- opts.god = true switches L.god(true) on first.  A hostile NPC spawned 4-6 m from a player can kill him within seconds (the Lua VM restarts
-- and the test starts over): call L.god(true) BEFORE spawning an enemy, or pass god=true.  A warning line is logged when you did not.
function L.spawn_npc(section, opts)
	opts = opts or {}
	if opts.god then L.god(true) end
	if opts.relation == "enemy" and not god_on then
		ev("WARN spawn_npc " .. tostring(section) .. " as enemy while god mode is off: it can kill the player (call L.god(true) first)")
	end
	local se, id = L.spawn(section, nil, { near = opts.near, offset = opts.offset or { 4, 0, 0 } })
	if se == nil then return nil, id end
	if opts.relation then
		local rel, pl = opts.relation, opts.near
		L.task("relation_" .. tostring(id), {
			function() return L.wait_for(function() return L.online(id) ~= nil end, 40) end,
			function(c, up)
				if up then
					local ok, err = L.set_relation(L.online(id), rel, pl)
					ev("relation of " .. tostring(id) .. " -> " .. rel .. " " .. tostring(ok) .. " " .. tostring(err))
				else
					ev("relation of " .. tostring(id) .. " not applied: never came online")
				end
			end,
		})
	end
	return se, id
end

-- L.remove(id_or_se): release a server object (call it a few seconds after creating it: releasing in the creation frame crashes)
function L.remove(spec)
	local id = spec
	if type(spec) ~= "number" then id = spec.id end
	local ok, se = try(function() return alife():object(id) end)
	if ok and se ~= nil then
		local ok2, err = try(function() alife():release(se, true) end)
		ev("remove " .. tostring(id) .. " " .. tostring(ok2) .. " " .. (ok2 and "" or tostring(err)))
		return ok2
	end
	return false
end

-- ---------------------------------------------------------------------------------------------------- hits and kills
-- L.hit(target_obj, opts) -> hp_before, hp_after (read in the same frame; effects can land a frame later)
--   opts.who    attacker: game_object | id | player spec (default: first player).  nil/false = the target itself
--   opts.bone   "bip01_spine1" (default) | "bip01_head" | "bip01_l_hand" ...      opts.power 0.5518 (about one PM bullet)
--   opts.type   hit.fire_wound (default)      opts.impulse 75
function L.hit(target, opts)
	opts = opts or {}
	local who = opts.who
	if who == nil then who = L.player(nil) elseif type(who) == "number" or type(who) == "string" then who = L.player(who) or L.online(who) end
	if who == false then who = nil end
	local h = hit()
	h.draftsman = who or target
	h.type = opts.type or hit.fire_wound
	local tp, wp = L.pos(target), L.pos(who or target)
	local d = vector():set(0, 0, 1)
	if tp and wp and (tp.x ~= wp.x or tp.z ~= wp.z) then d = vector():set(tp.x - wp.x, tp.y - wp.y, tp.z - wp.z) end
	h.direction = d
	h.power = opts.power or 0.5518
	h.impulse = opts.impulse or 75
	h:bone(opts.bone or "bip01_spine1")
	local before = target.health
	target:hit(h)
	return before, target.health
end

-- L.hits_to_kill(opts) -> ACTION, result { hits=n, dead=bool, killed=bool, id=, section=, hp0=, hp={after each hit}, power=, bone= } | nil, err
--   opts.section  NPC/monster section that hits_to_kill SPAWNS ITSELF beside the player (default sim_default_bandit_0).  It does NOT hit an
--                 NPC you spawned earlier: pass that one with opts.id.
--   opts.id       hit this ONLINE NPC (server object id) instead of spawning one.  It is never respawned: when it is already dead
--                 before the first hit the action ends with  nil, "target was already dead ..."  and counts no hit.
--   opts.near / opts.offset  player spec and {dx,dy,dz} (default first player, {4,0,0}) for the spawned target
--   opts.power (0.5518 = about one PM bullet) / opts.bone / opts.who / opts.impulse as in L.hit      opts.max 30 hits      opts.interval 1.2 s
--   opts.keep=true leaves the NPC alive/standing afterwards (default: released)
-- Result flags: res.killed = at least one counted hit AND the target is dead afterwards (assert THIS, not res.dead: dead alone is also true
--   when somebody else killed the target).  res.hurt_at_start = the target was already wounded before the first hit (hp0 < 0.99).
-- A target that is dead or wounded before the first hit is respawned up to 3 times (spawned targets only); if it is still dead after that the
-- action fails.  It sets god mode for the players for the duration, so the target's friends cannot end the test.
function L.hits_to_kill(opts)
	opts = opts or {}
	local res = { hits = 0, dead = false, killed = false, hp = {}, power = opts.power or 0.5518, bone = opts.bone or "bip01_spine1", section = opts.section or "sim_default_bandit_0" }
	local was_god = god_on
	local id = opts.id
	local interval = opts.interval or 1.2
	local max = opts.max or 30
	local tries = 0
	local function fail(why)
		L.god(was_god)
		ev("hits_to_kill " .. res.section .. " FAILED " .. why)
		if res.spawned and id ~= nil and not opts.keep then L.remove(id) end
		return L.done(nil, why)
	end
	return L.seq({
		"spawn",
		function()
			L.god(true)
			if id == nil then
				local se, sid = L.spawn_npc(res.section, { near = opts.near, offset = opts.offset or { 4, 0, 0 } })
				if se == nil then return fail("spawn failed: " .. tostring(sid)) end
				id = sid
				res.spawned = true
			end
			res.id = id
			return L.wait_for(function() return L.online(id) ~= nil end, 40)
		end,
		function(c, up)
			if not up then return fail("NPC never came online") end
			return L.wait(3)  -- let it settle (and let other NPCs finish hurting it, we want a clean start)
		end,
		function()
			local n = L.online(id)
			if n == nil then return fail("NPC went offline") end
			res.hp0 = n.health
			local bad = res.hp0 < 0.99 or not n:alive()
			-- a hostile NPC beside a village is often killed by the villagers before the first hit (hp0 -1 seen in the smoke run): respawn it
			if bad and res.spawned and opts.id == nil and tries < 3 then
				tries = tries + 1
				ev(string.format("hits_to_kill: target already hurt (hp %.2f), respawning (%d/3)", res.hp0, tries))
				L.remove(id)
				id = nil
				res.spawned = false
				return L.jump("spawn")
			end
			if not n:alive() then
				-- nothing of ours killed it: a result of hits=0, dead=true must never look like a successful kill
				res.already_dead = true
				return fail(string.format("target was already dead before the first hit (hp0 %.2f, %d respawn(s)); killed by someone else, no hit counted", res.hp0, tries))
			end
			if bad then res.hurt_at_start = true ev(string.format("hits_to_kill: target starts wounded (hp %.2f)", res.hp0)) end
		end,
		function()  -- one hit per pass, repeated every interval
			if res.hits >= max then return end
			local n = L.online(id)
			if n == nil or not n:alive() then return end
			local before, after = L.hit(n, { who = opts.who, bone = res.bone, power = res.power, impulse = opts.impulse })
			res.hits = res.hits + 1
			res.hp[#res.hp + 1] = after
			return L.again(interval)
		end,
		function()
			local n = L.online(id)
			res.dead = (n == nil) or (not n:alive())
			res.killed = res.dead and res.hits > 0
			res.hp_end = n and n.health or nil
			ev(string.format("hits_to_kill %s bone=%s power=%.4f -> %d hits, dead=%s, killed=%s, hp0=%.3f", res.section, res.bone, res.power, res.hits, tostring(res.dead), tostring(res.killed), res.hp0 or -1))
			if res.spawned and not opts.keep then return L.wait(2) end
		end,
		function()
			if res.spawned and not opts.keep then L.remove(id) end
			L.god(was_god)
			return L.done(res)
		end,
	}, "hits_to_kill")
end

-- L.kill(target [, killer]) -> method | nil, err.   target: game_object | id | player spec.  killer: game_object | id | player spec | nil.
-- Applies a lethal fire-wound hit with the killer as the attacker (so kill credit, relation and loot logic see him); if the
-- target is still alive one tick later the relative health setter is used as a fallback.  Returns "hit" or "health".
function L.kill(target, killer)
	local t = target
	if type(target) == "number" then t = L.online(target) or L.player(target) elseif type(target) == "string" then t = L.player(target) end
	if t == nil then return nil, "target not found" end
	local k = killer
	if type(killer) == "number" then k = L.online(killer) or L.player(killer) elseif type(killer) == "string" then k = L.player(killer) end
	local ok, err = try(L.hit, t, { who = k or false, power = 100000, impulse = 10, bone = "bip01_spine" })
	if not ok then ev("kill hit failed " .. tostring(err)) end
	ev("kill requested on " .. tostring(try(function() return t:name() end) and t:name()) .. " by " .. tostring(k and try(function() return k:name() end) and k:name() or "self"))
	return "hit"
end

-- L.kill_player(player [, killer]) -> ACTION: kills the player, waits for the death.  Result: true, "hit"|"health" | false, why
function L.kill_player(player, killer)
	local o, pid = L.player(player)
	if o == nil then return L.now(false, "no player") end
	return L.seq({
		function()
			L.kill(o, killer)
			return L.wait_for(function() return not obj_alive(o) end, 8)
		end,
		function(c, dead)
			if dead then return L.done(true, "hit") end
			pcall(function() o.health = -2 end)  -- fallback: the relative setter (-2 takes everything)
			return L.wait_for(function() return not obj_alive(o) end, 6)
		end,
		function(c, dead)
			if dead then return L.done(true, "health") end
			return L.done(false, "player still alive")
		end,
	}, "kill_player")
end

-- ---------------------------------------------------------------------------------------------------- teleport
-- L.teleport(player, pos [, dir]) -> ACTION.  Moves the player and waits until it is within 3 m.  Result: true, method | false, why
-- Uses teleport_actor_sv on the server (what the mod's own xrmpe_teleport_actors does) and set_actor_position on the object as fallback.
function L.teleport(player, pos, dirv)
	local o, pid = L.player(player)
	if o == nil then return L.now(false, "no player") end
	local p = L.pos(pos)
	if p == nil then return L.now(false, "bad position") end
	local dir = dirv or vector():set(0, 0, 1)
	local method = "set_actor_position"
	local function near()
		local cp = L.pos(pid) or L.pos(o)
		return cp ~= nil and L.dist3(cp, p) < 3
	end
	return L.seq({
		function()
			if L.on_server() and type(_G.teleport_actor_sv) == "function" then
				method = "teleport_actor_sv"
				pcall(_G.teleport_actor_sv, pid, p, dir)
			else
				pcall(function() o:set_actor_position(p) end)
			end
			return L.wait_for(near, 8)
		end,
		function(c, ok)
			if ok then ev(string.format("teleport player %s -> %s via %s ok", tostring(pid), fmt_pos(p), method)) return L.done(true, method) end
			-- other method
			if method == "teleport_actor_sv" then pcall(function() o:set_actor_position(p) end) method = "set_actor_position" else
				if type(_G.teleport_actor_sv) == "function" then pcall(_G.teleport_actor_sv, pid, p, dir) method = "teleport_actor_sv" end
			end
			return L.wait_for(near, 8)
		end,
		function(c, ok)
			if ok then ev(string.format("teleport player %s -> %s via fallback %s ok", tostring(pid), fmt_pos(p), method)) return L.done(true, method) end
			ev(string.format("teleport player %s -> %s FAILED", tostring(pid), fmt_pos(p)))
			return L.done(false, "player did not reach the target")
		end,
	}, "teleport")
end

-- ---------------------------------------------------------------------------------------------------- NPC listing
-- L.npcs_near(where, radius [, opts]) -> list sorted by distance { {id=, name=, section=, alive=, online=, dist=, pos=, job=, smart=, scheme=, kind="stalker"|"monster"} }
--   where: position spec / player / object.  opts.flat=true measures in x/z only.  opts.stalkers_only / opts.monsters_only.
--   job and smart come from the smart terrains' npc_info (server); scheme is the logic section of an online NPC.
function L.npcs_near(where, radius, opts)
	opts = opts or {}
	local c = L.pos(where)
	if c == nil then local o = L.player(where) if o then c = o:position() end end
	if c == nil then return nil, "bad centre" end
	local sim = alife()
	local jobs, found = {}, {}
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil then
			if se.npc_info ~= nil and se.job_data ~= nil then
				for nid, info in pairs(se.npc_info) do
					local sec = "?"
					pcall(function() if info.job_id ~= nil and info.job_id >= 0 and se.job_data[info.job_id] ~= nil then sec = se.job_data[info.job_id].section end end)
					jobs[nid] = { job = sec, smart = se:name() }
				end
			end
			local okc, cl = pcall(function() return se:clsid() end)
			if okc and cl then
				local kind
				local oks, isst = pcall(IsStalker, nil, cl)
				local okm, ismo = pcall(IsMonster, nil, cl)
				if (oks and isst) or cl == clsid.script_trader or cl == clsid.trader then kind = "stalker" elseif okm and ismo then kind = "monster" end
				if kind and not (opts.stalkers_only and kind ~= "stalker") and not (opts.monsters_only and kind ~= "monster") then
					local p = se.position
					local d = opts.flat and L.dist2(p, c) or L.dist3(p, c)
					if d <= radius then found[#found + 1] = { id = id, se = se, kind = kind, dist = d, pos = p } end
				end
			end
		end
	end
	local out = {}
	for _, f in ipairs(found) do
		local se = f.se
		local alive = true
		pcall(function() alive = se:alive() end)
		local on = L.online(f.id)
		local scheme = "-"
		if on ~= nil then pcall(function() local st = db.storage[f.id]; if st ~= nil then scheme = tostring(st.active_section) end end) end
		local jb = jobs[f.id] or {}
		out[#out + 1] = { id = f.id, name = se:name(), section = se:section_name(), alive = alive, online = on ~= nil, dist = f.dist, pos = f.pos,
		                  job = jb.job or "-", smart = jb.smart or "-", scheme = scheme, kind = f.kind }
	end
	table.sort(out, function(a, b) return a.dist < b.dist end)
	return out
end

-- L.dump_npcs(where, radius, tag [, opts]) -> list.  Logs  LIB NPC tag name= section= job= scheme= ...
function L.dump_npcs(where, radius, tag, opts)
	local list, err = L.npcs_near(where, radius, opts)
	if list == nil then ev("NPC " .. tostring(tag) .. " failed " .. tostring(err)) return nil, err end
	ev(string.format("NPC %s count=%d radius=%.0f", tostring(tag), #list, radius))
	for _, n in ipairs(list) do
		ev(string.format("NPC %s %-34s %-26s %s %s d=%.1f job=%s scheme=%s smart=%s pos=%s", tostring(tag), n.name, n.section, n.alive and "alive" or "DEAD",
			n.online and "online" or "offline", n.dist, n.job, n.scheme, n.smart, fmt_pos(n.pos)))
	end
	return list
end

-- ---------------------------------------------------------------------------------------------------- party-vote travel
-- guide codes of the ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_<CODE>_INFO flags -> level
L.GUIDE = {
	AES_1 = "coop_l11_stancia_1", AES_2 = "coop_l11_stancia_2", AGRU = "coop_l03_agroprom_underground", AGR = "coop_l03_agroprom",
	BAR = "coop_l05_bar", CON = "coop_l11_control_monolith", GAR = "coop_l02_garbage", MIL = "coop_l07_military", PRI = "coop_l10_pripyat",
	RAD = "coop_l09_radar", ROS = "coop_l06_rostok", SAR = "coop_l11_sarcofag", VAL = "coop_l04_darkvalley", X10 = "coop_l09_x10",
	X16 = "coop_l08_x16", X18 = "coop_l04_x18", YAN = "coop_l08_yantar",
}
L.ALL_LEVELS = { "coop_l01_escape", "coop_l02_garbage", "coop_l03_agroprom", "coop_l03_agroprom_underground", "coop_l04_darkvalley", "coop_l04_x18",
	"coop_l05_bar", "coop_l06_rostok", "coop_l07_military", "coop_l08_yantar", "coop_l08_x16", "coop_l09_radar", "coop_l09_x10", "coop_l10_pripyat",
	"coop_l11_stancia_1", "coop_l11_stancia_2", "coop_l11_control_monolith", "coop_l11_sarcofag" }
-- The guide restrictor (esc_smart_terrain_1_stalker_guide_space_restrictor.ltx) reacts to a passed vote with on_game_timer = 20 and then
-- xrmpe_teleport_actors(esc_smart_terrain_1_guide_temp_<N>_walk : ..._look): N is fixed per destination.  The game clock runs slowly on a
-- server, so L.travel speeds it up (opts.time_factor, default 300) and, with opts.fallback, does that teleport itself after 40 s.
local GUIDE_TEMP = { GAR = 1, AGR = 2, AGRU = 3, VAL = 4, X18 = 5, BAR = 6, ROS = 7, YAN = 8, X16 = 9, MIL = 10, RAD = 11, X10 = 12, PRI = 13,
                     AES_1 = 14, SAR = 15, CON = 16, AES_2 = 17 }
local FALLBACK_POINTS = {}
for code, n in pairs(GUIDE_TEMP) do
	FALLBACK_POINTS[code] = { "esc_smart_terrain_1_guide_temp_" .. n .. "_walk", "esc_smart_terrain_1_guide_temp_" .. n .. "_look" }
end

-- L.guide_code("bar" | "BAR" | "coop_l05_bar" | "l05_bar") -> "BAR", level name
function L.guide_code(dest)
	local d = string.upper(tostring(dest))
	if L.GUIDE[d] then return d, L.GUIDE[d] end
	local low = string.lower(tostring(dest))
	for code, lvl in pairs(L.GUIDE) do
		if lvl == low or lvl == "coop_" .. low or string.find(lvl, low, 1, true) and #low > 4 then return code, lvl end
	end
	return nil
end

-- L.travel(dest [, opts]) -> ACTION (server / listen host, starting on Cordon).  Gives the guide flag, then calls
-- coop_map_vote.on_yes for every alive player every 8 s (what the Yes buttons do).  A successful level change restarts the Lua VM,
-- so success is seen by L.travel_arrived() in the NEXT VM; the action only finishes on failure:  false, why  (or true when already there).
--   opts.timeout 150 s    opts.fallback=true teleports the party to the guide spot after 40 s    opts.start=true also calls coop_map_vote.start
function L.travel(dest, opts)
	opts = opts or {}
	local code, lvl = L.guide_code(dest)
	if code == nil then return L.now(false, "unknown destination " .. tostring(dest)) end
	if L.level_name() == lvl then return L.now(true, "already on " .. lvl) end
	if L.level_name() ~= "coop_l01_escape" then return L.now(false, "the guide vote starts on Cordon (now " .. tostring(L.level_name()) .. ")") end
	local timeout = opts.timeout or 150
	local t0, fb = nil, false
	return L.seq({
		function()
			L.state_set("travel_dest", lvl)
			L.state_set("travel_t0", os.time())
			story_flags.give_flag("ESC_SMART_TERRAIN_1_STALKER_GUIDE_TO_" .. code .. "_INFO")
			ev("travel to " .. lvl .. ": guide flag given")
			if opts.time_factor ~= false then pcall(level.set_time_factor, opts.time_factor or 300) end
			if opts.start then pcall(function() coop_map_vote.start(string.lower(code)) end) end
			return L.wait(3)
		end,
		function()  -- every 8 s: Yes for every alive player (what the vote buttons do)
			t0 = t0 or os.time()
			if os.time() - t0 >= timeout then return end
			local n = 0
			for _, pl in ipairs(L.players()) do
				if pcall(coop_map_vote.on_yes, pl.id) then n = n + 1 end
			end
			ev("travel vote yes sent for " .. n .. " player(s) after " .. (os.time() - t0) .. " s")
			if opts.fallback and not fb and os.time() - t0 > 40 and FALLBACK_POINTS[code] then
				fb = true
				pcall(function() xr_effects.xrmpe_teleport_actors(nil, nil, FALLBACK_POINTS[code]) end)
				ev("travel fallback teleport to the guide spot")
			end
			return L.again(8)
		end,
		function()
			L.state_set("travel_dest", nil)
			return L.done(false, "no level change after " .. timeout .. " s")
		end,
	}, "travel")
end

-- L.travel_arrived() -> true, level, seconds  when a travel started by L.travel finished (call it in the first hook of the new VM), else false
function L.travel_arrived()
	local st = L.state()
	local d = st.travel_dest
	if d and d == L.level_name() then
		local secs = os.time() - (tonumber(st.travel_t0) or os.time())
		L.state_set("travel_dest", nil)
		L.state_set("travel_t0", nil)
		ev("travel arrived on " .. d .. " after " .. secs .. " s")
		return true, d, secs
	end
	return false
end

-- ---------------------------------------------------------------------------------------------------- save and load
-- Saves are written by the server console command "save quicksave - N" (game_sv.saveGame, N rotates 1..5); load_last_save loads the newest.
-- L.saves() -> list { {name=, modif=} } newest first
function L.saves()
	local out = {}
	local ok = pcall(function()
		local flist = getFS():file_list_open_ex("$game_saves$", bit_or(FS.FS_ListFiles, FS.FS_RootOnly), "*.scop")
		flist:Sort(FS.FS_sort_by_modif_down)
		for i = 0, flist:Size() - 1 do
			local f = flist:GetAt(i)
			out[#out + 1] = { name = f:NameFull(), modif = f:ModifDigitOnly() }
		end
	end)
	if not ok or #out == 0 then
		-- some builds list one extension per call
		pcall(function()
			local flist = getFS():file_list_open_ex("$game_saves$", bit_or(FS.FS_ListFiles, FS.FS_RootOnly), "*")
			flist:Sort(FS.FS_sort_by_modif_down)
			for i = 0, flist:Size() - 1 do
				local f = flist:GetAt(i)
				out[#out + 1] = { name = f:NameFull(), modif = f:ModifDigitOnly() }
			end
		end)
	end
	return out
end

local function save_key(list) local r = {} for _, s in ipairs(list) do r[#r + 1] = s.name .. "@" .. tostring(s.modif) end return table.concat(r, "|") end

-- L.save() -> ACTION: saves the way the server does (game_sv.saveGame) and waits for a new / changed save file.  Result: name | nil, err
function L.save()
	local before
	return L.seq({
		function()
			before = save_key(L.saves())
			local ok, err
			if L.on_server() and _G.game_sv and type(game_sv.saveGame) == "function" then
				ok, err = pcall(game_sv.saveGame, 0)
			else
				ok, err = pcall(function() game_cl.executeFunctionOnServer("saveGame") end)
			end
			if not ok then ev("save call failed " .. tostring(err)) return L.done(nil, tostring(err)) end
			return L.wait_for(function() return save_key(L.saves()) ~= before end, 25)
		end,
		function(c, changed)
			if not changed then
				ev("save: no new file in $game_saves$ after 25 s")
				return L.done(nil, "no save file appeared")
			end
			local newest = L.saves()[1]
			ev("save done: " .. tostring(newest and newest.name))
			return L.done(newest and newest.name)
		end,
	}, "save")
end

-- L.load_last() -> console load_last_save through game_sv.loadLastSave (server).  The level reloads, the Lua VM restarts: continue in the next VM.
function L.load_last()
	local ok, err
	if L.on_server() and _G.game_sv and type(game_sv.loadLastSave) == "function" then
		ok, err = pcall(game_sv.loadLastSave, 0)
	else
		ok, err = pcall(function() game_cl.executeFunctionOnServer("loadLastSave") end)
	end
	ev("load_last " .. tostring(ok) .. " " .. tostring(err))
	return ok, err
end

-- ---------------------------------------------------------------------------------------------------- talk window (client)
-- L.open_talk(npc_spec [, opts]) -> ACTION (client / listen host).  npc_spec: game_object | name substring | story id.
-- Moves the local player 1.5 m in front of the NPC, runs run_talk_dialog, checks is_talking.  Result: true | false, why [, screenshot].
--   opts.shot = tag takes an engine screenshot while the window is open.      Close it with L.close_talk().
function L.open_talk(npc_spec, opts)
	opts = opts or {}
	local lo = L.local_player()
	if lo == nil then return L.now(false, "no local player (client side function)") end
	local npc = npc_spec
	if type(npc_spec) == "string" then
		npc = L.find_online(npc_spec)
		if npc == nil then
			local ok, sid = try(get_story_object_id, npc_spec)
			if ok and sid then npc = L.online(sid) end
		end
	end
	if npc == nil then return L.now(false, "NPC not online (go near it first): " .. tostring(npc_spec)) end
	local talking, okt
	return L.seq({
		function()
			local np = npc:position()
			local dirv = npc:direction()
			local target = vector():set(np.x + dirv.x * 1.5, np.y + 0.3, np.z + dirv.z * 1.5)
			pcall(function() lo:set_actor_position(target) end)
			return L.wait(5)
		end,
		function()
			local ok, err = pcall(function() lo:run_talk_dialog(npc, false) end)
			if not ok then return L.done(false, "run_talk_dialog failed: " .. tostring(err)) end
			return L.wait(4)
		end,
		function()
			okt, talking = try(function() return lo:is_talking() end)
			ev("open_talk is_talking=" .. tostring(talking))
			L._talk = { lo = lo, npc = npc }
			if opts.shot then return L.screenshot(opts.shot) end
		end,
		function(c, shot)
			return L.done(okt and talking == true, "is_talking=" .. tostring(talking), shot)
		end,
	}, "open_talk")
end

function L.close_talk()
	local tk = L._talk
	if tk == nil then return false end
	pcall(function() tk.lo:stop_talk() end)
	pcall(function() tk.npc:stop_talk() end)
	L._talk = nil
	return true
end

-- ---------------------------------------------------------------------------------------------------- tagged screenshot (client)
local function shot_files()
	local out = {}
	pcall(function()
		local flist = getFS():file_list_open_ex("$screenshots$", bit_or(FS.FS_ListFiles, FS.FS_RootOnly), "*")
		for i = 0, flist:Size() - 1 do
			local nm = flist:GetAt(i):NameFull()
			if string.find(string.lower(nm), "%.[jptb][pnmg][gap]?$") then out[nm] = true end
		end
	end)
	return out
end

-- L.screenshot(tag) -> ACTION: engine screenshot (console "screenshot jpg"), then renames the new file to  qa_<tag>__<original>.
-- Result: the final file name | nil, err.   (The file lands in this client's screenshots folder; run_coop copies it into the result dir.)
function L.screenshot(tag)
	tag = string.gsub(tostring(tag or "shot"), "[^%w_%-]", "_")
	local before, new
	return L.seq({
		function()
			before = shot_files()
			local ok, err = pcall(function() get_console():execute("screenshot jpg") end)
			if not ok then return L.done(nil, tostring(err)) end
			return L.wait_for(function()
				for name in pairs(shot_files()) do if not before[name] then new = name return true end end
				return false
			end, 15)
		end,
		function(c, found)
			if not found then ev("SHOT " .. tag .. " no new file in 15 s") return L.done(nil, "no screenshot file appeared") end
			return L.wait(1)  -- let the engine finish writing
		end,
		function()
			local final = "qa_" .. tag .. "__" .. new
			local okr = pcall(function()
				getFS():file_rename(getFS():update_path("$screenshots$", new), getFS():update_path("$screenshots$", final), true)
			end)
			if not okr then final = new end
			ev("SHOT " .. tag .. " -> " .. final)
			return L.done(final)
		end,
	}, "screenshot")
end

-- ---------------------------------------------------------------------------------------------------- game language
-- L.language() -> "rus" | "eng" : which language db the engine mounted (the string of a base option, Windowed, is Latin or Cyrillic).
-- Switching the language for a test run is done OUTSIDE the game with tools\stalker_xrmpe\qa_lang.ps1 (registry InstallLang, always restored).
function L.language()
	local ok, s = try(function() return game.translate_string("st_opt_windowed") end)
	if not ok or s == nil then return nil, "translate_string failed" end
	for i = 1, #s do if string.byte(s, i) >= 0xA8 then return "rus", s end end
	return "eng", s
end

ev("qa_lib " .. L.version .. " loaded")
end
