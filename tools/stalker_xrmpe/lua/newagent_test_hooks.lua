--@qa_lib
-- Independent tester hook (new-agent test of qa_lib, written from QA_LIB.md): hostile bandit, hits to kill, NPCs near the rookie
-- village fire, save + load, inventory dump.  Cordon, listen mode.
local L = qa_lib

local FIRE = { -206.9, -19.6, -140.1 }

local function check(name, ok, detail) qa.assert("NA " .. name, ok == true, detail) end

qa.once("newagent_test", function(t, lo)
	if _G.NA_STARTED then L.ev("NA duplicate start ignored") return end
	_G.NA_STARTED = true
	local stage = L.state_get("na_stage", 0)
	if stage == 1 then
		-- after load_last: the VM restarted
		L.task("after load", {
			function(c) return L.wait(8) end,
			function(c)
				check("flag set before the save is still set after load", L.flag_has("NA_MARK"), tostring(L.flag_has("NA_MARK")))
				local inv = L.dump_inventory(nil, "after_load")
				check("dump_inventory after load returns a list", inv ~= nil, inv and tostring(#inv) or "nil")
				L.state_set("na_stage", 2)
				check("run finished", true)
				return L.done()
			end,
		})
		return
	end
	if stage >= 2 then L.ev("NA already finished") return end
	L.task("newagent", {
		function(c) L.god(true) return L.wait(10) end,
		function(c)
			local inv = L.dump_inventory(nil, "start")
			check("dump_inventory at start returns a list", inv ~= nil, inv and tostring(#inv) or "nil")
			return L.teleport(nil, { FIRE[1] + 3, FIRE[2], FIRE[3] })
		end,
		function(c, ok, how)
			check("teleport next to the village fire", ok, tostring(how))
			return L.wait(5)
		end,
		function(c)
			local se, id = L.spawn_npc("sim_default_bandit_0", { relation = "enemy", offset = { 6, 0, 0 } })
			check("spawn hostile bandit", se ~= nil, tostring(id))
			c.bid = id
			return L.wait(4)
		end,
		function(c)
			if c.bid then
				local rel = L.get_relation(L.online(c.bid), nil)
				check("bandit reads enemy", rel == "enemy", tostring(rel))
			end
			return L.hits_to_kill({ id = c.bid, power = 0.5518 })
		end,
		function(c, res, err)
			check("hits_to_kill returned a result", res ~= nil, tostring(err))
			check("target died", res and res.dead == true, res and ("hits " .. tostring(res.hits)) or tostring(err))
			if res then L.ev("NA HITS " .. tostring(res.hits)) end
			local list, e = L.dump_npcs(FIRE, 15, "fire")
			check("dump_npcs near the fire returns a list", list ~= nil, list and (#list .. " npcs") or tostring(e))
			c.n = list and #list or -1
			return L.wait(1)
		end,
		function(c)
			L.flag_give("NA_MARK")
			return L.save()
		end,
		function(c, ok, name)
			check("save() succeeded", type(ok) == "string", tostring(ok))
			L.state_set("na_stage", 1)
			L.load_last()
			return L.wait(120)
		end,
		function(c)
			check("load_last reloaded the level", false, "level did not reload in 120 s")
			return L.done()
		end,
	})
end)
