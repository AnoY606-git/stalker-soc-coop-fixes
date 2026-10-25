--@qa_lib
-- Yantar: the second scientist (Semenov), the wounded scientist and the return task of the original SoC (test only, never shipped).
-- ONE listen-host run with one extra client (two players), Cordon start, party-vote travel to Yantar, then the chain is fast-forwarded with the flags
-- the dialogs and the world give. Nothing is rescued, so the professor is dead and Sakharov sends the party with Semenov.
--   path A (default): offer -> Semenov's escort talk -> three measurements -> the wounded scientist at the third site -> his talk -> he goes home
--   path B (-Cfg die=1): the same until the wounded scientist lies there, then he is killed -> YAN_SCIENTIST_DIE, the PDA tip, the return task
--            for every player, Sakharov's branch 5 (prototype anyway), the task closes
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socsem -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 420 -ResultDir <dir>
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner socsemd -Cfg die=1 -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 420 -ResultDir <dir>
--   python tools\stalker_xrmpe\qa_verdict.py <dir>
-- Every process (host and client each check their own player) asserts; the server-only parts (NPC objects, wounded state) are asserted on the host.
-- Lines in qa_events.log:  SOCSEM ...
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("SOCSEM " .. s) end
local DIE = qa.cfg and qa.cfg.die == "1"

local OFFERED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO"
local PREP = "YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO"
local REPORTED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO"
local HELMET = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO"
local SITES = { { 108.5, -8.9, -209.3 }, { 144.2, -8.9, -121.8 }, { 177.9, -4.6, -99.5 } }
local SEM_SPOT = { 36.95, -11.72, -274.93 }            -- bunker spot (SoC yantar_semenov was in the door yan_door_trader_2_1)
local WND_SPOT = { 171.98, -7.69, -99.49 }             -- SoC path yan_scientist_wounded_walk

local function tr(id) return safe(function() return game.translate_string(id) end) end

local function task_info(lo, id)
	local t = lo and safe(function() return lo:get_task(id, true) end)
	if t == nil then return nil end
	return { title = safe(function() return game.translate_string(t:get_title()) end),
		descr = safe(function() return game.translate_string(t:get_description()) end) }
end

local function descr_is(me, id, descr_id)
	local ti = task_info(me, id)
	qa.assert(id .. " description now [" .. descr_id .. "]", ti ~= nil and ti.descr == tr(descr_id) and ti.descr ~= descr_id, ti and tostring(ti.descr) or "no task")
end

local function everyone_got(id)
	if not L.on_server() then return true, "client" end
	local got = safe(function() return coop_soc_yan_semenov.who(id) end) or {}
	local set = {}
	for _, pid in ipairs(got) do set[pid] = true end
	local n, miss = 0, {}
	for pid, a in pairs(db.mp_actors) do
		n = n + 1
		if not set[pid] then miss[#miss + 1] = tostring(pid) end
	end
	return (#miss == 0 and n > 0), "players=" .. n .. " missing=" .. table.concat(miss, ",")
end

local function everyone_holds(section)
	local n, miss = 0, {}
	for _, p in ipairs(L.players()) do
		n = n + 1
		if (L.count_item(p.id, section) or 0) < 1 then miss[#miss + 1] = tostring(p.id) end
	end
	return n > 0 and #miss == 0, "players=" .. n .. " missing=" .. table.concat(miss, ",")
end

local function all_to(pos)
	for _, p in ipairs(L.players()) do safe(function() return L.teleport(p.id, pos) end) end
end

local function dist(o, p)
	local a = o:position()
	return math.sqrt((a.x - p[1]) ^ 2 + (a.y - p[2]) ^ 2 + (a.z - p[3]) ^ 2)
end

-- the online object of a story id (server) or nil
local function npc_of(story)
	local id = safe(function() return get_story_object_id(story) end)
	if id == nil then return nil, nil end
	return safe(function() return level.object_by_id(id) end), id
end

local function active_scheme(id)
	local st = db.storage and db.storage[id]
	return st and st.active_scheme
end

local function cordon_part()
	L.task("socsem_travel", {
		function(c) return L.wait(8) end,
		function(c) return L.travel("yan", { fallback = true, timeout = 170 }) end,
		function(c, ok, why) qa.assert("travel to yan (this VM only continues on failure)", ok == true, tostring(why)) end,
	})
end

local function yantar_part()
	local steps = {
		function(c) return L.wait(12) end,
		function(c)
			local me = L.local_player()
			qa.assert("nothing was rescued: the professor is dead (SoC bar_heli_scene_professor_die)", L.flag_has("YAN_SOC_PROFESSOR_DIE") and coop_soc_yan_semenov.professor_dead())
			qa.assert("Kruglov only says 'no time' (SoC branch 6)", coop_soc_yan_semenov.st_k_other() and not coop_soc_yan_semenov.st_k_meet())
			qa.assert("Semenov starts in the 'no time' state", coop_soc_yan_semenov.st_m_meet())
			if L.on_server() then
				local o, id = npc_of("yan_soc_semenov")
				qa.assert("Semenov exists (story id yan_soc_semenov)", id ~= nil)
				qa.assert("Semenov is online, alive and at the SoC spot (" .. tostring(o and dist(o, SEM_SPOT)) .. " m)", o ~= nil and o:alive() and dist(o, SEM_SPOT) < 6)
				qa.assert("Semenov has an active logic scheme (" .. tostring(id and active_scheme(id)) .. ")", id ~= nil and active_scheme(id) ~= nil)
				qa.assert("no wounded scientist yet", npc_of("yan_semenov_help") == nil)
				local s = safe(function() return L.find_online("yan_soc_semenov") end)
				if s ~= nil then return L.open_talk(s, { shot = "socsem_semenov_before" }) end
			end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with Semenov (no time state): " .. tostring(talking))
				qa.assert("the dialog window opens with Semenov", talking == true)
				L.close_talk()
			end
			local sak = safe(function() return L.find_online("yan_smart_terrain_1_ecolog_saharov") end)
			qa.assert("Sakharov is online", sak ~= nil)
			if sak ~= nil and L.on_server() then return L.open_talk(sak, { shot = "socsem_sakharov_offer" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with Sakharov (offer, Semenov variant): " .. tostring(talking))
				qa.assert("the SoC dialog window opens with Sakharov", talking == true)
				L.close_talk()
			end
			-- phrase 211132 sets both
			L.flag_give(OFFERED); L.flag_give("YAN_FIND_SCIENTIST_SEMENOV_START")
			return L.wait(8)
		end,
		function(c)
			local me = L.local_player()
			descr_is(me, "yan_start_talk_to_the_kruglov_quest_task", "coop_soc_yan_sem_talk_descr")
			qa.assert("Semenov: escort talk state, Kruglov silent", coop_soc_yan_semenov.st_m_talk() and not coop_soc_yan_semenov.st_k_talk())
			local s = safe(function() return L.find_online("yan_soc_semenov") end)
			if s ~= nil and L.on_server() then return L.open_talk(s, { shot = "socsem_semenov_talk" }) end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with Semenov (escort state): " .. tostring(talking))
				qa.assert("the escort dialog window opens with Semenov", talking == true)
				L.close_talk()
			end
			L.flag_give(PREP)                 -- phrase 513
			return L.wait(10)
		end,
		function(c)
			descr_is(L.local_player(), "yan_start_talk_to_the_kruglov_quest_task", "coop_soc_yan_sem_escort_descr")
			if L.on_server() then
				local n = 0
				for _, p in ipairs(L.players()) do n = n + (L.count_item(p.id, "yan_psi_detector") or 0) end
				qa.assert("the server gave the measuring device to the party (" .. n .. ")", n >= 1)
			end
			all_to(SITES[1])
			return L.wait(16)
		end,
		function(c)
			all_to(SITES[2])
			return L.wait(16)
		end,
		function(c)
			all_to(SITES[3])
			return L.wait(48)            -- site 3 is the research stop (a 33 s camera scene of cutscenes_pkg_yantar)
		end,
		function(c)
			local me = L.local_player()
			qa.assert("three measurements done", L.flag_has("YAN_START_TAKE_MEASUREMENTS_3_QUEST_TASK_INFO"))
			qa.assert("the wounded scientist was put at the third site (flag)", L.flag_has("YAN_SOC_SEM_WOUNDED"))
			descr_is(me, "yan_start_talk_to_the_kruglov_quest_task", "coop_soc_yan_sem_escort_descr")
			if L.on_server() then
				local w, wid = npc_of("yan_semenov_help")
				qa.assert("the wounded scientist exists (story id yan_semenov_help)", wid ~= nil)
				qa.assert("he is online and near the SoC wounded_walk spot (" .. tostring(w and dist(w, WND_SPOT)) .. " m)", w ~= nil and dist(w, WND_SPOT) < 5)
				qa.assert("he is wounded (xr_wounded.is_wounded)", w ~= nil and safe(function() return xr_wounded.is_wounded(w) end) == true)
				qa.assert("his talk is enabled and the start dialog is the wounded one", w ~= nil and safe(function() return w:is_talk_enabled() end) == true)
				qa.assert("the bunker Semenov is away", npc_of("yan_soc_semenov") == nil)
				if not DIE then
					local o = safe(function() return L.find_online("yan_soc_semenov_wounded") end)
					if o ~= nil then return L.open_talk(o, { shot = "socsem_wounded_talk" }) end
				end
			end
		end,
		function(c, talking)
			if talking ~= nil then
				ev("talk with the wounded scientist: " .. tostring(talking))
				qa.assert("the SoC wounded dialog opens", talking == true)
				L.close_talk()
			end
			if DIE then return end
			L.flag_give("YAN_SCIENTIST_RETURN_TO_BUNKER")          -- phrase 111
			return L.wait(8)
		end,
		function(c)
			if DIE then return end
			if L.on_server() then
				local w, wid = npc_of("yan_semenov_help")
				qa.assert("after the talk he stands up (no longer wounded)", w ~= nil and safe(function() return xr_wounded.is_wounded(w) end) ~= true)
			end
			return L.wait(26)
		end,
		function(c)
			if DIE then return end
			qa.assert("he went home: the flag is set", L.flag_has("YAN_SOC_SEM_WOUNDED_GONE"))
			if L.on_server() then
				qa.assert("the wounded scientist is gone", npc_of("yan_semenov_help") == nil)
				local o, id = npc_of("yan_soc_semenov")
				qa.assert("the bunker Semenov is back", id ~= nil)
			end
			ev("path A done")
			return L.screenshot("socsem_home")
		end,
	}
	if DIE then
		-- path B continues after the wounded scientist was checked
		local more = {
			function(c)
				if L.on_server() then
					local w = npc_of("yan_semenov_help")
					qa.assert("(death) the wounded scientist is there to be killed", w ~= nil)
					if w ~= nil then L.kill(w) end
				end
				return L.wait(12)
			end,
			function(c)
				local me = L.local_player()
				qa.assert("(death) YAN_SCIENTIST_DIE is set", L.flag_has("YAN_SCIENTIST_DIE"))
				qa.assert("(death) the PDA tip flag and the return task flag are set", L.flag_has("YAN_SOC_SEM_TIP_1") and L.flag_has("YAN_SCIENTIST_RETURN_TASK"))
				local ti = task_info(me, "yan_soc_return_task")
				qa.assert("(death) the return task is in this player's PDA", ti ~= nil)
				if ti then
					ev("TASK yan_soc_return_task title=[" .. tostring(ti.title) .. "] descr=[" .. tostring(ti.descr) .. "]")
					qa.assert("(death) title is [Talk to Sakharov]", ti.title == tr("coop_soc_yan_sem_return_name") and ti.title ~= "coop_soc_yan_sem_return_name")
					qa.assert("(death) description is the SoC briefing", ti.descr == tr("coop_soc_yan_sem_return_descr"))
				end
				local ok, info = everyone_got("yan_soc_return_task")
				qa.assert("(death) the server tick gave the return task to every player (" .. tostring(info) .. ")", ok)
				qa.assert("(death) Sakharov shows branch 5", coop_soc_yan_semenov.st_s_semdead() and not coop_soc_yan_semenov.st_s_results())
				local sak = safe(function() return L.find_online("yan_smart_terrain_1_ecolog_saharov") end)
				if sak ~= nil and L.on_server() then return L.open_talk(sak, { shot = "socsem_sakharov_died" }) end
			end,
			function(c, talking)
				if talking ~= nil then
					ev("talk with Sakharov (Semenov died): " .. tostring(talking))
					qa.assert("(death) the branch 5 dialog opens", talking == true)
					L.close_talk()
				end
				L.flag_give(REPORTED); L.flag_give(HELMET)             -- phrase 51 sets both
				return L.wait(12)
			end,
			function(c)
				qa.assert("(death) Sakharov's states moved on", not coop_soc_yan_semenov.st_s_semdead())
				if L.on_server() then
					local ok, info = everyone_holds("dev_psi_protection_helmet")
					qa.assert("(death) the helmet is in every player's bag (" .. tostring(info) .. ")", ok)
				end
				ev("path B done")
				return L.screenshot("socsem_died_done")
			end,
		}
		-- in path B the path A steps after the wounded talk return at once (guard), then these run
		for _, f in ipairs(more) do steps[#steps + 1] = f end
	end
	L.task("socsem_yantar", steps)
end

qa.once("socsem_run", function(t, lo)
	local lvl = L.level_name()
	ev("hook runs on " .. tostring(lvl) .. " die=" .. tostring(DIE))
	if lvl == "coop_l01_escape" then
		cordon_part()
	elseif lvl == "coop_l08_yantar" then
		L.travel_arrived()
		yantar_part()
	end
end)
