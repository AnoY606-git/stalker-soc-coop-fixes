--@qa_lib
-------------------------------------------------------------------------------------------------------
-- TEST ONLY (never shipped). Hook for tools/stalker_xrmpe/run_coop.ps1 -Mode listen -Clients 1 -Map coop_l01_escape (Cordon):
--   -Hooks <this file> -SoakSeconds 400 ; verdict: python tools\stalker_xrmpe\qa_verdict.py <ResultDir> --prefix CA --require 10
-- NOT RUN YET (written offline). It uses the test override death_manager.corpse_art_test (see death_manager.script of the patch):
--   A  chance x200 (= 100%), all_levels: 6 NPCs (3 stalker, 3 bandit) are spawned and killed; every corpse must hold all 12 artifacts of the
--      0.5% tier ( *_soc ids ) as SERVER children of the corpse, exactly once each; stats: deaths 6, rolls 72, drops 72.
--   B  chance x20 (= 10% each): 40 NPCs; stats rolls = 12 x 40, drops/rolls in 0.06 .. 0.14, and the artifacts found on the corpses = stats.drops.
--   C  normal chance (x1): on Cordon (a level SoC gives no artifacts) 30 NPCs -> rolls 0, drops 0 (level rule); then all_levels = true with the
--      normal chance: 100 NPCs -> rolls 1200, drops 0 .. 25 (expected 6), artifacts on the corpses = stats.drops (rate check).
-- Kill = L.kill (a lethal hit with the first player as draftsman), so the normal motivator_binder:death_callback -> create_release_item path runs.
-------------------------------------------------------------------------------------------------------
local L = qa_lib

local TIER = { "af_night_star_soc", "af_gold_fish_soc", "af_soul_soc", "af_electra_moonlight_soc", "af_rusty_sea-urchin_soc", "af_ameba_mica_soc",
	"af_cristall_soc", "af_dummy_glassbeads_soc", "af_dummy_pellicle_soc", "af_dummy_battery_soc", "af_dummy_spring_soc", "af_fuzz_kolobok_soc" }
local IS_TIER = {}
for _, a in ipairs(TIER) do IS_TIER[a] = true end

local function ev(s) qa.event("CA " .. tostring(s)) end

local function set_mode(mult, all_levels)
	if mult == nil then
		death_manager.corpse_art_test = nil
	else
		death_manager.corpse_art_test = { chance_mult = mult, all_levels = all_levels }
	end
	death_manager.init_drop_settings()   -- the tables are rebuilt here (the game does it when an actor spawns)
	death_manager.corpse_art_stats.deaths = 0
	death_manager.corpse_art_stats.rolls = 0
	death_manager.corpse_art_stats.drops = 0
end

-- { [corpse_id] = { [section] = n } } over the server objects whose parent is one of `ids`
local function artifacts_on(ids)
	local want, res = {}, {}
	for _, id in ipairs(ids) do want[id] = true res[id] = {} end
	local sim = alife()
	for id = 0, 65534 do
		local se = sim:object(id)
		if se ~= nil and want[se.parent_id] then
			local sec = se:section_name()
			if IS_TIER[sec] then res[se.parent_id][sec] = (res[se.parent_id][sec] or 0) + 1 end
		end
	end
	return res
end

local function total(res)
	local n = 0
	for _, t in pairs(res) do for _, c in pairs(t) do n = n + c end end
	return n
end

-- spawn n NPCs (half stalker, half bandit), wait for them to come online, kill them, wait for the death handling; returns the id list
local function batch_steps(n, ids)
	return {
		function(c)
			for i = 1, n do
				local sec = (i % 2 == 0) and "sim_default_bandit_0" or "sim_default_stalker_0"
				local se, id = L.spawn_npc(sec, { offset = { 4 + (i % 5), 0, (i % 3) } })
				if se ~= nil then ids[#ids + 1] = id else ev("spawn failed " .. tostring(id)) end
			end
			return L.wait(6)
		end,
		function(c)
			for _, id in ipairs(ids) do
				local o = L.online(id)
				if o ~= nil then L.kill(o) end
			end
			return L.wait(6)
		end,
	}
end

local function concat(...)
	local r = {}
	for _, t in ipairs({ ... }) do for _, f in ipairs(t) do r[#r + 1] = f end end
	return r
end

qa.once("corpse_artifacts_test", function()
	if not L.on_server() then return end
	local idsA, idsB, idsC1, idsC2 = {}, {}, {}, {}
	local steps = { function(c) return L.wait(10) end, function(c) L.god(true) set_mode(200, true) end }

	-- A
	for _, f in ipairs(batch_steps(6, idsA)) do steps[#steps + 1] = f end
	steps[#steps + 1] = function(c)
		local st = death_manager.corpse_art_stats
		local res = artifacts_on(idsA)
		local full = 0
		for id, t in pairs(res) do
			local distinct, dup = 0, false
			for _, a in ipairs(TIER) do
				if (t[a] or 0) >= 1 then distinct = distinct + 1 end
				if (t[a] or 0) > 1 then dup = true end
			end
			if distinct == 12 and not dup then full = full + 1 end
			ev("A corpse " .. tostring(id) .. " distinct " .. distinct .. " dup " .. tostring(dup))
		end
		qa.assert("CA A: 6 corpses spawned", #idsA == 6, #idsA)
		qa.assert("CA A: every corpse holds all 12 tier artifacts once", full == #idsA, full .. " of " .. #idsA)
		qa.assert("CA A: stats deaths/rolls/drops", st.deaths == #idsA and st.rolls == 12 * #idsA and st.drops == 12 * #idsA,
			st.deaths .. "/" .. st.rolls .. "/" .. st.drops)
	end

	-- B
	steps[#steps + 1] = function(c) set_mode(20, true) end
	for _, f in ipairs(batch_steps(40, idsB)) do steps[#steps + 1] = f end
	steps[#steps + 1] = function(c)
		local st = death_manager.corpse_art_stats
		local found = total(artifacts_on(idsB))
		local rate = (st.rolls > 0) and (st.drops / st.rolls) or -1
		ev(string.format("B deaths %d rolls %d drops %d found %d rate %.4f (expected 0.10)", st.deaths, st.rolls, st.drops, found, rate))
		qa.assert("CA B: rolls = 12 per corpse", st.rolls == 12 * #idsB and st.deaths == #idsB, st.deaths .. "/" .. st.rolls)
		qa.assert("CA B: drop rate plausible (0.10)", rate > 0.06 and rate < 0.14, rate)
		qa.assert("CA B: artifacts on the corpses = stats.drops", found == st.drops, found .. " vs " .. st.drops)
	end

	-- C1: normal chance, Cordon is not an artifact level in SoC
	steps[#steps + 1] = function(c) set_mode(nil) end
	for _, f in ipairs(batch_steps(30, idsC1)) do steps[#steps + 1] = f end
	steps[#steps + 1] = function(c)
		local st = death_manager.corpse_art_stats
		qa.assert("CA C1: Cordon, normal chance: no artifact roll at all (level rule)", st.rolls == 0 and st.drops == 0 and total(artifacts_on(idsC1)) == 0,
			st.deaths .. "/" .. st.rolls .. "/" .. st.drops)
	end

	-- C2: normal chance everywhere (host setting all_levels), the real rate
	steps[#steps + 1] = function(c) set_mode(1, true) end
	for k = 1, 5 do
		local part = {}
		for _, f in ipairs(batch_steps(20, part)) do steps[#steps + 1] = f end
		steps[#steps + 1] = function(c) for _, id in ipairs(part) do idsC2[#idsC2 + 1] = id end end
	end
	steps[#steps + 1] = function(c)
		local st = death_manager.corpse_art_stats
		local found = total(artifacts_on(idsC2))
		ev(string.format("C2 deaths %d rolls %d drops %d found %d (expected 6)", st.deaths, st.rolls, st.drops, found))
		qa.assert("CA C2: 100 corpses, 12 rolls each", st.deaths == 100 and st.rolls == 1200, st.deaths .. "/" .. st.rolls)
		qa.assert("CA C2: normal rate plausible (0..25 drops, expected 6)", st.drops >= 0 and st.drops <= 25, st.drops)
		qa.assert("CA C2: artifacts on the corpses = stats.drops", found == st.drops, found .. " vs " .. st.drops)
		set_mode(nil)
		ev("done")
	end

	L.task("corpse_artifacts_test", steps)
end)
