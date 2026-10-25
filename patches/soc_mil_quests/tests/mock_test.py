"""Offline check (no game) of the Army Warehouses quest chain of patch soc_mil_quests.
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL scripts (coop_soc_mil.script, coop_soc_mil_say.script) in a Lua 5.1 VM with a small engine mock (story flags, players, task
hand-out) and plays the REAL dialogs of freedom_duty (dialogs_coop_l07_military.xml): the phrase graph is walked like the engine does it
(hidden phrases pick the first state whose precondition holds, actor choices are filtered by their preconditions, actions and flags run)."""
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.dirname(os.path.dirname(PATCH))
sys.path.insert(0, os.path.join(PATCH, "tools"))
import mil_model as M

fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local mil_path, say_path = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}
E.__calls = {}
E.__client = false
E.__money = {}
E.__me = nil
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
E.__calls2 = {}
E.level = { name = function() return "coop_l07_military" end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f; E.__calls2[#E.__calls2 + 1] = { f, g } end }
E.__hits = {}
E.__objs = {}
E.hit = setmetatable({ chemical_burn = 7, wound = 1 }, { __call = function() return { bone = function() end } end })
E.vector = function() local v = {}; function v:set(x, y, z) return self end; function v:sub(a, b) return self end; return v end
E.get_story_object = function(sid) return E.__objs[sid] end
E.xr_effects = {}
function E.__mkobj(name)
	local o = { __name = name }
	function o:position() return {} end
	function o:hit(h) E.__hits[#E.__hits + 1] = { name = name, power = h.power, type = h.type } end
	E.__objs[name] = o
	return o
end
E.db = { mp_actors = {} }
function E.__player(id, name)
	local o = { __id = id, __name = name, __alive = true }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	E.db.mp_actors[id] = o
	return o
end
function E.getLocalActor() return E.__me end
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
E.__npc = { money = function(self) return E.__npc_money end }
E.__npc_money = nil
E.dialogs = {
	who_is_npc = function(a, b) if a == E.__npc then return a, b end return b, a end,
	relocate_money_to_actor = function(a, b, n) local me = E.__me:name(); E.__money[me] = (E.__money[me] or 0) + n end,
	break_dialog = function() end,
}
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
E.coop_soc_mil = load(mil_path, "coop_soc_mil")
E.coop_soc_mil_say = load(say_path, "coop_soc_mil_say")
return E
'''


def load_dialogs():
    path = os.path.join(REPO, "patches", "freedom_duty", "gamedata", "configs", "gameplay", "dialogs_coop_l07_military.xml")
    root = ET.fromstring(open(path, "rb").read())
    out = {}
    for d in root.findall("dialog"):
        ph = {}
        for p in d.find("phrase_list").findall("phrase"):
            t = p.find("text")
            ph[p.get("id")] = dict(
                text=(t.text.strip() if t is not None and t.text else ""),
                pre=[x.text.strip() for x in p.findall("precondition")],
                act=[x.text.strip() for x in p.findall("action")],
                flags=[x.text.strip() for x in p.findall("give_flag")],
                nxt=[x.text.strip() for x in p.findall("next")])
        out[d.get("id")] = ph
    return out


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    scripts = os.path.join(PATCH, "gamedata", "scripts")
    E = lua.execute(PRELUDE, os.path.join(scripts, "coop_soc_mil.script"), os.path.join(scripts, "coop_soc_mil_say.script"))
    mil = E["coop_soc_mil"]
    say = E["coop_soc_mil_say"]
    DLG = load_dialogs()
    npc = E["__npc"]

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(*ns):
        for n in ns:
            E["story_flags"]["give_flag"](n)

    def reset():
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__money"] = lua.table_from({})
        E["SOCMIL_FORCE_DEAD"] = None
        E["__npc_money"] = None
        E["__client"] = False
        mil["reset_given"]()

    def player(pid, name=None):
        return E["__player"](pid, name or "p%d" % pid)

    def step():
        E["__client"] = False
        return mil["step"]()

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def money(name):
        v = E["__money"][name]
        return int(v) if v else 0

    def force_dead(*stories):
        E["SOCMIL_FORCE_DEAD"] = lua.table_from({s: True for s in stories})

    def call(modname, fn, a, b):
        m = {"coop_soc_mil": mil, "coop_soc_mil_say": say}.get(modname)
        if m is None:
            return None
        f = m[fn]
        if f is None:
            raise RuntimeError("missing Lua function %s.%s" % (modname, fn))
        return f(a, b)

    # --------------------------------------------------------------------------------------------
    # the dialog engine: walk the real phrase graph
    # --------------------------------------------------------------------------------------------
    def talk(dlg, me, picks=(), maxn=80):
        """Plays one talk of the player `me` with the NPC; returns the visited phrase ids (phrases with text).
        picks: phrase ids to choose at choice points (the first available when none matches)."""
        E["__me"] = me
        E["__client"] = True
        ph = DLG[dlg]
        picks = list(picks)
        visited = []

        def pre_ok(q):
            for pre in q["pre"]:
                mod, fn = pre.split(".")
                if not call(mod, fn, npc, me):
                    return False
            return True

        def run(pid):
            q = ph[pid]
            for a in q["act"]:
                mod, fn = a.split(".")
                if mod != "dialogs":
                    call(mod, fn, npc, me)
            for f in q["flags"]:
                give(f)

        def expand(nexts):
            """real phrases offered after a phrase: a hidden phrase (empty text) is a state switch, the first that holds is followed"""
            out = []
            hidden_done = False
            for n in nexts:
                q = ph[n]
                if not pre_ok(q):
                    continue
                if q["text"] == "":
                    if hidden_done:
                        continue
                    sub = expand(q["nxt"])
                    if sub:
                        hidden_done = True
                        run(n)
                        out += sub
                else:
                    out.append(n)
            return out

        avail = expand(["0"])
        for _ in range(maxn):
            if not avail:
                break
            choice = next((pk for pk in picks if pk in avail), avail[0])
            run(choice)
            visited.append(choice)
            q = ph[choice]
            if not q["nxt"] or "dialogs.break_dialog" in q["act"]:
                break
            avail = expand(q["nxt"])
        E["__client"] = False
        return visited

    # --------------------------------------------------------------------------------------------
    # 0. the XML matches the model; every Lua function exists
    # --------------------------------------------------------------------------------------------
    for key, d in M.DIALOGS.items():
        ph = DLG.get(d["id"])
        check("dialog %s present" % d["id"], ph is not None)
        if ph is None:
            continue
        ids = [p[0] for p in d["phrases"]]
        check("dialog %s phrase ids" % d["id"], sorted(ids) == sorted(ph.keys()))
        for pid, spk, nxt, pre, flags, acts in d["phrases"]:
            for p in pre:
                check("lua precondition %s" % p, mil[p] is not None)
            for a in acts:
                check("lua action %s" % a, mil[a] is not None)
            if spk != M.H and not (key == "mx" and pid == "31"):
                check("lua say_%s_%s" % (key, pid), say["say_%s_%s" % (key, pid)] is not None)
    for old in M.REMOVED_DIALOGS:
        check("old dialog %s gone" % old, old not in DLG)

    # --------------------------------------------------------------------------------------------
    # 1. exactly one state per NPC for every flag combination (every talk finds a greeting, never two)
    # --------------------------------------------------------------------------------------------
    relevant = [M.LK, M.MAXF, M.CP, M.MD, M.SJ1, M.SJ2, M.SD, M.ST, M.KEY, M.LD, M.DD, M.DONE, M.BP, M.END, M.CR, M.FEE] + M.DUTY_DEAD[:2]
    rnd = random.Random(7)
    bad = []
    for n in range(3000):
        reset()
        player(1, "tester")
        E["__me"] = E["db"]["mp_actors"][1]
        for f in relevant:
            if rnd.random() < 0.4:
                give(f)
        for key, d in M.DIALOGS.items():
            if d.get("plain"):
                continue
            ph0 = [p for p in d["phrases"] if p[0] == "0"][0]
            holds = 0
            for h in ph0[2]:
                hp = [p for p in d["phrases"] if p[0] == h][0]
                if all(mil[pre](npc, E["__me"]) for pre in hp[3]):
                    holds += 1
            if holds != 1:
                bad.append((key, holds))
                break
    check("exactly one greeting state per flag combination (3000 random combinations, 4 NPCs)", not bad, bad[:3])

    # --------------------------------------------------------------------------------------------
    # 2. Freedom route: Lukash -> Max -> destroy the Duty -> Lukash -> Barrier -> Cap -> Lukash
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice")
    B = player(2, "bob")
    step()
    for t in ("mil_start_report_to_max_quest_task", "mil_start_talk_to_the_cap_quest_task", "mil_start_kill_skull_quest_task",
              "mil_start_kill_the_sniper_on_the_tower_quest_task", "mil_soc_return_lukash_task", "rad_start_go_to_radar_quest_task"):
        check("nothing given before any dialog: " + t, given(t, 1) == 0 and given(t, 2) == 0)
    v = talk("mil_soc_lukash_dialog", A, ["1100"])
    check("Lukash first talk: greeting, Duty farmstead, OK", v[:4] == ["1001", "1100", "1101", "11011"] and v[-1] == "11012", v)
    check("Lukash gave the Duty job flag", flag(M.LK))
    step()
    check("report to Max: given to both players", given("mil_start_report_to_max_quest_task", 1) == 1 and given("mil_start_report_to_max_quest_task", 2) == 1)
    C = player(3, "carol")      # late joiner
    step()
    check("late joiner gets the open task", given("mil_start_report_to_max_quest_task", 3) == 1)
    step(); step()
    check("tasks are given once per player", given("mil_start_report_to_max_quest_task", 1) == 1)
    check("Lukash while the job runs: 'told you to talk to Max'", talk("mil_soc_lukash_dialog", A) == ["2001"])
    check("Max before the report: asks the farmstead", talk("mil_soc_max_dialog", A, ["1200", "1220"])[:3] == ["1001", "1200", "1201"])
    check("Max gave the report flag", flag(M.MAXF))
    step()
    check("report task closed, 'Destroy the Duty squad' given to all",
          all(given("mil_start_kill_skull_quest_task", i) == 1 for i in (1, 2, 3)))
    check("the eight single 'kill the Duty' tasks are never given", all(given("mil_start_kill_the_duty_%d_quest_task" % i, 1) == 0 for i in range(1, 9)))
    check("Max while the counterattack runs: 'we'll talk after'", talk("mil_soc_max_dialog", A) == ["10001", "10002"])
    for f in M.DUTY_DEAD[:-1]:
        give(f)
    step()
    check("eight of nine squads dead: still no 'Return to Lukash', no DD", given("mil_soc_return_lukash_task", 1) == 0 and not flag(M.DD))
    give(M.DUTY_DEAD[-1])
    step()
    check("whole Duty group dead: DD set, 'Return to Lukash' given to all", flag(M.DD) and all(given("mil_soc_return_lukash_task", i) == 1 for i in (1, 2, 3)))
    check("Max after the fight: report to Lukash first", talk("mil_soc_max_dialog", A)[0] == "9100")
    v = talk("mil_soc_lukash_dialog", A, ["7004"])
    check("Lukash report: assignment complete, Barrier job accepted", v == ["3001", "3002", "7003", "7004"], v)
    check("flags DONE and BP", flag(M.DONE) and flag(M.BP))
    step()
    check("Barrier job step 1 'Talk to Barrier outpost commander' given to all", all(given("mil_start_talk_to_the_cap_quest_task", i) == 1 for i in (1, 2, 3)))
    check("Max after the report: his mod greeting", talk("mil_soc_max_dialog", A) == ["31"])
    check("Lukash during the Barrier job: 'go to the Barrier'", talk("mil_soc_lukash_dialog", A) == ["9001"])
    check("Cap lore dialog is a plain actor dialog", talk("mil_soc_cap_lore_dialog", A)[:2] == ["0", "1"])
    v = talk("mil_soc_cap_dialog", A)
    check("Cap job offer", v == ["4003", "1004", "1005"], v)
    check("Cap flag set", flag(M.CP))
    step()
    check("Barrier step 2 'help destroy the Monolith squad' given", all(given("mil_start_protect_the_barrier_quest_task", i) == 1 for i in (1, 2, 3)))
    check("Cap while the attack runs", talk("mil_soc_cap_dialog", A) == ["2001"])
    check("Lukash does not pay before the Monolith squad is dead", talk("mil_soc_lukash_dialog", A) == ["9001"])
    give(M.MD)
    step()
    check("Barrier step 3 'Talk to Barrier outpost commander' (reward) given", all(given("mil_soc_cap_reward_task", i) == 1 for i in (1, 2, 3)))
    E["__npc_money"] = 3001
    v = talk("mil_soc_cap_dialog", B)
    check("Cap reward talk", v == ["3001", "3002", "3003"], v)
    check("Cap paid half of his purse to the talking player only", money("bob") == 1500 and money("alice") == 0, (money("bob"), money("alice")))
    check("flag CR", flag(M.CR))
    check("Cap afterwards: good luck", talk("mil_soc_cap_dialog", A) == ["3003"])
    v = talk("mil_soc_lukash_dialog", A)
    check("Lukash pays for the Barrier", v == ["10001"], v)
    check("Lukash payment 4000 to the talking player", money("alice") == 4000, money("alice"))
    check("flag END and Lukash has no more work", flag(M.END) and talk("mil_soc_lukash_dialog", A) == ["6001"])
    check("Lukash paid once", money("alice") == 4000)

    # --------------------------------------------------------------------------------------------
    # 3. Duty route: Skull -> sniper -> pay -> assault -> snipers (3) -> Lukash -> fee
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice")
    B = player(2, "bob")
    step()
    v = talk("mil_soc_skull_dialog", A, ["101", "103", "105"])
    check("Skull first talk: join, go on, I'll try", v == ["100", "101", "102", "103", "104", "105", "1051"], v)
    check("Skull job flags (both of the mod)", flag(M.SJ1) and flag(M.SJ2))
    step()
    check("kill the tower sniper: given to both", given("mil_start_kill_the_sniper_on_the_tower_quest_task", 1) == 1 and given("mil_start_kill_the_sniper_on_the_tower_quest_task", 2) == 1)
    check("Skull while the sniper lives", talk("mil_soc_skull_dialog", A) == ["300"])
    give(M.SD)
    step()
    check("return to Skull: given to both", given("mil_start_talk_to_skull_about_the_assault_quest_task", 1) == 1 and given("mil_start_talk_to_skull_about_the_assault_quest_task", 2) == 1)
    v = talk("mil_soc_skull_dialog", A, ["401"])
    check("Skull pays and offers the assault", v == ["400", "450", "451", "401", "402", "403"], v)
    check("sniper payment 4000", money("alice") == 4000, money("alice"))
    check("assault flags", flag(M.ST) and flag(M.KEY))
    step()
    for i in (1, 2, 3):
        check("sniper %d given to both" % i, given("mil_start_kill_the_snipers_%d_quest_task" % i, 1) == 1 and given("mil_start_kill_the_snipers_%d_quest_task" % i, 2) == 1)
    check("only three snipers (the fourth is never given)", given("mil_start_kill_the_snipers_4_quest_task", 1) == 0)
    check("kill Lukash given to both", given("mil_start_kill_lukash_quest_task", 1) == 1 and given("mil_start_kill_lukash_quest_task", 2) == 1)
    check("fee step not yet", given("mil_soc_duty_fee_task", 1) == 0)
    check("Skull during the assault", talk("mil_soc_skull_dialog", A) == ["601"])
    give(M.LD)
    step()
    check("Lukash dead: fee step 'Return to the Duty farmstead' given", given("mil_soc_duty_fee_task", 1) == 1 and given("mil_soc_duty_fee_task", 2) == 1)
    v = talk("mil_soc_skull_dialog", B)
    check("Skull gives the reward", v == ["200", "201"], v)
    check("fee 8000 to the talking player", money("bob") == 8000, money("bob"))
    check("flag FEE and Skull is done", flag(M.FEE) and talk("mil_soc_skull_dialog", A) == ["701"])
    # the SoC payment 1 is shared: Lukash does not pay the same player twice
    give(M.BP, M.MD)
    v = talk("mil_soc_lukash_dialog", A)
    check("Lukash 10001 after the Duty payment: no second 4000 for the same player", money("alice") == 4000, money("alice"))

    # --------------------------------------------------------------------------------------------
    # 4. no soft-locks
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice")
    give(M.LK)
    force_dead("mil_smart_terrain_15_freedom_max")
    step()
    check("Max dead before the report: the report flag is given", flag(M.MAXF))
    reset()
    A = player(1, "alice")
    give(M.LK, M.MAXF, M.LD)
    step()
    check("Lukash dead: the job can be finished (DONE)", flag(M.DONE))
    reset()
    A = player(1, "alice")
    give(M.BP)
    force_dead("mil_smart_terrain_12_1_freedom_cap")
    step()
    check("Cap dead: his talk step is done (CP)", flag(M.CP))
    give(M.MD)
    step()
    check("Cap dead after the fight: his reward step is done (CR)", flag(M.CR))
    reset()
    A = player(1, "alice")
    give(M.SJ1, M.SJ2, M.SD, M.SKULL_DEAD)
    step()
    check("Skull dead: 'Return to Skull' is done (ST)", flag(M.ST))
    give(M.KEY, M.LD)
    step()
    check("Skull dead: the fee step is done (FEE)", flag(M.FEE))
    reset()
    A = player(1, "alice")
    give(M.LK)
    for f in M.DUTY_DEAD:
        give(f)
    step()
    check("Duty dead before Max: 'Return to Lukash' is given anyway", given("mil_soc_return_lukash_task", 1) == 1 and given("mil_start_report_to_max_quest_task", 1) == 0)
    reset()
    A = player(1, "alice")
    for f in M.DUTY_DEAD:
        give(f)
    step()
    v = talk("mil_soc_lukash_dialog", A, ["1200"])
    check("Lukash 'I've already dealt with them': the Barrier job follows", v == ["1001", "1200", "1210", "1221", "7003", "7004"], v)
    check("DONE set by that talk", flag(M.DONE))
    dxml = open(os.path.join(REPO, "patches", "freedom_duty", "gamedata", "configs", "gameplay", "dialogs_coop_l07_military.xml"), "rb").read().decode("cp1251")
    offer = re.search(r'<dialog id="mil_smart_terrain_15_freedom_max_flash_offer_dialog">(.*?)<phrase_list>', dxml, re.S).group(1)
    check("Max flash drive offer is gated on the report to Lukash (DONE) only", re.findall(r"<has_flag>([^<]*)</has_flag>", offer) == [M.DONE], offer)

    # dead player gets the task when alive again; a respawned player gets open tasks
    reset()
    A = player(1, "alice")
    give(M.LK)
    A["__alive"] = False
    step()
    check("dead player: not given", given("mil_start_report_to_max_quest_task", 1) == 0)
    A["__alive"] = True
    step()
    check("respawned player: given", given("mil_start_report_to_max_quest_task", 1) == 1)

    # Barkeep sent the player to the Radar: the Radar task still comes (the removed Military step used to give it)
    reset()
    A = player(1, "alice")
    give(M.RADIO)
    step()
    check("Radar task fallback", given("rad_start_go_to_radar_quest_task", 1) == 1)

    # a talk that is cut off after the accepting phrase keeps the flags (flag in the same phrase)
    reset()
    A = player(1, "alice")
    E["__me"] = A
    give(M.LK)
    check("Lukash accepting phrase carries the flag (11011)", M.LK in [f for p in M.DIALOGS["lu"]["phrases"] if p[0] == "11011" for f in p[4]])
    check("Cap job flag in 1004", M.CP in [f for p in M.DIALOGS["cp"]["phrases"] if p[0] == "1004" for f in p[4]])
    check("Skull assault flags in 401 / 411", all(f in [x for p in M.DIALOGS["sk"]["phrases"] if p[0] == "401" for x in p[4]] for f in (M.ST, M.KEY)))

    # the hand-out is real: tasks of the stages exist as sections in the effective tm file
    tm = open(os.path.join(REPO, "patches", "freedom_duty", "gamedata", "configs", "misc", "tm_coop_l07_military.ltx"), "rb").read().decode("cp1251")
    sections = set(re.findall(r"^\[([^\]]+)\]", tm, re.M))
    stage_ids = re.findall(r'\{ id = "([^"]+)"', open(os.path.join(scripts, "coop_soc_mil.script"), encoding="utf-8").read())
    missing = [s for s in stage_ids if s not in sections and not s.startswith("rad_")]
    check("every stage task has a section in tm_coop_l07_military.ltx", not missing, missing)

    # Duty assault: the SoC effect mil_bomb_explode (chemical_burn hit on the bomb, then on the wall objects)
    sr = open(os.path.join(PATCH, "gamedata", "configs", "scripts", "coop_l07_military", "space_restrictors",
                           "mil_explosive_dinamit_space_restrictor.ltx"), "rb").read().decode("latin1")
    check("restrictor calls =mil_bomb_explode before the BOOM flag, no hit_obj", "=mil_bomb_explode +MIL_EXPLOSIVE_DINAMIT_BOOM_SPACE_RESTRICTOR_INFO" in sr and "hit_obj" not in sr)
    mil["install"]()
    check("install registers xr_effects.mil_bomb_explode", E["xr_effects"]["mil_bomb_explode"] is not None)
    for n in ("mil_explosive_dinamit_1", "mil_military_wall_brick", "mil_military_wall_brick_in"):
        E["__mkobj"](n)
    E["__time"] = 1000
    E["xr_effects"]["mil_bomb_explode"](None, None, None)
    hits = [(h["name"], h["power"], h["type"]) for h in E["__hits"].values()]
    check("bomb gets one chemical_burn hit of power 1000000", hits == [("mil_explosive_dinamit_1", 1000000, 7)], hits)
    c2 = list(E["__calls2"].values())[-1]
    check("walls wait for the delay", not c2[1]())
    E["__time"] = 1500
    check("walls hit after the delay", c2[1]())
    c2[2]()
    hits = [(h["name"], h["type"]) for h in E["__hits"].values()]
    check("both wall objects get chemical_burn", hits[1:] == [("mil_military_wall_brick", 7), ("mil_military_wall_brick_in", 7)], hits)
    E["xr_effects"]["mil_bomb_explode"](None, None, None)
    check("second call within 20 s does nothing", len(list(E["__hits"].values())) == 3)
    E["__time"] = 30000
    E["__hits"] = lua.table_from({})
    E["__objs"]["mil_explosive_dinamit_1"] = None
    E["xr_effects"]["mil_bomb_explode"](None, None, None)
    c3 = list(E["__calls2"].values())[-1]
    E["__time"] = 31000
    c3[2]()
    hits = [h["name"] for h in E["__hits"].values()]
    check("bomb missing: the walls are still hit, nothing crashes", hits == ["mil_military_wall_brick", "mil_military_wall_brick_in"], hits)

    print()
    print("ALL PASS" if fails == 0 else "FAILED: %d" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
