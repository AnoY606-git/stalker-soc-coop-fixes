-- "normal run" side of the README comparison: the same Bar question (stalkers within 60 m of the arrival point) asked through run_coop.ps1.
-- Server role only; qa.assert writes the answer to client_S\qa_assert.log.
local done = false
qa.hooks.bar_census = function(t, lo)
	if done or not OnServer() or level.name() ~= "coop_l05_bar" then return end
	if t < 15 then return end
	done = true
	local p = vector():set(169.4, 0.0, 65.8)
	local n = 0
	for id = 0, 65534 do
		local se = alife():object(id)
		if se ~= nil and se.position:distance_to(p) <= 60 and string.find(se:section_name(), "stalker", 1, true) and se.parent_id == 65535 then
			local ok, alive = pcall(function() return se:alive() end)
			if ok and alive then n = n + 1 end
		end
	end
	qa.assert("bar census: stalkers within 60 m of the arrival point", n > 0, "n=" .. n)
end
