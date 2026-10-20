-- QA hook for run_coop.ps1 (dedicated mode, 2 real clients qaA/qaB + server role S):
--   run_coop.ps1 -Map coop_l01_escape -Owner x -Hooks <this file> -ExtraDir <patches\money_transfer\gamedata> -SoakSeconds 150
-- The server (role S) sets the start balances (A 5000, B 0) and watches the server view; A and B drive the transfers through the
-- real client request (game_cl.executeFunctionOnServer) and check their OWN balances and toasts.  Each step is triggered by the observed
-- state (not by a timer), so lag cannot reorder it.  Total money A + B must stay 5000 on the server at every sample.
local TOTAL = 5000
local T = { ph = 0, n_seen = 0, t_ph = nil, sum_bad = nil, sum_ok = 0, setup = false, b_done = false }
local function ev(s) qa.event("MT " .. s) end
local function money(o) if not o then return nil end local ok, v = pcall(function() return o:money() end); return ok and v or nil end
local function me_obj() return db.mp_actors[LocalActor()] end
local function other_id()
	for id in pairs(db.mp_actors) do if id ~= LocalActor() then return id end end
end
local function count() local n = 0 for _ in pairs(db.mp_actors) do n = n + 1 end return n end
local function toast() return coop_money and coop_money.get_last_toast() or "" end
local function has(s, sub) return string.find(s, sub, 1, true) ~= nil end

local function server_ids()
	local a, b
	for id, o in pairs(db.mp_actors) do
		local nm = string.lower(tostring(o:name()))
		if nm == "qaa" then a = id elseif nm == "qab" then b = id end
	end
	return a, b
end

qa.hooks.money_test = function(t, lo)
	local role = qa.cfg.role
	local now = time_global()
	if role == "S" then
		if count() < 2 then return end
		local ia, ib = server_ids()
		if not (ia and ib) then return end
		local A, B = db.mp_actors[ia], db.mp_actors[ib]
		if not T.setup then
			T.setup = true
			A:give_money(TOTAL - money(A)); B:give_money(0 - money(B))
			ev(string.format("S SETUP A(%d)=%s B(%d)=%s", ia, tostring(money(A)), ib, tostring(money(B))))
			T.t_setup = now
			qa.eventually("S1 server view A 4500 B 500", function() return money(A) == 4500 and money(B) == 500, "A=" .. tostring(money(A)) .. " B=" .. tostring(money(B)) end, 150)
			qa.eventually("S2 server view A 4000 B 1000 (refusal and repeat x3 applied once)", function() return money(A) == 4000 and money(B) == 1000, "A=" .. tostring(money(A)) .. " B=" .. tostring(money(B)) end, 150)
			qa.eventually("S3 server view A 5000 B 0 (B gave everything)", function() return money(A) == 5000 and money(B) == 0, "A=" .. tostring(money(A)) .. " B=" .. tostring(money(B)) end, 150)
			qa.eventually("S4 server view A 4000 B 1000 (window click)", function() return money(A) == 4000 and money(B) == 1000 and T.s3, "A=" .. tostring(money(A)) .. " B=" .. tostring(money(B)) end, 150)
		end
		if money(A) == 5000 and money(B) == 0 and T.t_setup and now - T.t_setup > 3000 then T.s3 = true end
		local s = (money(A) or 0) + (money(B) or 0)
		if s ~= TOTAL then T.sum_bad = T.sum_bad or string.format("A=%s B=%s", tostring(money(A)), tostring(money(B))) else T.sum_ok = T.sum_ok + 1 end
		if not T.sum_done and T.sum_ok > 100 and T.s3 and money(A) == 4000 then
			T.sum_done = true
			qa.assert("S5 conservation: A + B == 5000 at every one of " .. T.sum_ok .. " server samples", T.sum_bad == nil, tostring(T.sum_bad))
		end
		return
	end

	local me = me_obj()
	if me == nil or count() < 2 then return end
	local mm = money(me)
	local other = other_id()
	local function go(p) T.ph = p; T.t_ph = now end
	if role == "A" then
		if T.ph == 0 and mm == 5000 then coop_money.clear_last_toast(); coop_money.request(other, 2); go(1)
		elseif T.ph == 1 and mm == 4500 then
			qa.assert("A1 A gave 500: own balance 4500 and sender toast", has(toast(), "500"), toast())
			coop_money.clear_last_toast(); coop_money.request(other, 5); go(2)
		elseif T.ph == 2 and has(toast(), "Not enough") then
			qa.assert("A2 refused when too little (10000 > 4500): balance unchanged", mm == 4500, tostring(mm))
			coop_money.request(other, 2); coop_money.request(other, 2); coop_money.request(other, 2); go(3)
		elseif T.ph == 3 and mm == 4000 then go(4)
		elseif T.ph == 4 and now - T.t_ph > 6000 then
			qa.assert("A3 repeat/lag: three identical requests in one tick applied once (4000 after settling)", mm == 4000, tostring(mm))
			go(5)
		elseif T.ph == 5 and mm == 5000 then
			qa.assert("A4 received everything B had (balance 5000) + receiver toast", has(toast(), "gave you"), toast())
			coop_money.clear_last_toast(); coop_money.request(LocalActor(), 1); go(6)
		elseif T.ph == 6 and has(toast(), "not available") then
			qa.assert("A5 self transfer refused: balance unchanged", mm == 5000, tostring(mm))
			coop_money.open_window(other)
			qa.assert("A6 window created", coop_money.get_ui() ~= nil, "")
			local f = io.open(getFS():update_path("$logs$", "qa_cmd.txt"), "a")
			if f then f:write("screenshot\nconsole screenshot qashot_money\nconsole screenshot jpg\n"); f:close() end
			go(7)
		elseif T.ph == 7 and now - T.t_ph > 4000 then
			coop_money.get_ui():OnAmount(3); go(8)
		elseif T.ph == 8 and mm == 4000 then
			qa.assert("A7 window click 1000: balance 4000", true, "")
			go(9)
		end
	else
		if T.ph == 0 and mm == 500 then
			qa.assert("B1 received 500 from A: own balance 500 + receiver toast", has(toast(), "gave you") and has(toast(), "500"), toast())
			go(1)
		elseif T.ph == 1 and mm == 1000 then
			qa.assert("B2 balance 1000 after settling (repeat applied once)", true, "")
			go(2)
		elseif T.ph == 2 and now - T.t_ph > 6000 then
			qa.assert("B3 still 1000 after 6 s", mm == 1000, tostring(mm))
			coop_money.clear_last_toast(); coop_money.request(other, 0); go(3)
		elseif T.ph == 3 and mm == 0 then
			qa.assert("B4 gave everything: own balance 0 + sender toast", has(toast(), "1 000"), toast())
			go(4)
		elseif T.ph == 4 and mm == 1000 then
			qa.assert("B5 received 1000 from A via the window: own balance 1000", true, "")
			go(5)
		end
	end
end
