-- TEST ONLY: probe + experimental guard for the double GE_DIE crash. Appended after dd_driver.lua.
-- Registers callback.hit on every real player body (server role) and logs each hit callback (time_global frame, amount, health, attacker, bone).
-- Guard (ctl file dd_ctl.txt contains the word "guard", or role cfg dd_guard=1): the SECOND and later hit callbacks of one body in the same
-- frame set invulnerable(true) for that body until the next frame, so a burst of lethal hits cannot deliver a second GE_DIE.
if not _G.dd_guard then
_G.dd_guard = { reg = {}, fh = {}, inv = {}, last = 0, cfg_t = -10000, on = false, probe = true }
local g = _G.dd_guard

local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function lp(name) return getFS():update_path("$logs$", name) end
local function ev(msg)
	local f = io.open(lp("dd_guard.log"), "a")
	if f then f:write(string.format("[%s g=%d] %s\n", os.date("%H:%M:%S"), safe(time_global) or 0, tostring(msg))) f:close() end
end

local function cfg_refresh(now)
	if now - g.cfg_t < 1000 then return end
	g.cfg_t = now
	local on, probe = false, true
	local function scan(path)
		local f = io.open(path, "r")
		if not f then return end
		for line in f:lines() do
			if string.find(line, "^%s*guard%s*$") or string.find(line, "^%s*dd_guard%s*=%s*1") or string.find(line, "^%s*guard%s*=%s*1") then on = true end
			if string.find(line, "^%s*noprobe") then probe = false end
		end
		f:close()
	end
	scan(lp("qa_role.txt"))
	scan(lp("dd_ctl.txt"))
	g.on, g.probe = on, probe
end

local function on_hit(obj, amount, dir, who, bone)
	local now = safe(time_global) or 0
	local id = safe(function() return obj:id() end) or -1
	local f = g.fh[id]
	if not f or f.t ~= now then f = { t = now, n = 0 }; g.fh[id] = f end
	f.n = f.n + 1
	cfg_refresh(now)
	local hp = safe(function() return obj.health end) or -1
	local alive = safe(function() return obj:alive() end)
	local guarded = false
	if g.on and f.n >= 2 then
		guarded = safe(function() obj:invulnerable(true) return true end) or false
		g.inv[id] = now
	end
	if g.probe then
		ev(string.format("HITCB id=%d frame_n=%d amount=%s hp=%.3f alive=%s who=%s bone=%s inv_before=%s guard_set=%s", id, f.n, tostring(amount), hp, tostring(alive),
			tostring(safe(function() return who:name() end)), tostring(bone), tostring(safe(function() return obj:invulnerable() end)), tostring(guarded)))
	end
end

local function tick()
	if safe(OnServer) ~= true then return end
	local now = safe(time_global) or 0
	-- release the one-frame invulnerability
	for id, t in pairs(g.inv) do
		if now > t then
			local o = safe(level.object_by_id, id)
			if o then pcall(function() o:invulnerable(false) end) end
			g.inv[id] = nil
		end
	end
	if now - g.last < 250 then return end
	g.last = now
	if type(db.mp_actors) ~= "table" then return end
	for id, o in pairs(db.mp_actors) do
		if o ~= nil and not g.reg[id] then
			local nm = safe(function() return string.lower(tostring(o:name())) end)
			if nm and string.find(nm, "^qa[a-d]$") and safe(function() return o:alive() end) then
				local ok, err = pcall(function() o:set_callback(callback.hit, on_hit) end)
				g.reg[id] = true
				ev("hit callback registered on " .. nm .. "#" .. id .. " ok=" .. tostring(ok) .. " " .. tostring(ok and "" or err))
			end
		end
	end
end

do
	local ok, err = pcall(function() level.add_call(tick, function() end) end)
	local f = io.open(getFS():update_path("$logs$", "dd_guard_load.txt"), "a")
	if f then f:write("dd_guard loaded, add_call ", ok and "ok" or tostring(err), "\n") f:close() end
end
end
