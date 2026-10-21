"""Offline check (no game) of coop_soc_barros.script (the Bar / Rostok chain tick), the Barkeep states and hand-ins of coop_soc_bar.script (X16 documents,
Brain Scorcher job) and coop_soc_hunter.script (the hunter's rifle).
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL scripts in a Lua 5.1 VM with a small engine mock (story flags, players with an inventory, level tick, task hand-out)."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
DV = os.path.join(os.path.dirname(PATCH), "soc_dv_x18_quests")
fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local barros_path, bar_path, hunter_path, roots = ...
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
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return not E.__client end
function E.OnClient() return E.__client end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
E.level = { name = function() return "coop_l05_bar" end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.db = { mp_actors = {} }
function E.__player(id, name)
	local o = { __id = id, __name = name, __alive = true, __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:object(sec) return self.__items[sec] end
	E.db.mp_actors[id] = o
	return o
end
E.coop_soc_opening = { voice_lang = function() return E.__voice_lang end }
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
E.dialogs = { who_is_npc = function(a, b) if a == nil then return nil, b end return b, a end,
	relocate_item_section_from_actor = function(a, b, sec) E.__moved[#E.__moved + 1] = sec; local act = a or b; act.__items[sec] = nil end }
E.__moved = {}
E.__money = 0
E.dialogs_money = { give_money_to_actor_4000 = function() E.__money = E.__money + 4000 end,
	give_money_to_actor_5000 = function() E.__money = E.__money + 5000 end, give_money_to_actor_10000 = function() E.__money = E.__money + 10000 end }
E.dialogs_item = { transfer_family_gun = function(a, b) E.__moved[#E.__moved + 1] = "wpn_toz34_m2"; local act = a or b; act.__items["wpn_toz34_m2"] = nil end }
E.dialogs_coop_l05_bar = {}
local function mk_sound(path)
	local s = { path = path }
	function s:playing() return false end
	function s:stop() end
	function s:play(o, d, f) E.__played[#E.__played + 1] = path end
	return s
end
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(t, path) return mk_sound(path) end })
E.__me = nil
function E.getLocalActor() return E.__me end
E.getFS = function() return { exist = function(self, root, name)
	for r in string.gmatch(roots, "[^|]+") do
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
	fn()
	return env
end
E.coop_soc_barros = load(barros_path, "coop_soc_barros")
E.coop_soc_bar = load(bar_path, "coop_soc_bar")
E.coop_soc_hunter = load(hunter_path, "coop_soc_hunter")
return E
'''


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    S = lambda p, n: os.path.join(p, "gamedata", "scripts", n)
    E = lua.execute(PRELUDE, S(PATCH, "coop_soc_barros.script"), S(DV, "coop_soc_bar.script"), S(PATCH, "coop_soc_hunter.script"),
                    PATCH.replace("\\", "/") + "|" + DV.replace("\\", "/"))
    br, bar, hun = E["coop_soc_barros"], E["coop_soc_bar"], E["coop_soc_hunter"]

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(n):
        E["story_flags"]["give_flag"](n)

    def reset():
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__moved"] = lua.table_from({})
        E["__money"] = 0
        br["reset_given"]()

    def player(pid):
        return E["__player"](pid, "p%d" % pid)

    def step():
        return br["step"]()

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def all_tasks():
        return sorted(k for k in E["__given"].keys())

    def everyone(task, ids):
        return all(given(task, i) == 1 for i in ids)

    DONE18 = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO"
    GO_MIL = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_MILITARY_STOP_DIALOG_INFO"

    # ------------------------------------------------------------ nothing before the job
    reset()
    p1, p2 = player(1), player(2)
    step()
    check("nothing is given at the start", all_tasks() == [], all_tasks())
    give(DONE18)
    step()
    check("the X18 hand-in alone gives no Bar / Rostok task (the X16 job is accepted in the dialog)", all_tasks() == [], all_tasks())

    # ------------------------------------------------------------ X16 documents job
    st = lambda: bar["state"]()
    check("Barkeep after the X18 hand-in: offers the X16 job (SoC 19)", st() == "x16offer", st())
    give("BAR_X16_DOCUMENTS_START")
    step()
    check("X16 job accepted: ONE task to both players", everyone("bar_start_go_to_yantar_quest_task", (1, 2)))
    check("Barkeep: waits for the documents", st() == "x16wait" and bar["st_wait"](None, None))
    step(); step()
    check("given once per player", given("bar_start_go_to_yantar_quest_task", 1) == 1 and len(all_tasks()) == 2, all_tasks())
    p3 = player(3)
    step()
    check("late joiner gets the open job", given("bar_start_go_to_yantar_quest_task", 3) == 1)
    check("documents not found: no GAIN flag", not flag("YAN_X16_DOCUMENTS_GAIN"))

    # a player takes the documents (Ghost's body on Yantar)
    p2["__items"]["lab_x16_documents"] = True
    step()
    check("a player holds lab_x16_documents: YAN_X16_DOCUMENTS_GAIN", flag("YAN_X16_DOCUMENTS_GAIN"))
    check("Barkeep: asks for the X16 documents (SoC 12)", st() == "x16docs" and bar["st_x16docs"](None, None))
    check("phrase 1211 precondition: the holder can hand them in", bar["has_x16_docs"](None, p2))
    check("phrase 1211 precondition: a player without them cannot (somebody else holds them)", not bar["has_x16_docs"](None, p1))
    bar["take_x16_docs"](None, p1)
    check("the other player's talk takes nothing", len(list(E["__moved"].values())) == 0)
    bar["take_x16_docs"](None, p2)
    check("the holder's documents are taken", list(E["__moved"].values()) == ["lab_x16_documents"], list(E["__moved"].values()))
    give("BAR_X16_DOCUMENTS_DONE")                 # phrase 1211 sets it with the actions
    step()
    check("Barkeep: offers the Scorcher job (SoC 13)", st() == "radaroffer" and bar["st_radaroffer"](None, None))
    check("the X16 task is not given again after the hand-in", given("bar_start_go_to_yantar_quest_task", 1) == 1)

    # no soft-lock: the party took the documents but a player died with them / the lab was done another way
    reset()
    player(1)
    give(DONE18)
    give("BAR_X16_DOCUMENTS_START")
    give("X16_GHOST_DOCS_TAKEN")
    step()
    check("Ghost's documents taken (yantar_restore flag): GAIN", flag("YAN_X16_DOCUMENTS_GAIN"))
    me = player(7)
    check("documents lost with a dead player: the hand-in is open to the talker", bar["has_x16_docs"](None, me))
    reset()
    player(1)
    give(DONE18)
    step()
    check("nothing found yet: no hand-in", not bar["has_x16_docs"](None, player(8)))
    give("YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO")
    step()
    check("the lab done another way (installation off): GAIN, the Barkeep chain cannot stall", flag("YAN_X16_DOCUMENTS_GAIN") and st() == "x16docs")

    # ------------------------------------------------------------ Brain Scorcher job
    reset()
    player(1)
    player(2)
    give(DONE18)
    give("BAR_X16_DOCUMENTS_START")
    give("BAR_X16_DOCUMENTS_DONE")
    step()
    check("X16 done: the Scorcher job is not started by itself", given("bar_start_go_to_military_quest_task", 1) == 0)
    check("X16 done: the X16 task is gone (done at the Barkeep)", given("bar_start_go_to_yantar_quest_task", 1) == 0)
    give("BAR_DEACTIVATE_RADAR_START")
    give(GO_MIL)
    step()
    check("Scorcher job accepted: Military step to both players", everyone("bar_start_go_to_military_quest_task", (1, 2)))
    check("Barkeep: just greets while the job runs (SoC 16)", st() == "radar" and bar["st_radar"](None, None))
    give("BAR_START_GO_TO_MILITARY_QUEST_TASK_INFO")
    step()
    give("MIL_START_GO_TO_RADAR_QUEST_TASK_INFO")
    step()
    check("the Scorcher job is ONE task: not given again on Military / Radar", given("bar_start_go_to_military_quest_task", 1) == 1 and given("bar_start_go_to_military_quest_task", 2) == 1)
    check("the hidden Military step mil_start_go_to_radar is never given", given("mil_start_go_to_radar_quest_task", 1) == 0 and given("mil_start_go_to_radar_quest_task", 2) == 0)
    give("X10_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO")
    step()
    check("Scorcher off: BAR_DEACTIVATE_RADAR_DONE", flag("BAR_DEACTIVATE_RADAR_DONE"))

    # exactly one Barkeep state precondition at every stage of the job
    states = ["st_agroprom", "st_offer", "st_wait", "st_docs", "st_default", "st_x16offer", "st_x16docs", "st_radaroffer", "st_radar"]
    seq = [[], ["ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO"], ["BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO"],
           ["BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO"], ["BAR_DARKLAB_DOCUMENT_GAIN"], [DONE18],
           ["BAR_X16_DOCUMENTS_START"], ["YAN_X16_DOCUMENTS_GAIN"], ["BAR_X16_DOCUMENTS_DONE"], ["BAR_DEACTIVATE_RADAR_START"]]
    E["__reset_flags"]()
    for fl in seq:
        for f in fl:
            give(f)
        n = sum(1 for s in states if bar[s](None, None))
        check("exactly one Barkeep greeting after %s" % (fl[0] if fl else "nothing"), n == 1, [s for s in states if bar[s](None, None)])

    # ------------------------------------------------------------ hunter
    reset()
    player(1)
    player(2)
    step()
    check("hunter: no task before the quest is accepted", given("bar_start_find_the_family_gun_quest_task", 1) == 0)
    check("hunter greeting: problem", hun["state"]() == "new" and hun["st_new"](None, None))
    give("BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_STOP_DIALOG_INFO")
    step()
    check("hunter quest accepted: 'find the rifle' to both players", everyone("bar_start_find_the_family_gun_quest_task", (1, 2)))
    check("hunter greeting: any news", hun["state"]() == "wait")
    check("the return step waits for the rifle", given("bar_soc_hunter_return_task", 1) == 0)
    p1 = E["db"]["mp_actors"][1]
    p1["__items"]["wpn_toz34_m2"] = True
    step()
    check("a player holds the rifle: BAR_HUNTER_RIFLE_FOUND", flag("BAR_HUNTER_RIFLE_FOUND"))
    check("'return the rifle to the hunter' to both players", everyone("bar_soc_hunter_return_task", (1, 2)))
    check("the hunter hand-in precondition: the holder", hun["has_rifle"](None, p1))
    check("the hunter hand-in precondition: not the player without the rifle", not hun["has_rifle"](None, E["db"]["mp_actors"][2]))
    hun["take_rifle"](None, p1)
    hun["reward"](None, p1)
    check("the rifle is taken, 4000 paid (SoC have_hunter_reward)", list(E["__moved"].values()) == ["wpn_toz34_m2"] and int(E["__money"]) == 4000,
          (list(E["__moved"].values()), E["__money"]))
    give("BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_IDLE_STOP_DIALOG_INFO")
    check("hunter greeting afterwards: thanks", hun["state"]() == "done" and hun["st_done"](None, None))
    step()
    check("hunter tasks are given once", given("bar_start_find_the_family_gun_quest_task", 1) == 1 and given("bar_soc_hunter_return_task", 1) == 1)
    # a rifle lost with a dead player: the party found it once, the hand-in stays open
    reset()
    player(1)
    give("BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_STOP_DIALOG_INFO")
    give("BAR_HUNTER_RIFLE_FOUND")
    check("rifle lost after it was found: the talker can still hand in", hun["has_rifle"](None, E["db"]["mp_actors"][1]))
    reset()
    player(1)
    give("BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_IDLE_STOP_DIALOG_INFO")
    step()
    check("hunter done (old save): nothing is given", all_tasks() == [], all_tasks())

    # ------------------------------------------------------------ Kruglov
    reset()
    player(1)
    player(2)
    step()
    check("Kruglov: nothing before the radio call", all_tasks() == [], all_tasks())
    give("ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_END_INFO")
    step()
    check("Kruglov calls: 'Get through to Kruglov' to both", everyone("ros_start_help_kruglov_quest_task", (1, 2)))
    give("ROS_SMART_TERRAIN_3_KILLER_1_SQUAD_DEAD")
    step()
    check("Mercs dead: 'Talk to professor Kruglov' to both", everyone("ros_soc_kruglov_talk_task", (1, 2)))
    check("the escort waits until a player reached Kruglov", given("ros_start_escort_kruglov_to_yantar_quest_task", 1) == 0)
    p3 = player(3)
    step()
    check("late joiner gets the talk step only", given("ros_soc_kruglov_talk_task", 3) == 1 and given("ros_start_help_kruglov_quest_task", 3) == 0)
    give("BAR_KRUGLOV_FOLLOW_ACTOR")
    step()
    check("Kruglov speaks / walks: the escort to every player", everyone("ros_start_escort_kruglov_to_yantar_quest_task", (1, 2, 3)))
    check("the bring step waits for Yantar", given("ros_soc_kruglov_bring_task", 1) == 0)
    give("YAN_SMART_TERRAIN_1_WALKER_KRUGLOV_GO_TO_SAXAROV_INFO")
    step()
    check("on Yantar: 'Talk to Kruglov' to every player", everyone("ros_soc_kruglov_bring_task", (1, 2, 3)))
    give("YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO")
    step(); step()
    check("each Kruglov task is given once per player", all(v == 1 for v in (given(t, i) for t in ("ros_start_help_kruglov_quest_task", "ros_soc_kruglov_talk_task",
          "ros_start_escort_kruglov_to_yantar_quest_task", "ros_soc_kruglov_bring_task") for i in (1, 2))), all_tasks())
    # skipped steps: reaching Yantar without meeting Kruglov first
    reset()
    player(1)
    give("YAN_SMART_TERRAIN_1_WALKER_KRUGLOV_GO_TO_SAXAROV_INFO")
    step()
    check("Yantar first: the earlier flag is set, only the open step is given", flag("BAR_KRUGLOV_FOLLOW_ACTOR")
          and all_tasks() == ["ros_soc_kruglov_bring_task|1"], all_tasks())
    # a dead / respawned player gets the open tasks (a new player id is a new player)
    reset()
    a, b = player(1), player(2)
    give("BAR_X16_DOCUMENTS_START")
    step()
    b["__alive"] = False
    step()
    c = player(5)
    step()
    check("a respawned player (new id) gets the open job", given("bar_start_go_to_yantar_quest_task", 5) == 1)
    check("a dead player is not served", given("bar_start_go_to_yantar_quest_task", 2) == 1)

    # install registers the level call
    br["install"]()
    check("install registers one level call", len(list(E["__calls"].values())) >= 1)

    # ------------------------------------------------------------ voice of the new Barkeep lines
    voiced = list(bar["VOICE_IDS"].values())
    for pid in ("121", "13121", "1314"):
        check("phrase %s has a recording entry" % pid, pid in voiced)
    for lang in ("eng", "rus"):
        E["__voice_lang"] = lang
        for pid in ("121", "13121", "1314"):
            p = bar["voice_path"](pid)
            if lang == "eng":
                ok = p is not None and os.path.isfile(os.path.join(PATCH, "gamedata", "sounds", p.replace("\\", os.sep) + ".ogg"))
                check("voice %s eng: file ships in bar_soc_quests" % pid, ok, p)
            else:
                ok = p == "characters_voice\\dialogs\\bar_bar_barmen_start_" + pid and os.path.isfile(os.path.join(os.path.dirname(PATCH), "soc_ru_voices", "gamedata", "sounds", p.replace("\\", os.sep) + ".ogg"))
                check("voice %s rus: Russian file ships in soc_ru_voices" % pid, ok, p)
    E["__voice_lang"] = "eng"
    check("a line without a recording is silent", bar["voice_path"]("1316") is None)
    me = E["__player"](9, "talker")
    npc = E["__player"](10, "barman")
    E["__client"] = True
    E["__me"] = me
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    bar["say_13121"](npc, me)
    played = list(E["__played"].values())
    check("say_13121 plays the English recording on the talker's machine", played == ["characters_voice\\dialogs\\eng\\bar_bar_barmen_start_13121"], played)
    E["__client"] = False
    log = [str(x) for x in E["__log"].values()]
    check("the PDA archive line is emitted for the new phrase", any(x == "EMIT coop_soc_barman_13121" for x in log))
    bar["say_1211"](me, npc)
    hun["say_f_1"](npc, me)
    log = [str(x) for x in E["__log"].values()]
    check("PDA archive lines of the hand-in and of the hunter", "EMIT coop_soc_barman_1211" in log and "EMIT coop_soc_hunter_f_1" in log)

    print("\n%d FAIL" % fails if fails else "\nALL PASS")
    sys.exit(1 if fails else 0)


main()
