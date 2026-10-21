-- Observer for Bar sounds on a CLIENT role. Wraps sound_theme.play/stop_snd_obj_on_client and polls the object_sound_table.
bmc_state = bmc_state or {}
if not bmc_wrapped then
	bmc_wrapped = true
	local op = sound_theme.play_snd_obj_on_client
	sound_theme.play_snd_obj_on_client = function(obj_id, snd_id, file_number, start_from)
		local th = sound_theme.object_sound_table[snd_id]
		local o = db.storage[obj_id] and db.storage[obj_id].object
		local p = o and o:position()
		local a = getLocalActor and getLocalActor()
		local d = (p and a) and p:distance_to(a:position()) or -1
		live.note(string.format("BMC PLAY  t=%d obj=%s id=%s pos=%s theme=%s file=#%s %s start_from=%s dist_to_me=%.1f",
			time_global(), o and o:name() or "?", tostring(obj_id), p and string.format("%.1f,%.1f,%.1f", p.x, p.y, p.z) or "?",
			th and th.section or "?", tostring(file_number), th and tostring(th.sound[file_number]) or "?", tostring(start_from), d))
		return op(obj_id, snd_id, file_number, start_from)
	end
	local os_ = sound_theme.stop_snd_obj_on_client
	sound_theme.stop_snd_obj_on_client = function(snd_id)
		local th = sound_theme.object_sound_table[snd_id]
		live.note(string.format("BMC STOP  t=%d theme=%s", time_global(), th and th.section or "?"))
		return os_(snd_id)
	end
end
function bmc_poll()
	local seen = {}
	for k, th in pairs(sound_theme.object_sound_table) do
		if not seen[th] and th.snd_obj ~= nil then
			seen[th] = true
			local pl = th.snd_obj:playing()
			local rec = bmc_state[th]
			if pl and (rec == nil or rec.snd ~= th.snd_obj) then
				bmc_state[th] = { snd = th.snd_obj, t0 = time_global() }
				live.note(string.format("BMC HEARD t=%d theme=%s playing (client sound object started)", time_global(), th.section))
			elseif (not pl) and rec ~= nil and rec.snd == th.snd_obj and not rec.ended then
				rec.ended = true
				live.note(string.format("BMC ENDED t=%d theme=%s after %.1f s", time_global(), th.section, (time_global() - rec.t0) / 1000))
			end
		end
	end
	live.defer(0.5, bmc_poll)
end
if not bmc_started then
	bmc_started = true
	live.note("BMC observer (client) started t=" .. time_global())
	live.defer(0.5, bmc_poll)
end
return "client observer on"
