--@qa_lib
-- Regression hook for the qa_lib 1.2 fixes (run once after a change to qa_lib.lua).  Cordon, listen mode, one client, about 3 minutes:
--   run_coop.ps1 -Map coop_l01_escape -Owner <unique> -Mode listen -Clients 1 -Hooks <this file> -SoakSeconds 150 -CompareTimeout 10 -ResultDir <dir>
-- Then:  python tools\stalker_xrmpe\qa_verdict.py <dir>   (every "RG ..." line in qa_assert.log must be PASS).
-- Proves: qa.once starts the body ONCE per VM although the hooks file is appended to three scripts; hits_to_kill never reports a dead target as
-- a kill (res.killed / "already dead" error), respawns spawned targets, get_relation takes an id; save() returns the save name.
local L = qa_lib
local FIRE = L.PLACES.cordon_fire

local function check(name, ok, detail) qa.assert("RG " .. name, ok == true, detail) end

qa.once("regress_main", function(t, lo)
	_G.RG_STARTS = (_G.RG_STARTS or 0) + 1
	L.ev("RG body start #" .. _G.RG_STARTS)
	L.task("regress", {
		function(c) L.god(true) return L.wait(8) end,
		function(c)
			check("qa.once body ran exactly once in this VM", _G.RG_STARTS == 1, "starts=" .. tostring(_G.RG_STARTS))
			return L.teleport(nil, { FIRE[1] + 3, FIRE[2], FIRE[3] })
		end,
		function(c, ok, how)
			check("teleport next to the village fire (L.PLACES.cordon_fire)", ok, tostring(how))
			return L.wait(4)
		end,
		function(c)
			local se, id = L.spawn_npc("sim_default_bandit_0", { relation = "enemy", offset = { 6, 0, 0 } })
			check("spawn hostile bandit (god mode on first)", se ~= nil, tostring(id))
			c.bid = id
			return L.wait(4)
		end,
		function(c)
			local rel = c.bid and L.get_relation(c.bid, nil) or nil
			check("get_relation takes an object id", rel == "enemy" or rel == "neutral" or rel == "friend", tostring(rel))
			return L.hits_to_kill({ id = c.bid, power = 0.5518 })
		end,
		function(c, res, err)
			-- the villagers often kill the bandit first: that must come back as an error, never as hits=0 dead=true
			if res ~= nil then
				check("hits_to_kill with id: killed means hits > 0", res.killed == true and res.hits > 0, "hits " .. tostring(res.hits) .. " dead " .. tostring(res.dead))
			else
				check("hits_to_kill with id: an already dead target is an error", string.find(tostring(err), "already dead", 1, true) ~= nil, tostring(err))
			end
			return L.hits_to_kill({ section = "sim_default_bandit_0", power = 0.5518 })
		end,
		function(c, res, err)
			check("hits_to_kill with section spawns its own target and kills it", res ~= nil and res.killed == true and res.hits > 0, res and ("hits " .. res.hits .. " hp0 " .. string.format("%.2f", res.hp0 or -1)) or tostring(err))
			return L.save()
		end,
		function(c, name)
			check("save() result is the save name string", type(name) == "string" and #name > 0, tostring(name))
			check("run finished", true)
			return L.done()
		end,
	})
end)
