--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Hook file for tools/stalker_xrmpe/run_coop.ps1, patch host_settings (coop_settings.ltx).
-- Cordon, LISTEN mode, one client (the host). Takes about 3 minutes:
--   powershell -NoProfile -ExecutionPolicy Bypass -File tools\stalker_xrmpe\run_coop.ps1 -Map coop_l01_escape -Owner hostcfg -Mode listen -Clients 1 `
--     -Hooks <this file> -SoakSeconds 170 -CompareTimeout 10 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir> --prefix HC      (every "HC ..." line in client_A\qa_assert.log must be PASS)
-- The test profile app data (<game>\_appdata_qa_<tag>_A\) is brand new, so coop_settings.ltx does not exist when the server starts:
--   1. the file was CREATED on the first start (host_cfg.log has "file created with the defaults") and holds every setting at its db default
--   2. phase A: the hook writes the file with player_damage_mult = 1.0, calls coop_host_cfg.reload() -> start line shows damage.player_damage_mult=1(file),
--      coop_balance.cfg() reads 1.0, hits-to-kill of a Cordon bandit with one Makarov-sized hit (power 0.5518) = N1 hits (3 expected)
--   3. phase B: the hook writes player_damage_mult = 3.0 and more overrides, reload -> the SAME probe needs fewer hits (1 expected), and every consumer
--      shows its override (enemy scaling max_factor, box loot chances / weights, mutant part chance, repeat-quest cooldown)
--   4. phase C: a bad value ("banana") and a missing key fall back to the db default without an error; deleting the file makes the server write it again
-- Needs -Mode listen (the host is the server and the player). In dedicated mode the role S runs the same steps and role A only checks that a client
-- ignores the file.
-------------------------------------------------------------------------------------------------------
local L = qa_lib

local function check(name, ok, detail) qa.assert("HC " .. name, ok == true, detail) end
local function ev(s) qa.event("HC " .. tostring(s)) end

local function read_all(path)
	local f = io.open(path, "r")
	if not f then return nil end
	local t = f:read("*a")
	f:close()
	return t
end

local function write_cfg(text)
	local f = io.open(coop_host_cfg.path(), "w")
	if not f then return false end
	f:write(text)
	f:close()
	return true
end

local function has(s, needle) return s ~= nil and string.find(s, needle, 1, true) ~= nil end

local PHASE_A = "[damage]\nplayer_damage_mult = 1.0\n"

local PHASE_B = "[damage]\nplayer_damage_mult = 3.0   ; host: triple player damage\n"
	.. "[enemy_scaling]\nmax_factor = 1.75\nhuman_extra_per_player = 0.25\n"
	.. "[box_loot]\nwood_chance = 100\nmetal_chance = 0\n"
	.. "[box_loot_items]\nmedkit = 0\nvodka = 77\n"
	.. "[mutant_loot]\nmutant_dog_part = 1\n"
	.. "[repeat_quests]\ncooldown_min = 60\n"
	.. "[roaming]\nstay_min = 11\n"

local PHASE_C = "[damage]\nplayer_damage_mult = banana\n[ammo]\nmax_players = 3\n"

local function client_check()
	-- a joined client never reads the file: it gets the default whatever the file says
	check("client: coop_host_cfg.num returns the default", coop_host_cfg.num("damage", "player_damage_mult", 1.5) == 1.5,
		tostring(coop_host_cfg.num("damage", "player_damage_mult", 1.5)))
	check("client: coop_host_cfg.bool returns the default", coop_host_cfg.bool("damage", "log", true) == true)
end

qa.once("hostcfg_main", function(t, lo)
	if not OnServer() then
		client_check()
		return
	end
	local logpath = getFS():update_path("$logs$", "host_cfg.log")
	local res = {}
	L.task("hostcfg", {
		function(c) L.god(true) return L.wait(10) end,

		-- 1. the file was created on the first server start
		function(c)
			local path = coop_host_cfg.path()
			ev("settings file: " .. tostring(path))
			local before = read_all(path)
			check("file exists after the first server start", before ~= nil)
			check("file holds the db defaults (player_damage_mult = 1.5)", has(before, "player_damage_mult = 1.5"))
			check("file holds every section", has(before, "[damage]") and has(before, "[ammo]") and has(before, "[enemy_scaling]") and has(before, "[box_loot]")
				and has(before, "[box_loot_items]") and has(before, "[repeat_quests]") and has(before, "[mutant_loot]") and has(before, "[roaming]"))
			check("file has the EN and RU comment lines", has(before, "Damage multiplier") and has(before, "\208\156\208\189\208\190\208\182\208\184\209\130\208\181\208\187\209\140"))
			local lg = read_all(logpath)
			check("host_cfg.log: the first start CREATED the file", has(lg, "file created with the defaults"), lg and string.sub(lg, 1, 200) or "no log")
			ev("start line: " .. string.sub(coop_host_cfg.last_line or "", 1, 300))
			return L.wait(1)
		end,

		-- 2. phase A: damage multiplier 1.0
		function(c)
			check("phase A: file written", write_cfg(PHASE_A))
			local line = coop_host_cfg.reload()
			check("phase A: start line shows damage.player_damage_mult=1(file)", has(line, "damage.player_damage_mult=1(file)"), string.sub(line or "", 1, 160))
			check("phase A: coop_balance reads 1.0", coop_balance.cfg().player_damage_mult == 1.0, tostring(coop_balance.cfg().player_damage_mult))
			return L.hits_to_kill({ section = "sim_default_bandit_0", power = 0.5518 })
		end,
		function(c, r, err)
			res.a = r
			check("phase A: bandit killed", r ~= nil and r.killed == true, r and ("hits " .. tostring(r.hits)) or tostring(err))
			ev("phase A hits to kill (mult 1.0): " .. tostring(r and r.hits))
			return L.wait(3)
		end,

		-- 3. phase B: damage multiplier 3.0 and the other consumers
		function(c)
			check("phase B: file written", write_cfg(PHASE_B))
			local line = coop_host_cfg.reload()
			check("phase B: start line shows damage.player_damage_mult=3(file)", has(line, "damage.player_damage_mult=3(file)"), string.sub(line or "", 1, 160))
			check("phase B: start line says values came from the file", has(line, "value(s) from the file") and not has(line, ": 0 value(s) from the file"))
			check("phase B: coop_balance reads 3.0", coop_balance.cfg().player_damage_mult == 3.0, tostring(coop_balance.cfg().player_damage_mult))
			check("phase B: coop_balance ammo keeps the db value", coop_balance.cfg().ammo_per_extra_player == 1.0)
			check("phase B: player_scaling max_factor 1.75", player_scaling.cfg().max_factor == 1.75, tostring(player_scaling.cfg().max_factor))
			check("phase B: player_scaling human_extra 0.25", player_scaling.cfg().human_extra_per_player == 0.25)
			check("phase B: player_scaling slot_fraction is not host-editable", math.abs(player_scaling.cfg().slot_fraction - 0.6) < 1e-4, tostring(player_scaling.cfg().slot_fraction))
			local bl = stash_loot.config()
			check("phase B: box loot wood 100 / metal 0 / inventory 50", bl.chance.w == 100 and bl.chance.m == 0 and bl.chance.i == 50,
				tostring(bl.chance.w) .. "/" .. tostring(bl.chance.m) .. "/" .. tostring(bl.chance.i))
			local medkit, vodka = false, nil
			for _, it in ipairs(bl.items) do
				if it[1] == "medkit" then medkit = true end
				if it[1] == "vodka" then vodka = it[2] end
			end
			check("phase B: box loot medkit weight 0 removes it, vodka 77", (not medkit) and vodka == 77, tostring(medkit) .. "/" .. tostring(vodka))
			check("phase B: mutant part chance mutant_dog_part = 1", mutant_loot.chance_for("mutant_dog_part") == 1, tostring(mutant_loot.chance_for("mutant_dog_part")))
			check("phase B: roaming stay_min is read through coop_host_cfg", coop_host_cfg.num("roaming", "stay_min", 240) == 11)
			return L.hits_to_kill({ section = "sim_default_bandit_0", power = 0.5518 })
		end,
		function(c, r, err)
			res.b = r
			check("phase B: bandit killed", r ~= nil and r.killed == true, r and ("hits " .. tostring(r.hits)) or tostring(err))
			ev("phase B hits to kill (mult 3.0): " .. tostring(r and r.hits))
			local a, b = res.a and res.a.hits or 0, r and r.hits or 99
			check("phase B: fewer hits than phase A (multiplier 3.0 vs 1.0)", b < a, "A " .. tostring(a) .. " hits, B " .. tostring(b) .. " hits")
			return L.wait(3)
		end,
		function(c)
			-- the repeat-quest config is loaded by its own 2 s tick after the reload
			local q = coop_repeat_quests.quests
			check("phase B: repeat quests cooldown_min 60", q ~= nil and q[1] ~= nil and q[1].cd == 60, q and q[1] and tostring(q[1].cd) or "quests not loaded")
			return L.wait(1)
		end,

		-- 4. phase C: bad value and missing key, then the file is deleted and written again
		function(c)
			check("phase C: file written", write_cfg(PHASE_C))
			local line = coop_host_cfg.reload()
			check("phase C: bad value is named in the start line", has(line, "bad value 'banana'"), string.sub(line or "", 1, 200))
			check("phase C: bad value gives the db default 1.5", coop_balance.cfg().player_damage_mult == 1.5, tostring(coop_balance.cfg().player_damage_mult))
			check("phase C: the good line next to it still works (max_players 3)", coop_balance.cfg().max_players == 3, tostring(coop_balance.cfg().max_players))
			check("phase C: missing keys give the db default (human_extra 0.5)", player_scaling.cfg().human_extra_per_player == 0.5)
			check("phase C: bad_count >= 1", coop_host_cfg.bad_count() >= 1)
			local removed = pcall(os.remove, coop_host_cfg.path())
			check("phase C: file deleted by the hook", removed and read_all(coop_host_cfg.path()) == nil)
			line = coop_host_cfg.reload()
			local again = read_all(coop_host_cfg.path())
			check("phase C: deleted file is written again with the defaults", again ~= nil and has(again, "player_damage_mult = 1.5") and has(line, "file created with the defaults"))
			check("phase C: defaults are back for every consumer", coop_balance.cfg().player_damage_mult == 1.5 and coop_balance.cfg().max_players == 4
				and stash_loot.config().chance.w == 30)
			L.god(false)
			ev("done")
		end,
	})
end)
