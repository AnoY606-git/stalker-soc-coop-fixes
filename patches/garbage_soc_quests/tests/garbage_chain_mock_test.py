"""Offline check (no game) of coop_scn_garbage_soc.script.
usage: python garbage_chain_mock_test.py     (needs `pip install lupa`, like patches\\agroprom_soc\\tests\\agroprom_chain_mock_test.py)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with position, level tick, story objects, dialog money) and proves:
  * every task of the Garbage chain is handed to EVERY player, once, at the right stage; a late joiner gets the tasks of the stage that is open now
  * "Meet with Seriy": Fox's flag on Cordon (any level) or the arrival on the Garbage; it closes with Seriy's talk; the Agroprom task follows Seriy's dialog flag
  * Bes: task on arrival, the next two follow his dialog answer and the ambush squads
  * Duty: the wave starts with a player who stays near the checkpoint (not with a short visit); objective 2 only after the wave AND a player kill;
    a wave without a player kill never gives the commander task (nothing to wait for, no soft lock); the report dialog helper pays the talking player once
  * Seriy / Bes / the commander dead: the flags their dialogs give are set (the commander's death also opens the gate)
  * a new Lua VM (a level load) gives nothing that is already done
"""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
fails = 0
n_checks = 0


def check(name, ok, info=""):
    global fails, n_checks
    n_checks += 1
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local script_path = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}
E.__calls = {}
E.__side = "server"
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return E.__side == "server" end
function E.OnClient() return E.__side == "client" end
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
function E.__setpos(o, x, y, z) o.__pos = E.vector():set(x, y, z) end
E.__level = "coop_l02_garbage"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.db = { mp_actors = {} }
E.__story = {}           -- story name -> { id = n, alive = bool }
function E.get_story_object_id(name) local s = E.__story[name]; return s and s.id or nil end
function E.alife() return { object = function(self, id)
	for _, s in pairs(E.__story) do
		if s.id == id then return { alive = function() return s.alive end } end
	end
	return nil
end } end
E.__money = {}
E.__local = nil
E.dialogs = { relocate_money_to_actor = function(a, b, n) E.__money[E.__local:name()] = (E.__money[E.__local:name()] or 0) + n end }
function E.getLocalActor() return E.__local end
E.__scenes = {}
E.coop_scenes = { register = function(def) E.__scenes[def.id] = def; return true end }
E.__news = {}
E.game = { translate_string = function(id) return "T:" .. id end }
E.coop_pda_phrases = { phrase_speaker = {} }
E.__emitted = {}
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__emitted[#E.__emitted + 1] = tid end }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z) }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	E.db.mp_actors[id] = o
	return o
end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_scn_garbage_soc"))
setfenv(fn, env)
fn()
E.__env = env
return E
'''

TASKS = {
    "FOX": "gar_start_talk_to_gray_quest_task",
    "AGR": "gar_start_go_to_the_agroprom_quest_task",
    "T1": "gar_start_talk_to_devil_quest_task",
    "T2": "gar_start_help_to_repel_the_bandits_attack_quest_task",
    "T3": "gar_start_talk_to_devil_1_quest_task",
    "K1": "gar_start_help_fight_off_the_mutants_quest_task",
    "K2": "gar_soc_duty_report_task",
}
HIDDEN_A = "gar_start_help_the_gray_to_fight_off_the_bandits_quest_task"


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    path = os.path.join(PATCH, "gamedata", "scripts", "coop_scn_garbage_soc.script")
    st = {}

    def tick(ms=1500):
        E = st["E"]
        E["__time"] = E["__time"] + ms
        for f in list(E["__calls"].values()):
            f()

    def reset(level="coop_l02_garbage"):
        E = lua.execute(PRELUDE, path)
        E["__level"] = level
        st["E"] = E
        st["env"] = E["__env"]
        st["env"].install()

    def player(pid, name, x=0.0, y=0.0, z=0.0):
        return st["E"]["__player"](pid, name, x, y, z)

    def flag(n):
        return st["E"]["story_flags"]["has_flag"](n)

    def give(n):
        st["E"]["story_flags"]["give_flag"](n)

    def given(task, pid):
        v = st["E"]["__given"][task + "|" + str(pid)]
        return int(v) if v is not None else 0

    def all_once(task, pids):
        return all(given(task, p) == 1 for p in pids)

    def none(task, pids):
        return all(given(task, p) == 0 for p in pids)

    def story(name, sid, alive=True):
        s = lua.table_from({"id": sid, "alive": alive})
        st["E"]["__story"][name] = s
        return s

    ALL = list(TASKS.values())

    # ---- Cordon: Fox's flag gives "Meet with Seriy" to everybody, on any level
    reset("coop_l01_escape")
    a = player(1, "qaa")
    b = player(2, "qab")
    tick()
    check("Cordon, before Fox: nothing is given", all(none(t, (1, 2)) for t in ALL))
    give("ESC_SMART_TERRAIN_6_STALKER_FOX_INFO_MILITARY_STOP_DIALOG_INFO")      # Fox's dialog, last phrase
    tick()
    check("Cordon, Fox's dialog done: 'Meet with Seriy' for EVERY player, once", all_once(TASKS["FOX"], (1, 2)))
    check("Cordon: no Garbage task besides it", all(none(TASKS[k], (1, 2)) for k in ("AGR", "T1", "T2", "T3", "K1", "K2")))
    tick()
    tick()
    check("later ticks do not give again", all_once(TASKS["FOX"], (1, 2)))
    c = player(3, "qac")
    tick()
    check("a late joiner on Cordon gets it once", all_once(TASKS["FOX"], (3,)))
    check("the level maker's step 'help the Gray' is never given", none(HIDDEN_A, (1, 2, 3)))

    # ---- Garbage: arrival without Fox (fallback), Bes on arrival
    reset()
    a = player(1, "qaa", 35.7, 0.4, -313.0)
    b = player(2, "qab", 36.0, 0.4, -312.0)
    tick()
    check("before the arrival flag nothing is given", all(none(t, (1, 2)) for t in ALL))
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    tick()
    check("arrival: 'Meet with Seriy' (fallback, no Fox) for EVERY player, once", all_once(TASKS["FOX"], (1, 2)))
    check("arrival: 'Respond to the call for help' (Bes) for EVERY player, once", all_once(TASKS["T1"], (1, 2)))
    check("arrival: nothing of the later steps", all(none(TASKS[k], (1, 2)) for k in ("AGR", "T2", "T3", "K1", "K2")))
    # Bes's dialog answer
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO")
    c = player(3, "qac", 36.0, 0.4, -312.0)
    tick()
    check("Bes answered: 'Repel the bandit raid' for EVERY player incl. the joiner, once", all_once(TASKS["T2"], (1, 2, 3)))
    check("Bes answered: the call-for-help task is over (the joiner does not get it)", none(TASKS["T1"], (3,)))
    give("GAR_SMART_TERRAIN_3_BANDIT_1_SQUAD_DEAD")
    tick()
    check("one ambush squad dead: 'Talk to Bes' not yet", none(TASKS["T3"], (1, 2, 3)))
    give("GAR_SMART_TERRAIN_3_BANDIT_2_SQUAD_DEAD")
    d = player(4, "qad", 36.0, 0.4, -312.0)
    tick()
    check("both ambush squads dead: 'Talk to Bes' for EVERY player, once", all_once(TASKS["T3"], (1, 2, 3, 4)))
    check("both ambush squads dead: the raid task is over (a joiner does not get it)", none(TASKS["T2"], (4,)))
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO")
    e = player(5, "qae", 36.0, 0.4, -312.0)
    tick()
    check("Bes paid: 'Talk to Bes' is over for a joiner", none(TASKS["T3"], (5,)))

    # ---- Seriy: his dialog flag gives the Agroprom task
    check("before Seriy's talk: no Agroprom task", all(none(TASKS["AGR"], (p,)) for p in (1, 2, 3, 4)))
    give("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO")
    tick()
    check("Seriy's dialog done: the Agroprom task for EVERY player, once", all_once(TASKS["AGR"], (1, 2, 3, 4, 5)))
    f = player(6, "qaf", 36.0, 0.4, -312.0)
    tick()
    check("Seriy's dialog done: a joiner gets the Agroprom task but not 'Meet with Seriy'", all_once(TASKS["AGR"], (6,)) and none(TASKS["FOX"], (6,)))
    give("AGR_STALKER_HELP_1_INFO")
    g = player(7, "qag", 36.0, 0.4, -312.0)
    tick()
    check("Agroprom gate reached: the Agroprom task is over", none(TASKS["AGR"], (7,)))

    # ---- Duty: the wave needs a player who stays
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    b = player(2, "qab", 200.0, 0.4, -100.0)
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    tick()
    check("far from the checkpoint: no wave", not flag("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
    st["E"]["__setpos"](b, 40.0, 0.5, 232.0)
    tick(2000)
    check("a player just arrived near the checkpoint: no wave yet", not flag("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
    st["E"]["__setpos"](b, 200.0, 0.4, -100.0)
    tick(2000)
    st["E"]["__setpos"](b, 40.0, 0.5, 232.0)
    tick(2000)
    tick(2000)
    check("a short visit and a new one: still no wave (the timer restarts)", not flag("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
    tick(3000)
    tick(3000)
    check("a player stays near the checkpoint: the wave starts", flag("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
    tick()
    check("wave started: 'Help the Duty checkpoint' (kill the boars) for EVERY player, once", all_once(TASKS["K1"], (1, 2)))
    check("wave started: the commander task is not given yet", none(TASKS["K2"], (1, 2)))
    for i in (1, 2, 3, 4):
        give("GAR_SMART_TERRAIN_8_M_BOAR_%d_SQUAD_DEAD" % i)
    give("GAR_DUTY_BOAR_KILLED_3")                          # a player killed a boar
    c = player(3, "qac", 200.0, 0.4, -100.0)
    tick()
    check("boars dead, a player killed one: 'Talk with the Duty commander' for EVERY player incl. the joiner, once", all_once(TASKS["K2"], (1, 2, 3)))
    check("boars dead: the kill task is over (the joiner does not get it)", none(TASKS["K1"], (3,)))

    # dialog helpers
    E = st["E"]
    E["__side"] = "client"
    la = player(1, "qaa", 40.0, 0.5, 232.0)
    E["__local"] = E["db"]["mp_actors"][1]
    env = st["env"]
    check("report is offered to the talking player", env.report_open(None, None) is True)
    env.report_pay(None, None)
    check("report: the shared flag completes the task for everybody", flag("GAR_SOC_DUTY_REPORT_INFO"))
    check("report: the reward goes to the talking player", E["__money"]["qaa"] == 1500, E["__money"]["qaa"])
    check("report: not offered to him a second time", env.report_open(None, None) is False)
    env.report_pay(None, None)
    check("report: a second action call does not pay again", E["__money"]["qaa"] == 1500)
    E["__local"] = E["db"]["mp_actors"][2]
    check("another player can still be thanked (his own reward)", env.report_open(None, None) is True)
    env.report_pay(None, None)
    check("the other player is paid once too", E["__money"]["qab"] == 1500 and E["__money"]["qaa"] == 1500)
    E["__side"] = "server"
    tick()
    h = player(8, "qah", 200.0, 0.4, -100.0)
    tick()
    check("after the report a joiner does not get the commander task", none(TASKS["K2"], (8,)))
    check("the favor dialog is no longer offered once the wave started", env.favor_open(None, None) is False)

    # ---- Seriy (2500) and Bes (2000) pay in their dialogs, to the talking player, once
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    b = player(2, "qab", 200.0, 0.4, -100.0)
    E = st["E"]
    env = st["env"]
    E["__side"] = "client"
    E["__local"] = E["db"]["mp_actors"][1]
    env.pay_seriy(None, None)
    env.pay_seriy(None, None)
    env.pay_bes(None, None)
    env.pay_bes(None, None)
    check("Seriy pays 2500 once to the talking player", E["__money"]["qaa"] == 4500 and E["__money"]["qab"] is None, E["__money"]["qaa"])
    E["__local"] = E["db"]["mp_actors"][2]
    env.pay_seriy(None, None)
    check("the other player talking to Seriy is paid his own 2500", E["__money"]["qab"] == 2500, E["__money"]["qab"])
    E["__side"] = "server"
    E["__local"] = E["db"]["mp_actors"][1]
    env.pay_bes(None, None)
    check("a repeated call from the server context does not pay again", E["__money"]["qaa"] == 4500)

    # ---- payment on every host type (no OnClient() gate): the speakers decide who is paid, once
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)      # the host player of a listen host
    b = player(2, "qab", 200.0, 0.4, -100.0)      # a remote client
    npc = player(30, "seriy", 200.0, 0.4, -100.0)
    E = st["E"]
    env = st["env"]
    pa, pb, pn = E["db"]["mp_actors"][1], E["db"]["mp_actors"][2], E["db"]["mp_actors"][30]
    E["__local"] = pa
    for side in ("server", "client", "server", "client"):     # the host's server and client context both run the action, twice
        E["__side"] = side
        env.pay_seriy(pa, pn)
    check("listen host, host player talks (OnClient false or true): paid 2500 exactly once", E["__money"]["qaa"] == 2500 and E["__money"]["qab"] is None, E["__money"]["qaa"])
    E["__side"] = "server"
    env.pay_seriy(pb, pn)
    env.pay_bes(pn, pb)
    check("listen host machine, a REMOTE player talks: this machine pays nothing (his own machine does)", E["__money"]["qaa"] == 2500 and E["__money"]["qab"] is None)
    E["__local"] = pb
    for side in ("client", "client"):
        E["__side"] = side
        env.pay_seriy(pb, pn)
        env.pay_bes(pn, pb)                    # speaker order does not matter
    check("the remote player's own machine pays him once per reward (Seriy 2500 + Bes 2000)", E["__money"]["qab"] == 4500 and E["__money"]["qaa"] == 2500, E["__money"]["qab"])
    E["__side"] = "server"
    E["__local"] = None
    env.pay_seriy(pa, pn)
    env.pay_bes(pb, pn)
    check("dedicated server (no local actor): pays nobody and sets no paid flag", E["__money"]["qaa"] == 2500 and E["__money"]["qab"] == 4500
          and not flag("GAR_SOC_PAID_BES_QAA") and not flag("GAR_SOC_PAID_SERIY_QAB_X"))
    E["__local"] = pa
    E["__side"] = "client"
    env.pay_bes(pa, pn)
    check("the host player is still paid Bes's 2000 afterwards (nothing was blocked by the server calls)", E["__money"]["qaa"] == 4500, E["__money"]["qaa"])
    # commander report on a listen host
    reset()
    a = player(1, "qaa", 40.0, 0.5, 232.0)
    b = player(2, "qab", 40.0, 0.5, 232.0)
    npc = player(30, "prapor", 40.0, 0.5, 232.0)
    E = st["E"]
    env = st["env"]
    pa, pb, pn = E["db"]["mp_actors"][1], E["db"]["mp_actors"][2], E["db"]["mp_actors"][30]
    for i in (1, 2, 3):
        give("GAR_SMART_TERRAIN_8_M_BOAR_%d_SQUAD_DEAD" % i)
    give("GAR_SMART_TERRAIN_8_M_BOAR_4_SQUAD_DEAD")
    give("GAR_DUTY_BOAR_KILLED_1")
    E["__local"] = pa
    for side in ("server", "client"):
        E["__side"] = side
        env.report_pay(pa, pn)
    check("report on a listen host: the host player gets 1500 once", E["__money"]["qaa"] == 1500 and E["__money"]["qab"] is None, E["__money"]["qaa"])
    E["__side"] = "server"
    env.report_pay(pb, pn)
    check("report: the host machine does not pay the remote talker", E["__money"]["qab"] is None)

    # ---- Duty: the favor from the commander
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    env = st["env"]
    check("favor offered before the wave", env.favor_open(None, None) is True)
    env.favor_start(None, None)
    tick()
    check("favor accepted: the wave flag is set", flag("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))
    check("favor accepted: the kill task is given", all_once(TASKS["K1"], (1,)))

    # ---- Duty: no player killed a boar (SoC gar_actor_looser)
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    give("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO")
    tick()
    for i in (1, 2, 3, 4):
        give("GAR_SMART_TERRAIN_8_M_BOAR_%d_SQUAD_DEAD" % i)
    tick()
    check("wave over, no player kill: the commander task is not given", none(TASKS["K2"], (1,)))
    tick()
    check("wave over, no player kill: still no commander task later (a joiner too)", none(TASKS["K2"], (1,)) and not flag("GAR_SOC_DUTY_REPORT_INFO"))
    check("no pass is given by this script", not flag("GAR_FREE_PASS"))

    # ---- characters dead
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    story("gar_smart_terrain_2_stalker_gray", 101, True)
    story("gar_smart_terrain_4_stalker_devil", 102, True)
    story("gar_smart_terrain_8_duty_prapor", 103, True)
    tick()
    check("everybody alive: no dead-guard flags", not flag("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO") and not flag("GAR_FREE_PASS"))
    st["E"]["__story"]["gar_smart_terrain_2_stalker_gray"]["alive"] = False
    tick()
    check("Seriy dead: his talk flag is given", flag("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO"))
    tick()
    check("Seriy dead: the Agroprom task goes to every player", all_once(TASKS["AGR"], (1,)))
    st["E"]["__story"]["gar_smart_terrain_4_stalker_devil"]["alive"] = False
    tick()
    check("Bes dead: his answer and payment flags are given", flag("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO") and flag("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO"))
    check("Bes dead: the pass is still closed", not flag("GAR_FREE_PASS"))
    st["E"]["__story"]["gar_smart_terrain_8_duty_prapor"]["alive"] = False
    tick()
    check("the Duty commander dead: the report flag and the pass (gate) are given", flag("GAR_SOC_DUTY_REPORT_INFO") and flag("GAR_FREE_PASS"))
    # the global used by the in-game hook
    reset()
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    st["E"]["GARSOC_FORCE_DEAD"] = lua.table_from({"gar_smart_terrain_2_stalker_gray": True})
    tick()
    check("test switch GARSOC_FORCE_DEAD makes Seriy count as dead", flag("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO"))

    # ---- only the Garbage level runs the level side
    reset("coop_l03_agroprom")
    a = player(1, "qaa", 40.0, 0.5, 232.0)
    tick(7000)
    tick(7000)
    check("another level: no Duty wave from a player standing at the same coordinates", not flag("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO"))

    # ---- a new Lua VM (level load) gives nothing that is done
    reset()
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    give("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO")
    give("AGR_STALKER_HELP_1_INFO")
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO")
    give("GAR_SMART_TERRAIN_3_BANDIT_1_SQUAD_DEAD")
    give("GAR_SMART_TERRAIN_3_BANDIT_2_SQUAD_DEAD")
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO")
    give("GAR_START_HELP_FIGHT_OFF_THE_MUTANTS_QUEST_TASK_INFO")
    for i in (1, 2, 3, 4):
        give("GAR_SMART_TERRAIN_8_M_BOAR_%d_SQUAD_DEAD" % i)
    give("GAR_DUTY_BOAR_KILLED_1")
    give("GAR_SOC_DUTY_REPORT_INFO")
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    tick()
    check("everything done in the save: a reload gives no task at all", all(none(t, (1,)) for t in ALL))

    # ---- two installs in a row: the old tick retires
    reset()
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    a = player(1, "qaa", 200.0, 0.4, -100.0)
    st["env"].install()
    tick()
    check("two installs: the task is given once", all_once(TASKS["T1"], (1,)))

    # ---- Seriy's radio call of mod 8.0 (scene gar_seriy_sos of the Scene Director): same trigger as the mod's logic, once, every player
    reset()
    E = st["E"]
    sc = E["__scenes"]["gar_seriy_sos"]
    check("SOS: the scene is registered for the Garbage, once, no skip", sc is not None and sc["level"] == "coop_l02_garbage" and sc["once"] is True and sc["skip"] == "none")

    def trig(now):
        return bool(sc["trigger"](lua.table_from({"now": now})))

    check("SOS: not before Bes's job is paid", not trig(1000) and not trig(9000))
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_STOP_DIALOG_INFO")
    give("GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO")
    check("SOS: not at the arrival or with Bes's answer only", not trig(20000))
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO")
    check("SOS: Bes paid: the delay starts (20 game seconds of the mod = 2 s)", not trig(30000))
    check("SOS: 1 s later still waiting", not trig(31000))
    check("SOS: after the delay it fires", trig(32100))
    steps = sc["steps"](None, None)
    kinds = [steps[i]["do"] for i in range(1, len(steps) + 1)]
    snd = [steps[i] for i in range(1, len(steps) + 1) if steps[i]["do"] == "snd2d"]
    check("SOS: steps = PDA news, the mod's sound grey_grey_1, wait", kinds == ["fn", "snd2d", "wait"], kinds)
    check("SOS: the sound is the mod's own file (script_sound.ltx path of grey_grey_1)",
          len(snd) == 1 and snd[0]["path"] == "characters_voice\scenario\coop_l02_garbage\grey_grey_1")
    # the PDA news (client side)
    act = lua.eval("function(log) return { give_game_news = function(self, ...) log[#log + 1] = table.concat({...}, '|') end } end")(E["__news"])
    E["db"]["actor"] = act
    steps[1]["fn"](None)
    news = [E["__news"][i] for i in range(1, len(E["__news"]) + 1)]
    check("SOS: the news shows the 8.0 task name and text of the call", len(news) == 1 and "st_gar_seriy_sos_name" in news[0] and "st_gar_seriy_sos_text" in news[0], news)
    # Seriy already talked to (as the mod: the section needs -GRAY_HELP_STOP): nothing
    reset()
    E = st["E"]
    sc = E["__scenes"]["gar_seriy_sos"]
    give("GAR_SMART_TERRAIN_4_STALKER_DEVIL_HELP_THE_AND_STOP_DIALOG_INFO")
    give("GAR_SMART_TERRAIN_2_STALKER_GRAY_HELP_STOP_DIALOG_INFO")
    check("SOS: Seriy was talked to already: no call", not trig(50000) and not trig(60000))

    print("%d checks, %d failed" % (n_checks, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
