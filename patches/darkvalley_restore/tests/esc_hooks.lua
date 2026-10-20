-- Cordon arrival hooks (test only)
if not _G.__dv_boot then
	_G.__dv_boot = true
	pcall(function() coop_scenes.install() end)
end
if not _G.__dv_tips then
	_G.__dv_tips = {}
	pcall(function()
		local orig = news_manager.send_tip
		news_manager.send_tip = function(actor, news_id, timeout, sender, showtime, sender_id)
			_G.__dv_tips[#_G.__dv_tips + 1] = tostring(news_id) .. "|" .. tostring(sender)
			return orig(actor, news_id, timeout, sender, showtime, sender_id)
		end
	end)
end
local function has_tip(id)
	for _, v in ipairs(_G.__dv_tips) do if string.find(v, id, 1, true) then return true, v end end
	return false
end

qa.once("esc_server", function(t, lo)
	if not OnServer() then return end
	if level.name() ~= "coop_l01_escape" then return end
	qa.eventually("Cordon zone esc_return_from_dv exists", function()
		local z = alife():object("esc_return_from_dv")
		if z == nil then return false, "missing" end
		local p = z.position
		return math.abs(p.x - 304.26) < 1 and math.abs(p.z - 5.41) < 1, string.format("clsid %s pos %.1f %.1f %.1f", tostring(z:clsid()), p.x, p.y, p.z)
	end, 60)
	pcall(function() level.set_time_factor(300) end)
end)

qa.once("esc_client", function(t, lo)
	if OnServer() or lo == nil then return end
	if level.name() ~= "coop_l01_escape" then return end
	qa.esc = { stage = 0 }
	qa.hooks.esc_tick = function(t2, lo2)
		local P = qa.esc
		if P.stage == 0 and t2 > 25 then
			pcall(function() story_flags.give_flag("VAL_RAID_START") end)
			local ok, e = pcall(function() lo2:set_actor_position(vector():set(304.3, 16.0, 5.4)) end)
			qa.event("move into esc_return_from_dv " .. tostring(ok) .. " " .. tostring(e))
			P.stage = 1; P.t = t2
			qa.eventually("Cordon: Sidorovich arrival message reached the player", function()
				local ok2, v = has_tip("st_esc_return_dv")
				return ok2, tostring(v)
			end, 90)
			qa.eventually("Cordon: ESC_RETURN_FROM_DV_INFO set after the timer", function()
				return story_flags.has_flag("ESC_RETURN_FROM_DV_INFO"), ""
			end, 120)
		elseif P.stage == 1 and t2 - P.t > 15 then
			pcall(function() get_console():execute("screenshot") end)
			P.stage = 2
		end
	end
end)
