"""Offline check (no game) of coop_soc_yan_semenov.script: the professor-is-dead variant, the two Semenov NPCs (bunker, wounded) and their hand-over,
the death of the wounded scientist (flags, PDA tips, the return task for every player), the dialog states, the voice lines.
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL scripts (coop_soc_yan.script of patch soc_yan_x16_quests and coop_soc_yan_semenov.script) in a Lua 5.1 VM with a small engine mock
(story flags, players, alife():create / release / object, story ids, task hand-out)."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
PATCHES = os.path.dirname(PATCH)
fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local yan_path, sem_path, patch_root = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}                 -- "task|player" -> count
E.__calls = {}
E.__client = false
E.__played = {}
E.__voice_lang = "eng"
E.__created = {}               -- list of "section|x,y,z"
E.__fail_create = false
E.__story = {}                 -- story id -> entity id
E.__ents = {}                  -- entity id -> { id, section, alive, pos }
E.__released = {}
E.__me = nil
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return not E.__client end
function E.OnClient() return E.__client end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
E.__level = "coop_l08_yantar"
local nextid = 100
E.__vpos = nil
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end,
	vertex_id = function(pos) E.__vpos = pos; return 77 end,
	vertex_position = function(lv) return E.__vpos end,
	object_by_id = function(id)
		local e = E.__ents[id]
		if e and e.online then return { alive = function() return e.alive end } end
		return nil end }
E.get_story_object_id = function(s) return E.__story[s] end
E.unregister_story_id = function(s) E.__story[s] = nil end
E.add_story_object = function(id, s) E.__story[s] = id end
local STORY = { yan_soc_semenov = "yan_soc_semenov", yan_soc_semenov_wounded = "yan_semenov_help" }
E.alife = function() return {
	create = function(self, section, pos, lv, gv)
		if E.__fail_create then error("create failed") end
		nextid = nextid + 1
		local se = { id = nextid, section = section, pos = pos, lv = lv, gv = gv, alive = true, online = true }
		E.__ents[se.id] = se
		if STORY[section] then E.__story[STORY[section]] = se.id end
		E.__created[#E.__created + 1] = section .. "|" .. string.format("%.2f,%.2f,%.2f", pos.x, pos.y, pos.z)
		return setmetatable({ id = se.id, section_name = function() return section end,
			alive = function() return se.alive end }, { __index = se })
	end,
	object = function(self, id)
		local e = E.__ents[id]
		if e == nil then return nil end
		return { id = e.id, section_name = function() return e.section end, alive = function() return e.alive end }
	end,
	release = function(self, se, flag)
		local e = E.__ents[se.id]
		E.__released[#E.__released + 1] = e and e.section or "?"
		if e then
			E.__ents[se.id] = nil
			for k, v in pairs(E.__story) do if v == se.id then E.__story[k] = nil end end
		end
	end } end
E.__squad = nil                -- story id of the squad -> member entity id (the mod's squad of the Yantar Kruglov)
E.__squad_removed = 0
E.get_story_squad = function(s)
	if E.__squad and E.__squad.story == s then return E.__squad end
	return nil
end
E.sim_board = { get_sim_board = function() return { remove_squad = function(self, sq)
	E.__squad_removed = E.__squad_removed + 1
	local e = E.__ents[sq.member]
	if e then
		E.__released[#E.__released + 1] = e.section
		E.__ents[sq.member] = nil
		for k, v in pairs(E.__story) do if v == sq.member then E.__story[k] = nil end end
	end
	E.__squad = nil
end } end }
E.db = { mp_actors = {}, spawned_vertex_by_id = {}, storage = {} }
E.__logic = {}
E.ini_file = function(f) return { file = f } end
E.modules = { stype_stalker = 0 }
E.xr_logic = {
	configure_schemes = function(npc, ini, f, stype, sect, scheme) E.__logic[#E.__logic + 1] = "configure " .. f; return ini end,
	determine_section_to_activate = function(npc, ini, sect, actor) return "remark@x" end,
	activate_by_section = function(npc, ini, sect, a, b) E.__logic[#E.__logic + 1] = "activate " .. sect end }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z), __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec) if self.__items[sec] then return true end return nil end
	function o:level_vertex_id() return 1 end
	function o:game_vertex_id() return 2 end
	E.db.mp_actors[id] = o
	return o
end
E.coop_soc_opening = { voice_lang = function() return E.__voice_lang end }
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
local function mk_sound(p)
	local s = { path = p }
	function s:playing() return false end
	function s:stop() end
	function s:play(o, d, f) E.__played[#E.__played + 1] = p end
	return s
end
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(t, p) return mk_sound(p) end })
function E.getLocalActor() return E.__me end
E.getFS = function() return { exist = function(self, root, name)
	for _, r in ipairs({ patch_root, patch_root .. "/../soc_ru_voices", patch_root .. "/../soc_yan_x16_quests" }) do
		local f = io.open(r .. "/gamedata/sounds/" .. string.gsub(name, "\\", "/"), "rb")
		if f then f:close() return true end
	end
	return false end } end
E.game = { translate_string = function(s) return "Windowed" end }

local function load(path, name)
	local f = io.open(path, "r")
	local src = f:read("*a")
	f:close()
	local env = setmetatable({}, { __index = E })
	local fn = assert(loadstring(src, name))
	setfenv(fn, env)
	E[name] = env           -- the other module is looked up by name while the first runs top-level code
	fn()
	return env
end
load(yan_path, "coop_soc_yan")
load(sem_path, "coop_soc_yan_semenov")
return E
'''

OFFERED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO"
PREP = "YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO"
REPORTED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO"
HELMET = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO"
RESCUE = "ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_INFO"
MEAS = ["YAN_START_TAKE_MEASUREMENTS_%d_QUEST_TASK_INFO" % i for i in (1, 2, 3)]
SEM_START = "YAN_FIND_SCIENTIST_SEMENOV_START"
YAN, X16 = "coop_l08_yantar", "coop_l08_x16"
SEM, WND = "yan_soc_semenov", "yan_soc_semenov_wounded"
KRU = "yan_smart_terrain_1_ecolog_kruglov"
KGONE = "YAN_SOC_KRUGLOV_GONE"


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    E = lua.execute(PRELUDE, os.path.join(PATCHES, "soc_yan_x16_quests", "gamedata", "scripts", "coop_soc_yan.script").replace("\\", "/"),
                    os.path.join(PATCH, "gamedata", "scripts", "coop_soc_yan_semenov.script").replace("\\", "/"), PATCH.replace("\\", "/"))
    S = E["coop_soc_yan_semenov"]
    Y = E["coop_soc_yan"]

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(n):
        E["story_flags"]["give_flag"](n)

    def reset(level=YAN):
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__created"] = lua.table_from({})
        E["__released"] = lua.table_from({})
        E["__story"] = lua.table_from({})
        E["__ents"] = lua.table_from({})
        E["__logic"] = lua.table_from({})
        E["db"]["storage"] = lua.table_from({})
        E["__fail_create"] = False
        E["__squad"] = None
        E["__squad_removed"] = 0
        E["__level"] = level
        E["__time"] = 0
        E["__client"] = False
        E["__voice_lang"] = "eng"
        E["__me"] = None
        S["reset_given"]()

    def player(pid, x=0.0, y=0.0, z=0.0):
        return E["__player"](pid, "p%d" % pid, x, y, z)

    def step(dt=1000):
        E["__time"] = E["__time"] + dt
        return S["step"](E["__time"])

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def created():
        return sorted(str(v) for v in E["__created"].values())

    def n_created(prefix):
        return sum(1 for c in created() if c.startswith(prefix + "|"))

    def released():
        return [str(v) for v in E["__released"].values()]

    def ent(section):
        for k, v in E["__ents"].items():
            if v["section"] == section:
                return v
        return None

    def story(sid):
        v = E["__story"][sid]
        return int(v) if v else None

    def add_kru(squad=True):
        E["__ents"][500] = lua.table_from({"id": 500, "section": KRU, "alive": True, "online": True})
        E["__story"][KRU] = 500
        if squad:
            E["__squad"] = lua.table_from({"story": KRU + "_squad", "member": 500})

    # ---------------------------------------------------------------- the professor is dead (not rescued): the Semenov variant
    reset()
    player(1, 30, -11, -272)
    add_kru()
    check("not rescued: the professor is dead", S["professor_dead"]())
    step()
    check("on Yantar without the rescue: PROFESSOR_DIE is set (SoC yan_ecolog_spam_space_restrictor)", flag("YAN_SOC_PROFESSOR_DIE"))
    check("Semenov is created ONCE at the SoC spot next to the bunker", n_created(SEM) == 1 and created()[0].startswith(SEM + "|36.95,-11.72,-274.93"), created())
    check("his story id is registered (a loaded game finds him again)", story("yan_soc_semenov") is not None)
    step(); step(); step()
    check("no second Semenov on later ticks", n_created(SEM) == 1, created())
    check("Semenov variant: the mod's bunker Kruglov is taken out once (squad release), Semenov stays", ent(KRU) is None and ent(SEM) is not None
          and flag(KGONE) and int(E["__squad_removed"]) == 1 and released() == [KRU], (released(), E["__squad_removed"]))

    # no Kruglov squad: the entity is released directly; no Kruglov at all: only the flag; the order: Semenov first
    reset(); player(1, 30, -11, -272); add_kru(False)
    step()
    check("Semenov is created in the first tick, Kruglov is not touched in the same tick (no same-frame release)", ent(SEM) is not None and ent(KRU) is not None and not flag(KGONE))
    step()
    check("no squad: Kruglov is released directly, once", ent(KRU) is None and released() == [KRU] and flag(KGONE), released())
    for i in range(5):
        step()
    check("... and never again", released() == [KRU])
    reset(); player(1, 30, -11, -272)
    step(); step()
    check("no Kruglov yet: it keeps looking for 45 s (he may not exist right after the level load), no flag yet", not flag(KGONE) and released() == [])
    for i in range(5):
        step(10000)
    check("no Kruglov in the save: after 45 s only the flag is set, nothing released", flag(KGONE) and released() == [])
    reset(); player(1, 30, -11, -272); add_kru(); give(KGONE)
    step(); step()
    check("flag set (Kruglov of another entity id would stay): no second release attempt", ent(KRU) is not None and released() == [])
    reset(); player(1, 30, -11, -272); add_kru()
    E["__fail_create"] = True
    step(); step(); step()
    check("no Semenov yet (create fails): Kruglov stays, the bunker is never empty", ent(KRU) is not None and not flag(KGONE))
    E["__fail_create"] = False
    reset(X16); player(1, 0, 0, 0); add_kru()
    for i in range(3):
        step()
    check("other level: Kruglov untouched", ent(KRU) is not None and not flag(KGONE))
    reset(); player(1, 30, -11, -272); add_kru()
    give(OFFERED); give(SEM_START); give(PREP)
    for m in MEAS:
        give(m)
    step(); step(); step()
    check("save that already had both and is mid-trip (wounded one out, bunker Semenov gone): Kruglov taken out after Semenov was first created", ent(KRU) is None or flag(KGONE))
    reset(); player(1, 30, -11, -272); add_kru()
    give(SEM_START); give("YAN_SCIENTIST_DIE"); give(OFFERED)
    step(); step()
    check("Semenov dead (variant) and the bunker empty of him: Kruglov is still removed (SoC: only the scientist who died was there)", ent(KRU) is None and flag(KGONE))
    reset(); player(1, 30, -11, -272)
    check("Sakharov: the Kruglov offer is hidden, the Semenov offer shows", not S["st_prof_alive"]() and S["st_prof_die"]())
    check("Kruglov: every state yields, only 'no time' (SoC branch 6)", not S["st_k_meet"]() and not S["st_k_talk"]() and not S["st_k_busy"]() and not S["st_k_after"]()
          and not S["st_k_meet_r"]() and S["st_k_other"]())
    check("Semenov before the offer: 'no time'", S["st_m_meet"]() and not S["st_m_talk"]() and not S["st_m_busy"]() and not S["st_m_after"]())

    # ---------------------------------------------------------------- rescued: the Kruglov variant is untouched
    reset()
    player(1, 30, -11, -272)
    give(RESCUE)
    add_kru()
    step()
    check("rescued: no PROFESSOR_DIE, the professor lives", not flag("YAN_SOC_PROFESSOR_DIE") and not S["professor_dead"]())
    check("rescued: Kruglov states are the stock ones", S["st_k_meet_r"]() == Y["st_k_meet_r"]() and S["st_k_meet"]() == Y["st_k_meet"]() and not S["st_k_other"]()
          and S["st_prof_alive"]() and not S["st_prof_die"]())
    check("rescued: exactly one scientist, Kruglov: no Semenov, Kruglov stays (SoC)", n_created(SEM) == 0 and ent(KRU) is not None and released() == [] and not flag(KGONE))
    give(OFFERED)
    check("rescued + offered: Kruglov gives the escort talk", S["st_k_talk"]() and Y["st_k_talk"]())
    for m in MEAS:
        give(m)
    give(PREP)
    for i in range(30):
        step()
    check("rescued: no wounded scientist (Kruglov variant has none)", n_created(WND) == 0 and not flag("YAN_SOC_SEM_WOUNDED"), created())
    check("rescued: after the whole chain Kruglov is still the only scientist", ent(KRU) is not None and n_created(SEM) == 0 and released() == [], (created(), released()))
    # a save of an older version that already has Semenov in the Kruglov variant: he is removed once
    reset(); player(1, 30, -11, -272); give(RESCUE); add_kru()
    al = E["alife"]()
    vec = E["vector"]()
    vec["set"](vec, 36.95, -11.72, -274.93)
    al["create"](al, SEM, vec, 77, 1)
    step(); step()
    check("rescued, old save with Semenov: Semenov released, Kruglov kept", SEM in released() and ent(SEM) is None and ent(KRU) is not None, released())
    check("PROFESSOR_DIE is not set later either", not flag("YAN_SOC_PROFESSOR_DIE"))

    # ---------------------------------------------------------------- the Semenov variant: offer, talk, three measurements, wounded
    reset()
    p1, p2 = player(1, 30, -11, -272), player(2, 33, -11, -272)
    step()
    give(OFFERED)
    give(SEM_START)                                    # the dialog (SoC 211132) sets both
    check("offered (Semenov): Semenov's escort talk, Kruglov silent", S["st_m_talk"]() and not S["st_m_meet"]() and not S["st_k_talk"]() and S["st_k_other"]())
    give(PREP)                                         # Semenov's dialog (SoC 513)
    check("agreed: Semenov busy", S["st_m_busy"]() and not S["st_m_talk"]())
    for i in range(5):
        step()
    check("before the measurements are done there is no wounded scientist", n_created(WND) == 0)
    give(MEAS[0]); give(MEAS[1])
    step()
    check("two of three measurements: still no wounded scientist", n_created(WND) == 0)
    give(MEAS[2])
    step()
    check("three measurements: the wounded scientist is created at the SoC spot (wounded_walk)", n_created(WND) == 1
          and any(c.startswith(WND + "|171.98,-7.69,-99.49") for c in created()), created())
    check("his story id is the one of the SoC task markers (yan_semenov_help)", story("yan_semenov_help") is not None)
    check("the bunker Semenov is gone (he is away with the player)", SEM in released() and story("yan_soc_semenov") is None, released())
    check("flag WOUNDED set", flag("YAN_SOC_SEM_WOUNDED"))
    for i in range(10):
        step()
    check("nothing is created twice while he lies there", n_created(WND) == 1 and n_created(SEM) == 1, created())
    check("the wounded states: first talk", S["st_w_first"]() and not S["st_w_done"]() and not S["st_w_after"]())
    give("YAN_SCIENTIST_RETURN_TO_BUNKER")             # the wounded dialog (SoC 111)
    check("after the talk: 'Done! Pack the camera'", S["st_w_done"]() and not S["st_w_first"]())
    for i in range(15):
        step()
    check("he stays 20 s after the talk", ent(WND) is not None and not flag("YAN_SOC_SEM_WOUNDED_GONE"))
    for i in range(10):
        step()
    check("then he goes home: removed, the bunker Semenov is back", ent(WND) is None and flag("YAN_SOC_SEM_WOUNDED_GONE") and WND in released()
          and ent(SEM) is not None and n_created(SEM) == 2, (created(), released()))
    for i in range(5):
        step()
    check("no soft-lock: the wounded one never comes back after he went home", n_created(WND) == 1 and n_created(SEM) == 2)
    check("no return task without his death", given("yan_soc_return_task", 1) == 0 and given("yan_soc_return_task", 2) == 0)
    give(REPORTED)
    check("results delivered: Semenov 'how's life'", S["st_m_after"]() and not S["st_m_busy"]())

    # ---------------------------------------------------------------- results delivered while he still lies there
    reset()
    player(1, 30, -11, -272)
    step(); give(OFFERED); give(SEM_START); give(PREP)
    for m in MEAS:
        give(m)
    step(); step()
    check("(2nd run) the wounded one lies at the site", ent(WND) is not None)
    give(REPORTED)
    for i in range(8):
        step()
    check("results delivered without talking to him: he goes home, the bunker Semenov is back", ent(WND) is None and ent(SEM) is not None and flag("YAN_SOC_SEM_WOUNDED_GONE"))
    check("wounded dialog: after the results 'how's life'", S["st_w_after"]())

    # ---------------------------------------------------------------- he dies: PDA tip, return task for EVERY player, prototype branch
    reset()
    p1, p2 = player(1, 170, -7, -99), player(2, 172, -7, -99)
    step(); give(OFFERED); give(SEM_START); give(PREP)
    for m in MEAS:
        give(m)
    step(); step()
    w = ent(WND)
    check("(death run) the wounded one exists", w is not None)
    w["alive"] = False
    step()
    check("his death sets YAN_SCIENTIST_DIE (SoC death@scientist)", flag("YAN_SCIENTIST_DIE"))
    check("no return task at the moment of death (SoC: 4 s)", not flag("YAN_SCIENTIST_RETURN_TASK") and given("yan_soc_return_task", 1) == 0)
    check("Sakharov: the Semenov-died branch shows, the results branch yields", S["st_s_semdead"]() and not S["st_s_results"]() and Y["st_s_results"]())
    step(2000)
    check("2 s after: still no task", not flag("YAN_SCIENTIST_RETURN_TASK"))
    step(3000)
    check("4 s after: the PDA tip 1 and the flag of the return task (SoC yan_scientist_return_task)", flag("YAN_SOC_SEM_TIP_1") and flag("YAN_SCIENTIST_RETURN_TASK") and not flag("YAN_SOC_SEM_TIP_2"))
    check("the return task goes to BOTH players", given("yan_soc_return_task", 1) == 1 and given("yan_soc_return_task", 2) == 1, E["__given"])
    p3 = player(3, 170, -7, -99)
    step()
    check("a late joiner gets it too", given("yan_soc_return_task", 3) == 1)
    step(); step()
    check("once per player", given("yan_soc_return_task", 1) == 1 and given("yan_soc_return_task", 3) == 1)
    check("his corpse is not replaced and the bunker Semenov does not come back", n_created(WND) == 1 and n_created(SEM) == 1, created())
    check("who() reports the three players", sorted(int(x) for x in S["who"]("yan_soc_return_task").values()) == [1, 2, 3])
    give(REPORTED); give(HELMET)                       # dialog branch 5 (SoC 51) sets both
    check("after the prototype: no semdead state", not S["st_s_semdead"]())
    p4 = player(4, 170, -7, -99)
    step(); step()
    check("the return task is closed once the lab job started (no new hand-out)", given("yan_soc_return_task", 4) == 0)

    # ---------------------------------------------------------------- he dies after the talk (SoC sr_idle@2): tip 2 only, no return task
    reset()
    player(1, 170, -7, -99)
    step(); give(OFFERED); give(SEM_START); give(PREP)
    for m in MEAS:
        give(m)
    step(); step()
    give("YAN_SCIENTIST_RETURN_TO_BUNKER")
    ent(WND)["alive"] = False
    step(); step(5000)
    check("died after the talk: tip 2, no return task", flag("YAN_SOC_SEM_TIP_2") and not flag("YAN_SOC_SEM_TIP_1") and not flag("YAN_SCIENTIST_RETURN_TASK")
          and given("yan_soc_return_task", 1) == 0)

    # ---------------------------------------------------------------- his logic sets the flag too: the tick does not need to see the body
    reset()
    player(1, 170, -7, -99)
    step(); give(OFFERED); give(SEM_START); give(PREP)
    for m in MEAS:
        give(m)
    step(); step()
    give("YAN_SCIENTIST_DIE")                           # death@yan_soc_semenov (logic file)
    step(); step(5000)
    check("flag from his logic: the return task comes the same way", flag("YAN_SCIENTIST_RETURN_TASK") and given("yan_soc_return_task", 1) == 1)

    # ---------------------------------------------------------------- the bunker Semenov dies (review fix): no waiting for a corpse
    reset()
    player(1, 30, -11, -272)
    step()
    ent(SEM)["alive"] = False
    step(); step(6000)
    check("bunker Semenov dead BEFORE the offer: removed and a new one is created", n_created(SEM) == 2 and SEM in released() and not flag("YAN_SCIENTIST_DIE"), (created(), released()))
    ent(SEM)["alive"] = False
    give(OFFERED); give(SEM_START)
    step(); step()
    check("bunker Semenov dead AFTER the offer: YAN_SCIENTIST_DIE, so Sakharov's branch 5 gives the prototype (no soft-lock)",
          flag("YAN_SCIENTIST_DIE") and S["st_s_semdead"]())
    step(5000)
    check("... with the PDA tip and the return task", flag("YAN_SCIENTIST_RETURN_TASK") and given("yan_soc_return_task", 1) == 1)
    give(REPORTED); give(HELMET)
    step(); step()
    check("after the prototype nothing more happens", n_created(SEM) == 2 and not S["st_s_semdead"]())

    # ---------------------------------------------------------------- not on Yantar: nothing happens
    reset(X16)
    player(1, 0, 0, 0)
    for i in range(5):
        step()
    check("on the lab level: nothing is created, no flag", len(created()) == 0 and not flag("YAN_SOC_PROFESSOR_DIE"))
    reset("coop_l01_escape")
    player(1, 0, 0, 0)
    step()
    check("on Cordon: nothing is created", len(created()) == 0)

    # ---------------------------------------------------------------- no player yet, create fails and retries
    reset()
    step()
    check("no player: nothing is created", len(created()) == 0)
    player(1, 30, -11, -272)
    E["__fail_create"] = True
    step(); step(); step()
    check("a failing create does not throw and does not create", len(created()) == 0)
    E["__fail_create"] = False
    step(6000)
    check("the next try after the cooldown works (once)", n_created(SEM) == 1, created())

    # ---------------------------------------------------------------- the engine did not start the logic: the script does (two idle ticks)
    reset()
    player(1, 30, -11, -272)
    step()
    sid = int(story("yan_soc_semenov"))
    E["db"]["storage"][sid] = lua.table_from({"object": lua.table_from({}), "active_scheme": None})
    step()
    check("one idle tick: wait", len(E["__logic"]) == 0)
    step()
    lg = [str(v) for v in E["__logic"].values()]
    check("two idle ticks: the logic file of Semenov is started by script", lg == ["configure scripts\coop_l08_yantar\yan_soc_semenov.ltx", "activate remark@x"], lg)
    E["db"]["storage"][sid]["active_scheme"] = "remark"
    E["__logic"] = lua.table_from({})
    step(); step(); step()
    check("an NPC with an active scheme is left alone", len(E["__logic"]) == 0)

    # ---------------------------------------------------------------- dead player is not given tasks
    reset()
    p1, p2 = player(1, 30, -11, -272), player(2, 30, -11, -272)
    step(); give(OFFERED); give(SEM_START); give(PREP)
    for m in MEAS:
        give(m)
    step(); step()
    ent(WND)["alive"] = False
    p2["__alive"] = False
    step(); step(5000)
    check("a dead player is skipped (the respawned one gets it later)", given("yan_soc_return_task", 1) == 1 and given("yan_soc_return_task", 2) == 0)
    p2["__alive"] = True
    step()
    check("respawned player gets the open task", given("yan_soc_return_task", 2) == 1)

    # ---------------------------------------------------------------- voice and PDA archive
    reset()
    p1 = player(1, 30, -11, -272)
    p2 = player(2, 31, -11, -272)
    E["__client"] = True
    E["__me"] = p1
    S["say_s51"](p2, p1)                # Sakharov (npc) speaks to the local player
    check("English voice of the Sakharov line 51 (Semenov died)", str(S["played"]) == "characters_voice\\dialogs\\eng\\yantar_general_ucheniy_talk_start_51", S["played"])
    E["__time"] = E["__time"] + 5000
    E["__voice_lang"] = "rus"
    S["say_s5111"](p2, p1)
    check("Russian voice with voice_language rus", str(S["played"]) == "characters_voice\\dialogs\\yantar_general_ucheniy_talk_start_5111", S["played"])
    S["played"] = ""
    E["__time"] = E["__time"] + 5000
    S["say_s511"](p2, p1)
    check("a line without a recording is silent", str(S["played"]) == "")
    E["__time"] = E["__time"] + 5000
    S["say_m514"](p2, p1)
    check("Semenov 514 plays the recording of the same words (Kruglov 111111), Russian", str(S["played"]) == "characters_voice\\dialogs\\yantar_help_scientist_111111", S["played"])
    S["played"] = ""
    E["__time"] = E["__time"] + 5000
    E["__voice_lang"] = "eng"
    S["say_s51"](E["__player"](9, "other", 0, 0, 0), E["__player"](8, "other2", 0, 0, 0))
    check("a talk between other players does not play on this machine", str(S["played"]) == "", S["played"])
    E["__client"] = False
    log = "\n".join(str(v) for v in E["__log"].values())
    check("the PDA archive line is emitted for the phrase", "EMIT coop_soc_yan_sem_s_51" in log)
    for fn in ("say_m513", "say_w11", "say_w111"):
        S[fn](p2, p1)
    speakers = E["coop_pda_phrases"]["phrase_speaker"]
    check("speaker per phrase: NPC and actor lines", speakers["coop_soc_yan_sem_s_51"] == "npc" and speakers["coop_soc_yan_sem_s_511"] == "actor"
          and speakers["coop_soc_yan_sem_m_514"] == "npc" and speakers["coop_soc_yan_sem_m_513"] == "actor" and speakers["coop_soc_yan_sem_w_11"] == "npc"
          and speakers["coop_soc_yan_sem_w_111"] == "actor", dict(speakers.items()))

    # every voice file the tables name exists in a patch
    S_voice = [str(v) for v in S["VOICE_S"].values()]
    missing = []
    for i in S_voice:
        for rel in ("soc_yan_semenov/gamedata/sounds/characters_voice/dialogs/eng/yantar_general_ucheniy_talk_start_%s.ogg" % i,
                    "soc_yan_semenov/gamedata/sounds/characters_voice/dialogs/yantar_general_ucheniy_talk_start_%s.ogg" % i):
            if not os.path.exists(os.path.join(PATCHES, rel)):
                missing.append(rel)
    for rel in ("soc_yan_x16_quests/gamedata/sounds/characters_voice/dialogs/eng/yantar_help_scientist_111111.ogg",
                "soc_ru_voices/gamedata/sounds/characters_voice/dialogs/yantar_help_scientist_111111.ogg"):
        if not os.path.exists(os.path.join(PATCHES, rel)):
            missing.append(rel)
    check("every voice file named by the tables ships in a patch (EN and RU)", not missing, missing)

    # install(): one tick per level.add_call, a second install replaces the first
    E["__calls"] = lua.table_from({})
    reset()
    S["install"]()
    S["install"]()
    calls = list(E["__calls"].values())
    check("install registers a tick; the older one stops after a re-install", len(calls) == 2 and calls[0]() is True and calls[1]() is False)

    print("\nALL PASS" if fails == 0 else "\n%d FAILED" % fails)
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
