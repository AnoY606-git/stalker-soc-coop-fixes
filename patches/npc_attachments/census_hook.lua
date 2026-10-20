-- census of NPC weapons and installed addons (server side, whole alife)
local did = {}
local function flags_of(o)
	local pk = net_packet()
	o:STATE_Write(pk)
	local n = pk:r_elapsed()
	local last
	local b = {}
	for i = 1, n do b[i] = pk:r_u8() end
	return b[n - 2]
end
local function bit(v, k) return math.floor(v / k) % 2 == 1 end
local function census(tag)
	local sys = system_ini()
	local c = { npc_weapons = 0, sup_scope = 0, sup_sil = 0, sup_gl = 0, scope = 0, sil = 0, gl = 0, any = 0, other_parent_weapons = 0 }
	for id = 1, 65534 do
		local o = alife():object(id)
		if o and o.parent_id ~= 65535 then
			local s = o:section_name()
			if string.find(s, "^wpn_") and not string.find(s, "^wpn_addon") and sys:line_exist(s, "scope_status") then
				local p = alife():object(o.parent_id)
				if p and p:clsid() == clsid.script_stalker then
					c.npc_weapons = c.npc_weapons + 1
					local f = flags_of(o)
					local a = false
					if sys:r_u32(s, "scope_status") == 2 then c.sup_scope = c.sup_scope + 1 end
					if sys:r_u32(s, "silencer_status") == 2 then c.sup_sil = c.sup_sil + 1 end
					if sys:r_u32(s, "grenade_launcher_status") == 2 then c.sup_gl = c.sup_gl + 1 end
					if bit(f, 1) then c.scope = c.scope + 1 a = true end
					if bit(f, 2) then c.gl = c.gl + 1 a = true end
					if bit(f, 4) then c.sil = c.sil + 1 a = true end
					if a then c.any = c.any + 1 end
				else
					c.other_parent_weapons = c.other_parent_weapons + 1
				end
			end
		end
	end
	qa.event(string.format("CENSUS %s npc_weapons=%d attachable(scope=%d silencer=%d launcher=%d) installed(scope=%d silencer=%d launcher=%d) weapons_with_any=%d", tag, c.npc_weapons, c.sup_scope, c.sup_sil, c.sup_gl, c.scope, c.sil, c.gl, c.any))
	return c
end
qa.hooks.census = function(t, lo)
	if not OnServer() then return end
	if type(db.mp_actors) ~= "table" then return end
	local a
	for id, o in pairs(db.mp_actors) do a = o break end
	if not a then return end
	if not did.t0 then did.t0 = t end
	local dt = t - did.t0
	if dt > 3 and not did.c1 then
		did.c1 = true
		local ok, err = pcall(census, qa.cfg.tag or "run")
		if not ok then qa.event("CENSUS error " .. tostring(err)) end
	end
end
