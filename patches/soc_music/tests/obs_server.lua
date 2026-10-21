-- Observer for Bar sounds on the SERVER role (S). Polls xr_sound.sound_table every 0.25 s and logs start/end of object sounds.
bm_state = bm_state or {}
local function oname(id)
	local st = db.storage[id]
	local o = st and st.object
	if o then
		local p = o:position()
		return o:name(), string.format("%.1f,%.1f,%.1f", p.x, p.y, p.z)
	end
	return "?", "?"
end
function bm_poll()
	local seen = {}
	for id, th in pairs(xr_sound.sound_table) do
		if th.class_id == "object_sound" then
			seen[id] = true
			local rec = bm_state[id]
			if rec == nil or rec.snd ~= th.snd_obj then
				if rec ~= nil then
					live.note(string.format("BM END   t=%d id=%d %s (replaced)", time_global(), id, tostring(rec.theme)))
				end
				local n, p = oname(id)
				live.note(string.format("BM START t=%d id=%d obj=%s pos=%s theme=%s file=#%s %s sync=%s",
					time_global(), id, n, p, th.section, tostring(th.played_id), tostring(th.sound[th.played_id]), tostring(th.sync)))
				bm_state[id] = { snd = th.snd_obj, theme = th.section, t0 = time_global() }
			end
		end
	end
	for id, rec in pairs(bm_state) do
		if not seen[id] then
			live.note(string.format("BM END   t=%d id=%d %s played %.1f s", time_global(), id, tostring(rec.theme), (time_global() - rec.t0) / 1000))
			bm_state[id] = nil
		end
	end
	live.defer(0.25, bm_poll)
end
if not bm_started then
	bm_started = true
	live.note("BM observer (server) started t=" .. time_global())
	live.defer(0.25, bm_poll)
end
return "server observer on"
