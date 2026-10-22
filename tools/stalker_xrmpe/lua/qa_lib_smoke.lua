--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped): Cordon listen-mode smoke run for qa_lib.lua.  Every library function is exercised once and writes
-- one PASS/FAIL line (qa_assert.log).  The run restarts the Lua VM twice (party-vote travel, then load of the last save); progress
-- is kept in the persisted state (L.state_*).  Written as step lists (qa_lib actions), no coroutines.
--
--   powershell -NoProfile -ExecutionPolicy Bypass -File ..\run_coop.ps1 -Map coop_l01_escape -Owner botlib -Mode listen -Clients 1 `
--       -Hooks C:\...\tools\stalker_xrmpe\lua\qa_lib_smoke.lua -SoakSeconds 600 -CompareTimeout 10 -ResultDir <dir>
--   -Cfg parts=base,npc,hits,talk,save,travel,death   (default: all; "travel" also does Garbage and the load of the last save, "death" runs last)
-------------------------------------------------------------------------------------------------------
local L = qa_lib

local function parts()
	local p = qa.cfg.parts
	if p == nil or p == "" or p == "all" then return { base = 1, npc = 1, hits = 1, talk = 1, save = 1, travel = 1, death = 1 } end
	local r = {}
	for w in string.gmatch(p, "[^,]+") do r[w] = 1 end
	return r
end

local function check(name, ok, detail)
	qa.assert("QL " .. name, ok == true, detail)
end

local TRADER_BUNKER = { -243.0, -24.2, -135.0 }

local function run_base()
	return L.seq({
		function(c)
			local pl, pid = L.player()
			check("player() finds the local player", pl ~= nil and pid ~= nil, tostring(pid))
			check("local_player() and level_name()", L.local_player() ~= nil and L.level_name() == "coop_l01_escape", tostring(L.level_name()))
			-- persisted state
			L.state_set("smoke_probe", "alpha 7")
			check("state_set / state_get", L.state_get("smoke_probe") == "alpha 7", tostring(L.state_get("smoke_probe")))
			L.state_set("smoke_probe", nil)
			-- story flags (shared) and info portions (per player)
			check("flag_give sets the shared story flag", L.flag_give("QA_LIB_SMOKE_FLAG") and L.flag_has("QA_LIB_SMOKE_FLAG"))
			check("flag_clear clears it", L.flag_clear("QA_LIB_SMOKE_FLAG") and not L.flag_has("QA_LIB_SMOKE_FLAG"))
			c.n = L.info_give("QA_LIB_SMOKE_INFO")
			return L.wait(1)
		end,
		function(c)
			check("info_give / info_has (per-player info portion)", c.n >= 1 and L.info_has("QA_LIB_SMOKE_INFO"), "players given " .. tostring(c.n))
			L.info_clear("QA_LIB_SMOKE_INFO")
			return L.wait(1)
		end,
		function(c)
			check("info_clear removes it", not L.info_has("QA_LIB_SMOKE_INFO"))
			L.set_money(nil, 1234)
			return L.wait(1)
		end,
		function(c)
			check("set_money", L.money() == 1234, tostring(L.money()))
			L.give_money(nil, -234)
			return L.wait(1)
		end,
		function(c)
			check("give_money (delta)", L.money() == 1000, tostring(L.money()))
			c.ids = L.give_item(nil, "medkit", 2)
			c.ammo = L.give_item(nil, "ammo_9x18_fmj", 30)
			return L.wait(3)
		end,
		function(c)
			local ids, ammo = c.ids, c.ammo
			check("give_item creates server objects", ids ~= nil and #ids == 2 and ammo ~= nil, tostring(ids and #ids))
			local srv, src = L.dump_inventory(nil, "server", "server")
			local mk = 0
			for _, it in ipairs(srv or {}) do if it.section == "medkit" then mk = mk + 1 end end
			check("dump_inventory (server scan) lists the 2 medkits", mk == 2 and src == "server", "medkits " .. mk .. ", items " .. tostring(srv and #srv))
			local onl, src2 = L.dump_inventory(nil, "online")
			local mk2, eq = 0, 0
			for _, it in ipairs(onl or {}) do
				if it.section == "medkit" then mk2 = mk2 + 1 end
				if it.slot and it.slot > 0 then eq = eq + 1 end
			end
			check("dump_inventory (online walk) lists the medkits and slots", onl ~= nil and #onl > 0 and mk2 == 2, "source " .. tostring(src2) .. ", medkits " .. mk2 .. ", equipped " .. eq .. ", items " .. tostring(onl and #onl))
			check("count_item", L.count_item(nil, "medkit") == 2, tostring(L.count_item(nil, "medkit")))
			-- language
			local lang, s = L.language()
			check("language() reads the mounted language", lang == (qa.cfg.lang or "eng"), tostring(lang) .. " (" .. tostring(s) .. ")")
		end,
	}, "base")
end

local function run_npc()
	return L.seq({
		function(c)
			-- spawn near the player with a relation, then the relative health setter on a real NPC
			local se, id = L.spawn_npc("sim_default_bandit_0", { relation = "friend", offset = { 4, 0, 0 } })
			check("spawn_npc creates the bandit", se ~= nil, tostring(id))
			if se == nil then return L.done() end
			c.id = id
			return L.wait_for(function() return L.online(id) ~= nil end, 45)
		end,
		function(c, up)
			check("spawned NPC comes online", up)
			if not up then return L.done() end
			return L.wait_for(function() return L.get_relation(L.online(c.id), nil) == "friend" end, 15)
		end,
		function(c)
			local id = c.id
			local n, pl = L.online(id), L.player(nil)
			local function raw(tag)
				local ok1, r = pcall(function() return n:relation(pl) end)
				local ok2, g = pcall(function() return n:goodwill(pl) end)
				local ok3, gg = pcall(function() return n:general_goodwill(pl) end)
				local ok4, cg = pcall(function() return n:community_goodwill(pl:character_community(), id) end)
				L.ev(string.format("REL %s relation=%s goodwill=%s general=%s community=%s", tag, tostring(r), tostring(g), tostring(gg), tostring(cg)))
			end
			raw("after spawn_npc(relation=friend)")
			check("spawn_npc relation=friend applied (relation() reads friend)", L.get_relation(n, nil) == "friend", tostring(L.get_relation(n, nil)))
			L.set_relation(n, "friend", nil)
			raw("after set_relation friend")
			pcall(function() n:force_set_goodwill(1000, pl) end)
			raw("after force_set_goodwill 1000")
			check("some friend call makes relation() read friend", L.get_relation(n, nil) == "friend", tostring(L.get_relation(n, nil)))
			local ok2 = L.set_relation(n, "enemy", nil)
			raw("after set_relation enemy")
			check("set_relation enemy and read back", ok2 and L.get_relation(n, nil) == "enemy", tostring(L.get_relation(n, nil)))
			return L.wait(1)
		end,
		function(c)
			L.dump_npcs(nil, 40, "npc_part")
			L.remove(c.id)      -- the hostile bandit must not shoot at the player during the health test
			return L.wait(4)
		end,
		function(c)
			c.p = L.player(nil)
			L.heal(c.p)
			return L.wait(2)
		end,
		function(c)
			c.h0 = c.p.health
			c.p.health = -0.2
			c.same = c.p.health
			return L.wait(2)
		end,
		function(c)
			local h1 = c.p.health
			check("engine health setter is RELATIVE (x adds x; applied on the next frame)", math.abs((c.h0 - 0.2) - h1) < 0.06, string.format("%.3f -> same frame %.3f -> 2 s later %.3f", c.h0, c.same, h1))
			L.set_health(c.p, 0.6)
			return L.wait(2)
		end,
		function(c)
			local h2 = c.p.health
			check("set_health sets an absolute value (read 2 s later)", math.abs(h2 - 0.6) < 0.08, string.format("%.3f", h2))
			L.heal(c.p)
			return L.wait(2)
		end,
		function(c)
			local h3 = c.p.health
			check("heal / positive x adds (capped at 1)", h3 > 0.95, string.format("%.3f", h3))
		end,
		function(c)
			local list = L.npcs_near(nil, 250)
			local withjob = 0
			for _, x in ipairs(list or {}) do if x.job ~= "-" then withjob = withjob + 1 end end
			check("npcs_near lists NPCs around the player (name/section/job/scheme)", list ~= nil and #list >= 3, string.format("%d NPCs within 250 m, %d with a smart-terrain job", list and #list or 0, withjob))
			L.dump_npcs(nil, 250, "cordon", { stalkers_only = true })
		end,
	}, "npc")
end

local function run_hits()
	return L.seq({
		function(c) return L.hits_to_kill({ section = "sim_default_bandit_0", power = 0.5518, bone = "bip01_spine1" }) end,
		function(c, r1, e1)
			check("hits_to_kill (body, PM-sized hits) kills the bandit", r1 ~= nil and r1.killed == true, r1 and string.format("%d hits (hp0 %.2f)", r1.hits, r1.hp0 or -1) or tostring(e1))
			c.r1 = r1
			return L.wait(3)
		end,
		function(c) return L.hits_to_kill({ section = "sim_default_bandit_0", power = 0.5518, bone = "bip01_head" }) end,
		function(c, r2, e2)
			check("hits_to_kill (head) kills the bandit", r2 ~= nil and r2.killed == true, r2 and string.format("%d hits (hp0 %.2f)", r2.hits, r2.hp0 or -1) or tostring(e2))
			if c.r1 and r2 then L.ev(string.format("HITS summary body=%d head=%d", c.r1.hits, r2.hits)) end
		end,
	}, "hits")
end

local function run_talk()
	return L.seq({
		function(c) return L.teleport(nil, TRADER_BUNKER) end,
		function(c, ok, why)
			check("teleport moves the player to the trader bunker", ok == true, tostring(why))
			return L.wait(8)
		end,
		function(c) return L.open_talk("sidorovich", { shot = "smoke_talk" }) end,
		function(c, ok2, why2, shot)
			check("open_talk opens the Sidorovich window (is_talking)", ok2 == true, tostring(why2) .. ", shot " .. tostring(shot))
			return L.wait(2)
		end,
		function(c)
			L.close_talk()
			return L.wait(2)
		end,
		function(c)
			local lo = L.local_player()
			local okt, talking = L.try(function() return lo:is_talking() end)
			check("close_talk closes the window", okt and talking == false, tostring(talking))
			return L.screenshot("smoke_tag")
		end,
		function(c, f)
			check("screenshot is taken and tagged", f ~= nil and string.find(f, "^qa_smoke_tag__") ~= nil, tostring(f))
		end,
	}, "talk")
end

local function run_save()
	return L.seq({
		function(c)
			L.flag_give("QA_LIB_SMOKE_MARK")
			return L.save()
		end,
		function(c, name, err)
			check("save() writes a save file the way the server does", name ~= nil, tostring(name or err))
			local sv = L.saves()
			L.ev("saves in $game_saves$: " .. #sv)
			for _, s in ipairs(sv) do L.ev("SAVE " .. s.name .. " " .. tostring(s.modif)) end
		end,
	}, "save")
end

local function run_death()
	return L.seq({
		function(c)
			local se, id = L.spawn_npc("sim_default_bandit_0", { offset = { 4, 0, 0 } })
			check("death: killer NPC spawned", se ~= nil)
			if se == nil then return L.done() end
			c.id = id
			return L.wait_for(function() return L.online(id) ~= nil end, 45)
		end,
		function(c)
			local killer = L.online(c.id)
			check("death: killer is online", killer ~= nil)
			if killer == nil then return L.done() end
			return L.kill_player(nil, killer)
		end,
		function(c, ok, how)
			check("kill_player kills the player with the NPC as attacker", ok == true, tostring(how))
			return L.wait_for(function() return #L.players() >= 1 end, 90)
		end,
		function(c, back)
			check("player respawns after the death (harness respawn)", back)
			return L.wait(3)
		end,
		function(c) L.remove(c.id) end,
	}, "death")
end

local function part(want, key, make)
	return function(c)
		if want[key] then return L.protect(make(), key) end
	end
end

qa.once("qa_lib_smoke", function(t, lo)
	if not L.on_server() or L.is_dedicated() then return end
	if _G.__qa_smoke_started then return end     -- the file is appended to three scripts that can load at different times: start once
	_G.__qa_smoke_started = true
	local want = parts()
	L.task("smoke", {
		function(c)
			c.stage = L.state_get("stage", 0)
			c.lvl = L.level_name()
			L.ev("SMOKE stage " .. tostring(c.stage) .. " on " .. tostring(c.lvl))
			return L.wait(6)
		end,
		function(c)
			if c.stage >= 3 then L.ev("SMOKE already finished (VM restarted after the death test)") return L.done() end
			if c.stage == 1 then return L.jump("arrived") end
			if c.stage == 2 then return L.jump("loaded") end
		end,
		-- stage 0: Cordon, fresh start
		part(want, "base", run_base),
		part(want, "npc", run_npc),
		part(want, "hits", run_hits),
		part(want, "talk", run_talk),
		part(want, "save", run_save),
		function(c)
			if want.travel then
				L.state_set("stage", 1)
				c.travel = true
				return L.travel("gar", { timeout = 170, fallback = true })
			end
			if want.death then return L.protect(run_death(), "death") end
		end,
		function(c, ok, why)
			if c.travel then
				-- only reached when the level did NOT change
				check("travel('gar') changes the level via the party vote", ok == true, tostring(why))
				L.state_set("stage", 0)
			end
			L.ev("SMOKE complete (no travel)")
			check("smoke run finished", true)
			return L.done()
		end,
		-- stage 1: arrived on Garbage in a new VM
		"arrived",
		function(c)
			local arrived, dest, secs = L.travel_arrived()
			check("travel arrived on Garbage after the party vote", arrived and dest == "coop_l02_garbage", string.format("%s in %s s", tostring(dest), tostring(secs)))
			return L.wait(8)
		end,
		function(c)
			L.dump_npcs(nil, 120, "garbage", { stalkers_only = true })
			if not want.save then L.state_set("stage", 0) check("smoke run finished", true) return L.done() end
			-- the engine also autosaves on every level change, so the newest save is the one made here, on Garbage:
			-- set a flag, save, clear the flag, load the newest save: the flag must come back and the level stays Garbage
			L.flag_give("QA_LIB_SMOKE_G")
			return L.save()
		end,
		function(c, name, err)
			check("save() on the new level", name ~= nil, tostring(name or err))
			L.flag_clear("QA_LIB_SMOKE_G")
			check("flag cleared before the load", not L.flag_has("QA_LIB_SMOKE_G"))
			L.state_set("stage", 2)
			L.ev("SMOKE loading the newest save")
			L.load_last()
			return L.wait(120)
		end,
		function(c)
			check("load_last reloaded the level", false, "level did not reload in 120 s")
			return L.done()
		end,
		-- stage 2: after the load of the newest save
		"loaded",
		function(c)
			check("load_last: newest save (made on Garbage) is loaded", c.lvl == "coop_l02_garbage", tostring(c.lvl))
			check("load_last: the flag cleared after the save is back (state restored from the save)", L.flag_has("QA_LIB_SMOKE_G"))
			check("load_last: the flag set on Cordon before the first save is still there", L.flag_has("QA_LIB_SMOKE_MARK"))
			L.state_set("stage", 3)
			if want.death then return L.seq({ function() return L.wait(4) end, function() return L.protect(run_death(), "death") end }) end
		end,
		function(c)
			L.ev("SMOKE complete")
			check("smoke run finished", true)
		end,
	})
end)
