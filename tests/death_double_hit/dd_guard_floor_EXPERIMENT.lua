-- TEST ONLY: experimental floor guard G1 for the double GE_DIE crash. Appended after the driver.
-- Per frame, every real player body: when health <= F (ctl "gF=<x>", default 0.3) and the guard is switched on (ctl word "guard"),
-- the body is made invulnerable and killed ONCE by script (game_object:kill), so no later hit of the same frame can send a second GE_DIE.
if not _G.dd_g2 then
_G.dd_g2 = { done = {}, last = -1, cfg_t = -10000, on = false, F = 0.3, n = 0 }
local g = _G.dd_g2
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function lp(name) return getFS():update_path("$logs$", name) end
local function ev(msg)
	local f = io.open(lp("dd_guard2.log"), "a")
	if f then f:write(string.format("[%s g=%d] %s\n", os.date("%H:%M:%S"), safe(time_global) or 0, tostring(msg))) f:close() end
end
local function cfg_refresh(now)
	if now - g.cfg_t < 1000 then return end
	g.cfg_t = now
	local on, F = false, 0.3
	local function scan(path)
		local f = io.open(path, "r")
		if not f then return end
		for line in f:lines() do
			if string.find(line, "^%s*guard%s*$") or string.find(line, "^%s*dd_guard%s*=%s*1") or string.find(line, "^%s*guard%s*=%s*1") then on = true end
			local v = string.match(line, "^%s*g?F%s*=%s*([%d%.]+)") or string.match(line, "^%s*dd_gF%s*=%s*([%d%.]+)")
			if v then F = tonumber(v) or F end
		end
		f:close()
	end
	scan(lp("qa_role.txt")); scan(lp("dd_ctl.txt"))
	g.on, g.F = on, F
end
local function tick()
	if safe(OnServer) ~= true then return end
	local now = safe(time_global) or 0
	if now == g.last then return end
	g.last = now
	cfg_refresh(now)
	if not g.on or type(db.mp_actors) ~= "table" then return end
	for id, o in pairs(db.mp_actors) do
		if o ~= nil and not g.done[id] then
			local nm = safe(function() return string.lower(tostring(o:name())) end)
			if nm and string.find(nm, "^qa[a-d]$") and safe(function() return o:alive() end) then
				local h = safe(function() return o.health end)
				if h and h <= g.F then
					g.done[id] = now
					g.n = g.n + 1
					local ok1 = pcall(function() o:invulnerable(true) end)
					local ok2 = pcall(function() o:kill(o) end)
					ev(string.format("GUARD fired #%d on %s#%d health=%.3f F=%.2f invulnerable ok=%s kill ok=%s", g.n, nm, id, h, g.F, tostring(ok1), tostring(ok2)))
				end
			end
		end
	end
end
do
	local ok, err = pcall(function() level.add_call(tick, function() end) end)
	local f = io.open(getFS():update_path("$logs$", "dd_guard2_load.txt"), "a")
	if f then f:write("dd_guard2 loaded, add_call ", ok and "ok" or tostring(err), "\n") f:close() end
end
end
