"""Offline check (no game) of the Bar Duty / Freedom line of patch soc_bar_duty_line.
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL scripts (coop_soc_duty.script, coop_soc_duty_say.script) in a Lua 5.1 VM with a small engine mock (story flags, players with
inventories and money, alife():create, story objects, task hand-out) and plays the REAL dialogs (gamedata\\configs\\gameplay\\dialogs_coop_soc_duty.xml):
the phrase graph is walked like the engine does it (hidden phrases pick the first state whose precondition holds, actor choices are filtered by their
preconditions, actions and flags run)."""
import os
import random
import sys
import xml.etree.ElementTree as ET

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PATCH, "tools"))
import duty_model as M

fails = 0
npass = 0


def check(name, ok, info=""):
    global fails, npass
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if ok:
        npass += 1
    else:
        fails += 1


PRELUDE = r'''
local duty_path, say_path = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}
E.__calls = {}
E.__client = false
E.__me = nil
E.__lvl = "coop_l05_bar"
E.__created = {}
E.__next_id = 1000
E.__relations = {}
E.__spent = {}
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

-- vectors, level, game graph
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z return self end
function V:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
E.__no_node = false
E.level = { name = function() return E.__lvl end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end,
	vertex_id = function(p) if E.__no_node then return 4294967295 end E.__lastpos = E.vector():set(p.x, p.y, p.z) return 5000 + math.floor(p.x) end,
	vertex_position = function(lv) return E.__lastpos or E.vector() end,
	object_by_id = function(id) return E.__online[id] end }
E.__online = {}
E.game_object = { enemy = 2, friend = 0 }
function E.game_graph()
	return { vertex = function(self, i) return { level_id = function() return 7 end, level_point = function() return E.vector():set(i, 0, 0) end } end,
		valid_vertex_id = function(self, i) return i < 400 end }
end
-- alife
local stories = {}
local ents = {}
E.__ents = ents
E.__stories = stories
local function mkse(section, pos, lv, gv, parent)
	E.__next_id = E.__next_id + 1
	local se = { id = E.__next_id, section = section, position = pos, m_level_vertex_id = lv, m_game_vertex_id = gv, parent = parent, __alive = true }
	function se:alive() return self.__alive end
	function se:section_name() return self.section end
	ents[se.id] = se
	if E.__section_story and E.__section_story[section] then stories[E.__section_story[section]] = se.id end
	E.__created[#E.__created + 1] = se
	if parent ~= nil and E.__holder and E.__holder[parent] then E.__holder[parent].__inv[section] = se end
	return se
end
E.__holder = {}
function E.__clear() for k in pairs(stories) do stories[k] = nil end for k in pairs(ents) do ents[k] = nil end end
function E.alife()
	return { create = function(self, section, pos, lv, gv, parent) return mkse(section, pos, lv, gv, parent) end,
		object = function(self, id) return ents[id] end }
end
function E.get_story_object_id(s) return stories[s] end
function E.add_story_object(id, s) stories[s] = id end
function E.unregister_story_id(s) stories[s] = nil end
E.db = { mp_actors = {}, storage = {}, spawned_vertex_by_id = {} }
function E.__player(id, name, lv, gv)
	local o = { __id = id, __name = name, __alive = true, __inv = {}, __money = 0, __pos = E.vector():set(10, 0, 10), __lv = lv or 777, __gv = gv or 55 }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:level_vertex_id() return self.__lv end
	function o:game_vertex_id() return self.__gv end
	function o:object(sec) local it = self.__inv[sec]; if it ~= nil and ents[it.id] == nil then self.__inv[sec] = nil; return nil end return it end
	function o:money() return self.__money end
	E.db.mp_actors[id] = o
	E.__holder[id] = o
	return o
end
function E.getLocalActor() return E.__me end
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
E.__npc = { __id = 90001 }
function E.__npc:id() return self.__id end
E.__pay = {}
E.dialogs = {
	who_is_npc = function(a, b) if a == E.__npc then return a, b end return b, a end,
	relocate_money_to_actor = function(a, b, n) local me = E.__me:name(); E.__pay[me] = (E.__pay[me] or 0) + n; E.__me.__money = E.__me.__money + n end,
	relocate_money = function(victim, n, t) E.__me.__money = E.__me.__money - n; E.__spent[#E.__spent + 1] = n end,
	relocate_item_section_from_actor = function(a, b, sec)
		local it = E.__me.__inv[sec]
		if it ~= nil then ents[it.id] = nil; E.__me.__inv[sec] = nil end
	end,
	relocate_item_section_to_actor = function(a, b, sec, n)
		local se = mkse(sec, E.__me.__pos, 1, 1, E.__me:id())
		E.__me.__inv[sec] = se
	end,
	actor_set_dolg = function(a, b) E.__dolg = (E.__dolg or 0) + 1 end,
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
E.coop_soc_duty = load(duty_path, "coop_soc_duty")
E.coop_soc_duty_say = load(say_path, "coop_soc_duty_say")
return E
'''


def load_dialogs():
    path = os.path.join(PATCH, "gamedata", "configs", "gameplay", "dialogs_coop_soc_duty.xml")
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
        out[d.get("id")] = dict(phrases=ph, pre=[x.text.strip() for x in d.findall("precondition")])
    return out


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    scripts = os.path.join(PATCH, "gamedata", "scripts")
    E = lua.execute(PRELUDE, os.path.join(scripts, "coop_soc_duty.script"), os.path.join(scripts, "coop_soc_duty_say.script"))
    duty = E["coop_soc_duty"]
    say = E["coop_soc_duty_say"]
    DLG = load_dialogs()
    npc = E["__npc"]
    # the engine registers the story_id of the spawn section: read it from the generated spawn sections
    story = {}
    cur = None
    sp = os.path.join(PATCH, "gamedata", "configs", "creatures", "spawn_sections_coop_l06_rostok.ltx")
    for line in open(sp, encoding="ascii").read().splitlines():
        line = line.strip()
        if line.startswith("[") and "]" in line:
            cur = line[1:line.index("]")]
        elif line.startswith("story_id") and cur:
            story[cur] = line.split("=", 1)[1].strip()
    E["__section_story"] = lua.table_from(story)
    G = lua.globals()

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(*ns):
        for n in ns:
            E["story_flags"]["give_flag"](n)

    def reset():
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__pay"] = lua.table_from({})
        E["__spent"] = lua.table_from({})
        E["__clear"]()
        E["__online"] = lua.table_from({})
        E["__holder"] = lua.table_from({})
        E["__created"] = lua.table_from({})
        E["__lvl"] = "coop_l05_bar"
        E["__no_node"] = False
        E["__dolg"] = 0
        E["SOCDUTY_FORCE_DEAD"] = None
        E["__client"] = False
        duty["reset_given"]()

    def player(pid, name=None, money=0):
        p = E["__player"](pid, name or "p%d" % pid)
        p["__money"] = money
        return p

    def step():
        E["__client"] = False
        E["__time"] = E["__time"] + 1000
        return duty["step"]()

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def force_dead(*stories):
        E["SOCDUTY_FORCE_DEAD"] = lua.table_from({s: True for s in stories})

    def created(section=None):
        out = []
        for i in range(1, int(len(E["__created"])) + 1):
            se = E["__created"][i]
            if section is None or se["section"] == section:
                out.append(se)
        return out

    def has_item(p, sec):
        return p["object"](p, sec) is not None

    def give_item(p, sec):
        se = lua.eval("function(E, pid, sec) return E.alife():create(sec, E.vector():set(0,0,0), 1, 1, pid) end")(E, p["id"](p), sec)
        return se

    def call(modname, fn, a, b):
        m = {"coop_soc_duty": duty, "coop_soc_duty_say": say}.get(modname)
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
        Returns None when the dialog is not offered (its dialog-level precondition fails)."""
        E["__me"] = me
        E["__client"] = True
        D = DLG[dlg]
        ph = D["phrases"]
        for pre in D["pre"]:
            mod, fn = pre.split(".")
            if not call(mod, fn, npc, me):
                return None
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
                    if mod == "coop_soc_duty_say":
                        pass
            for f in q["flags"]:
                give(f)

        def expand(nexts):
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
            avail = expand(ph[choice]["nxt"])
        E["__client"] = False
        return visited

    # ============================================================================================
    # 0. static: every Lua function named in the dialogs exists; say_ function per phrase
    # ============================================================================================
    missing = []
    for did, D in DLG.items():
        for pid, q in D["phrases"].items():
            for x in q["pre"] + q["act"]:
                mod, fn = x.split(".")
                if mod == "dialogs":
                    continue
                m = {"coop_soc_duty": duty, "coop_soc_duty_say": say}[mod]
                if m[fn] is None:
                    missing.append(x)
        for x in D["pre"]:
            mod, fn = x.split(".")
            if duty[fn] is None:
                missing.append(x)
    check("every dialog function exists in the scripts", not missing, missing[:5])

    # ============================================================================================
    # 1. join Duty: the pass
    # ============================================================================================
    reset()
    p1 = player(1, "alpha", money=500)
    p2 = player(2, "beta", money=3000)
    check("gate: pass dialog offered before the pass", talk("bar_soc_ga_dialog", p1) is not None)
    v = talk("bar_soc_ga_dialog", p1, ["11", "12"])
    check("gate: poor player cannot pay (only 'changed my mind')", v == ["0", "1", "12", "121"], v)
    check("gate: no flag, no money taken", not flag(M.PASS) and p1["money"](p1) == 500)
    v = talk("bar_soc_ga_dialog", p2, ["11"])
    check("gate: paying: phrases", v == ["0", "1", "11", "111"], v)
    check("gate: flags pass + community start + leader", flag(M.PASS) and flag(M.CSTART) and flag(M.CLEAD))
    check("gate: 1000 taken from the paying player", p2["money"](p2) == 2000 and int(E["__spent"][1]) == 1000)
    check("gate: dialog gone after the pass", talk("bar_soc_ga_dialog", p2) is None)
    step()
    check("community task given to every player", given("bar_soc_dolg_community_task", 1) == 1 and given("bar_soc_dolg_community_task", 2) == 1)
    p3 = player(3, "late")
    step()
    check("community task: late joiner gets it once", given("bar_soc_dolg_community_task", 3) == 1)
    step(); step()
    check("community task: not given twice", given("bar_soc_dolg_community_task", 1) == 1 and given("bar_soc_dolg_community_task", 3) == 1)

    # greetings of the gate commander / Petrenko / Ivantsov follow the same three states
    reset(); p1 = player(1)
    v = talk("bar_soc_gc_dialog", p1)
    check("commander greeting without pass: 11", v == ["11"], v)
    give(M.PASS, M.CSTART)
    check("commander greeting with pass: 21", talk("bar_soc_gc_dialog", p1) == ["21"])
    check("Petrenko greeting with pass: 21", talk("bar_soc_pe_dialog", p1) == ["21"])
    give(M.OATH)
    check("commander greeting as member: 31", talk("bar_soc_gc_dialog", p1) == ["31"])
    check("Petrenko greeting as member: 31", talk("bar_soc_pe_dialog", p1) == ["31"])
    check("commander talk dialog: 4 phrases", talk("bar_soc_gt_dialog", p1) == ["0", "1", "2", "3"])

    # ============================================================================================
    # 2. Ivantsov's test: offer, accept, the Arena, report
    # ============================================================================================
    reset(); p1 = player(1); p2 = player(2)
    check("Ivantsov without pass: greeting 11 only", talk("bar_soc_iv_dialog", p1) == ["11"])
    give(M.PASS, M.CSTART)
    v = talk("bar_soc_iv_dialog", p1, ["I1", "I3"])
    check("Ivantsov with pass: greeting, offer, accept", v == ["21", "I1", "I2", "I3"], v)
    check("test accepted flag", flag(M.TSTART))
    step()
    check("test task given to every player", given("bar_soc_dolg_test_task", 1) == 1 and given("bar_soc_dolg_test_task", 2) == 1)
    v = talk("bar_soc_iv_dialog", p1)
    check("Ivantsov while the test runs: greeting only (no report before the fight)", v == ["21"], v)
    # the Arena pulse: set and cleared by the arena restrictor; the frame poll latches it
    give("BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_SQUAD_DEAD")
    duty["arena_poll"]() if duty["arena_poll"] is not None else step()
    E["story_flags"]["disable_flag"]("BAR_ARNY_ARENA_SMART_TERRAIN_PSEUDODOG_SQUAD_DEAD")
    step()
    check("the Arena fight is latched even when the pulse is gone", flag(M.ARENA))
    v = talk("bar_soc_iv_dialog", p1, ["I5"])
    check("Ivantsov report: reference given", v == ["21", "I5", "I6"] and flag(M.TDONE), v)
    step()

    # ============================================================================================
    # 3. Voronin: the Bulldog 6 job, the hand-in, the oath
    # ============================================================================================
    reset(); p1 = player(1, "alpha"); p2 = player(2, "beta")
    check("Voronin hub greeting: 11", talk("bar_soc_vo_dialog", p1) == ["11"])
    v = talk("bar_soc_vj_dialog", p1, ["1111"])
    check("Voronin job accepted: SoC phrases", v == ["0", "1", "11", "111", "1111", "11111"], v)
    check("Voronin job flag", flag(M.RSTART))
    check("Voronin job dialog gone once accepted", talk("bar_soc_vj_dialog", p1) is None)
    E["__lvl"] = "coop_l05_bar"
    step()
    check("rg6 task given to every player", given("bar_soc_rg6_task", 1) == 1 and given("bar_soc_rg6_task", 2) == 1)
    check("community task opens with the Bulldog 6 job", given("bar_soc_dolg_community_task", 1) == 1)
    check("rg6 not created on the Bar level", len(created("wpn_rg-6")) == 0)
    E["__lvl"] = "coop_l07_military"
    step(); step()
    rg = created("wpn_rg-6")
    check("rg6 created once at the stash on the Army Warehouses", len(rg) == 1, len(rg))
    check("rg6 has the SoC position", abs(rg[0]["position"]["x"] - (-274.55)) < 0.01 and abs(rg[0]["position"]["z"] - 245.41) < 0.01)
    check("rg6 story id registered (map marker)", E["get_story_object_id"](M.RG6_STORY) is not None)
    check("RGAIN not set before somebody picks it up", not flag(M.RGAIN))
    give_item(p2, "wpn_rg-6")
    step()
    check("RGAIN when a player holds the Bulldog 6", flag(M.RGAIN))
    E["__lvl"] = "coop_l05_bar"
    # hand-in through the greeting (SoC bar_dolg_leader_start 31 / 311 / 3111)
    check("Voronin greeting for a player without the rifle: hub (11)", talk("bar_soc_vo_dialog", p1) == ["11"])
    v = talk("bar_soc_vo_dialog", p2)
    check("Voronin greeting with the rifle: 31 / 311 / 3111", v == ["31", "311", "3111"], v)
    check("rg6 taken, outfit given, done flag", flag(M.RDONE) and not has_item(p2, "wpn_rg-6") and has_item(p2, M.__dict__.get("OUTFIT", "dolg_scientific_outfit")))
    step()
    # the oath needs Ivantsov's reference
    check("Voronin: 41 greeting after the rifle", talk("bar_soc_vo_dialog", p2) == ["41"])
    check("oath not offered without the reference", talk("bar_soc_vp_dialog", p2) is None)
    give(M.TDONE)
    v = talk("bar_soc_vp_dialog", p2)
    check("oath: nine SoC phrases", v == ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"] or v == ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"][:len(v)] and len(v) == 10, v)
    check("oath flag and the Duty community call", flag(M.OATH) and int(E["__dolg"]) == 1)
    check("Voronin greeting as member: 21", talk("bar_soc_vo_dialog", p2) == ["21"])
    check("Voronin job dialog (What can I do for Duty?)", talk("bar_soc_vb_dialog", p2) == ["0", "1"])
    step()

    # the actor-dialog hand-in (SoC bar_dolg_leader_quest_rg6_finish)
    reset(); p1 = player(1)
    give(M.RSTART)
    check("hand-in dialog needs the rifle", talk("bar_soc_vr_dialog", p1) is None)
    give_item(p1, "wpn_rg-6")
    v = talk("bar_soc_vr_dialog", p1)
    check("hand-in dialog: rifle taken, flag, outfit", v == ["0", "1"] and flag(M.RDONE) and has_item(p1, "dolg_scientific_outfit") and not has_item(p1, "wpn_rg-6"), v)

    # ============================================================================================
    # 4. soft-lock rules
    # ============================================================================================
    reset(); p1 = player(1); p2 = player(2)
    give(M.RSTART)
    E["__lvl"] = "coop_l07_military"
    step(); step()
    se = created("wpn_rg-6")[0]
    h = give_item(p2, "wpn_rg-6")
    step()
    check("rifle held: RGAIN", flag(M.RGAIN))
    # the holder dies with it and it is destroyed: nobody holds it, the party took it once
    E["__ents"][h["id"]] = None
    E["__ents"][se["id"]] = None
    E["__stories"][M.RG6_STORY] = None
    p2["__alive"] = False
    E["__lvl"] = "coop_l05_bar"
    n0 = len(created("wpn_rg-6"))
    step(); step()
    check("lost rifle: a replacement is made next to a living player", len(created("wpn_rg-6")) == n0 + 1, (n0, len(created("wpn_rg-6"))))
    step(); step()
    check("replacement made only once", len(created("wpn_rg-6")) == n0 + 1)
    # the hand-in is open to the talker when the party took the rifle and nobody carries it
    E["__ents"][created("wpn_rg-6")[-1]["id"]] = None
    E["__stories"][M.RG6_STORY] = None
    check("hand-in open when the rifle is gone (RGAIN, nobody holds it)", talk("bar_soc_vr_dialog", p1) == ["0", "1"])

    # dead NPCs never block
    reset(); p1 = player(1)
    give(M.RSTART)
    force_dead(M.NPC["commander"])
    step()
    check("gate commander dead: the pass is given", flag(M.PASS) and flag(M.CSTART))
    reset(); p1 = player(1)
    give(M.CSTART)
    force_dead(M.NPC["ivancov"])
    step()
    check("Ivantsov dead: the reference is given", flag(M.TDONE))
    reset(); p1 = player(1)
    give(M.RSTART, M.KSTART)
    force_dead(M.NPC["voronin"])
    step()
    check("Voronin dead: the oath and the report are done", flag(M.OATH) and flag(M.RDONE) and flag(M.KDONE))
    step()
    check("Voronin dead: no task left open", given("bar_soc_rg6_task", 1) == 0 or flag(M.RDONE))

    # ============================================================================================
    # 5. the Barkeep jobs: Lucky and the veterans, Tyran and the Mercs
    # ============================================================================================
    reset(); p1 = player(1, "alpha", money=0); p2 = player(2, "beta")
    check("Barkeep jobs closed before the Agroprom hand-in", talk("bar_soc_bj_dialog", p1) is None)
    give(M.AGR_DONE)
    v = talk("bar_soc_bj_dialog", p1, ["32112"])
    check("veterans job offered and accepted", v == ["0", "321", "3211", "32111", "32112", "321121"] and flag(M.VSTART), v)
    v = talk("bar_soc_bj_dialog", p1)
    check("while the veterans job runs: 271", v == ["0", "271"], v)
    E["__lvl"] = "coop_l06_rostok"
    step(); step()
    for sec in ("soc_vet_lucky", "soc_vet_1", "soc_vet_2"):
        check("%s created on the Wild Territory" % sec, len(created(sec)) == 1, len(created(sec)))
    check("Lucky has the SoC story id", E["get_story_object_id"](M.NPC["lucky"]) is not None)
    check("Tyran not created before his job", len(created("soc_tyran")) == 0)
    step(); step()
    check("NPCs created only once", len(created("soc_vet_lucky")) == 1)
    check("veterans task given to every player", given("bar_soc_veterans_task", 1) == 1 and given("bar_soc_veterans_task", 2) == 1)
    # hostile relation on the online object
    lid = E["get_story_object_id"](M.NPC["lucky"])
    lua.eval("function(E, id) local o = {} function o:alive() return true end function o:set_relation(r, who) E.__relations[#E.__relations + 1] = r .. ':' .. who:id() end E.__online[id] = o end")(E, lid)
    E["__time"] = E["__time"] + 6000
    step()
    rels = sorted(E["__relations"][i] for i in range(1, int(len(E["__relations"])) + 1))
    check("hostile NPC: enemy relation (2) set to every player", rels == ["2:1", "2:2"], rels)
    # Lucky dies
    E["__ents"][lid]["__alive"] = False
    step(); step()
    check("Lucky dead: flag", flag(M.VKILLED))
    pdas = created("bar_lucky_pda")
    check("Lucky's PDA made once at his body", len(pdas) == 1, len(pdas))
    step(); step()
    check("PDA not made twice", len(created("bar_lucky_pda")) == 1)
    check("Barkeep hand-in not offered without the PDA while it lies there", talk("bar_soc_bv_dialog", p1) is None)
    give_item(p1, "bar_lucky_pda")
    step()
    p1["__money"] = 0
    v = talk("bar_soc_bv_dialog", p1)
    check("Lucky's PDA hand-in: phrases", v == ["0", "1", "11", "111"], v)
    check("PDA taken, 5000 paid, done flag", flag(M.VDONE) and not has_item(p1, "bar_lucky_pda") and p1["money"](p1) == M.PAY_LUCKY)
    step()
    v = talk("bar_soc_bj_dialog", p1, ["3312"])
    check("Tyran job offered after the veterans and accepted", v == ["0", "331", "3312", "33121"] and flag(M.ASTART), v)
    E["__lvl"] = "coop_l06_rostok"
    step(); step()
    for sec in ("soc_tyran", "soc_merc_1", "soc_merc_2", "soc_merc_3", "soc_merc_4"):
        check("%s created while the Tyran job is open" % sec, len(created(sec)) == 1, len(created(sec)))
    check("Tyran task given to every player", given("bar_soc_ambush_task", 1) == 1 and given("bar_soc_ambush_task", 2) == 1)
    tid = E["get_story_object_id"](M.NPC["tyran"])
    E["__ents"][tid]["__alive"] = False
    step(); step()
    check("Tyran dead: flag and PDA", flag(M.AKILLED) and len(created("bar_tiran_pda")) == 1)
    give_item(p2, "bar_tiran_pda")
    step()
    v = talk("bar_soc_ba_dialog", p2)
    check("Tyran PDA hand-in: phrases, 8000", v == ["0", "1", "2", "3"] and flag(M.ADONE) and p2["money"](p2) == M.PAY_TYRAN, v)
    step()
    v = talk("bar_soc_bj_dialog", p1)
    check("Barkeep: nothing more after both jobs (311)", v == ["0", "311"], v)

    # leader creation fails 3 times: counts as dead, the PDA is made next to a player (no soft-lock)
    reset(); p1 = player(1)
    give(M.VSTART)
    E["__lvl"] = "coop_l06_rostok"
    E["__no_node"] = True
    for _ in range(5):
        step()
    check("Lucky cannot be created (no AI node): counted as dead", flag(M.VKILLED))
    step(); step()
    check("PDA made next to the player when Lucky never existed", len(created("bar_lucky_pda")) == 1)
    # the lost PDA is replaced
    pda = created("bar_lucky_pda")[0]
    E["__ents"][pda["id"]] = None
    E["__stories"]["soc_duty_lucky_pda"] = None
    step(); step()
    check("lost PDA replaced once", len(created("bar_lucky_pda")) == 2)


    # a player held Lucky's PDA once and died with it (item destroyed): the hand-in opens for the next player, no soft-lock
    reset(); p1 = player(1, "alpha"); p2 = player(2, "beta")
    give(M.AGR_DONE, M.VSTART, M.VKILLED)
    step(); step()
    h = give_item(p1, "bar_lucky_pda")
    step()
    check("PDA taken flag", flag("SOC_DUTY_LUCKY_PDA_TAKEN"))
    E["__ents"][h["id"]] = None
    p1["__alive"] = False
    v = talk("bar_soc_bv_dialog", p2)
    check("PDA lost with its holder: hand-in open to the other player", v == ["0", "1", "11", "111"] and flag(M.VDONE), v)

    # ============================================================================================
    # 6. Voronin's war with Freedom: Lukash
    # ============================================================================================
    reset(); p1 = player(1)
    give(M.OATH)
    check("member greeting 21 before the Tyran job is done", talk("bar_soc_vo_dialog", p1) == ["21"])
    give(M.ADONE)
    v = talk("bar_soc_vo_dialog", p1)
    check("after Tyran Voronin orders the Freedom leader's death: 51 gives the flag", v == ["51"] and flag(M.KSTART), v)
    step()
    check("leader task given", given("bar_soc_leader_task", 1) == 1)
    check("Voronin waits: 51 again", talk("bar_soc_vo_dialog", p1) == ["51"])
    force_dead(M.NPC["lukash"])
    step()
    check("Lukash dead: flag", flag(M.KKILLED))
    v = talk("bar_soc_vo_dialog", p1)
    check("Voronin praises: 81, done flag", v == ["81"] and flag(M.KDONE), v)
    check("Voronin afterwards: 811", talk("bar_soc_vo_dialog", p1) == ["811"])
    reset(); p1 = player(1)
    give(M.KSTART, M.LUKASH_DEAD)
    step()
    check("Lukash dead flag of the Army Warehouses counts", flag(M.KKILLED))

    # ============================================================================================
    # 7. states exclude each other (random flag combinations)
    # ============================================================================================
    reset(); p1 = player(1)
    allflags = [M.PASS, M.CSTART, M.TSTART, M.ARENA, M.TDONE, M.RSTART, M.RGAIN, M.RDONE, M.OATH, M.KSTART, M.KKILLED, M.KDONE, M.VSTART, M.VDONE,
                M.ASTART, M.ADONE, M.AGR_DONE]
    rnd = random.Random(7)
    bad = []
    for n in range(2000):
        E["__reset_flags"]()
        for f in allflags:
            if rnd.random() < 0.4:
                give(f)
        E["__client"] = True
        E["__me"] = p1
        vo = [x for x in ("kdone", "kkilled", "kwait", "koffer", "member", "oath", "rg6", "hub") if duty["vo_st_" + x](npc, p1)]
        gc = [x for x in ("member", "pass", "default") if duty["gc_st_" + x](npc, p1)]
        bj = [x for x in ("vet_offer", "vet_busy", "amb_offer", "none") if duty["bj_" + x](npc, p1)]
        if len(vo) != 1 or len(gc) != 1 or len(bj) > 1:
            bad.append((vo, gc, bj))
    E["__client"] = False
    check("exactly one Voronin state and one gate state (2000 random flag sets), at most one Barkeep job state", not bad, bad[:2])
    # every combination ends with a way forward for the Barkeep: offer when nothing started
    E["__reset_flags"]()
    give(M.AGR_DONE)
    E["__client"] = True
    check("Barkeep job state with nothing started: veterans offer", duty["bj_vet_offer"](npc, p1))
    E["__client"] = False

    # ---- review: Lucky made earlier and released (no story id, no entity): counts as dead, no soft-lock
    reset(); p1 = player(1, "alpha"); player(2, "beta")
    give(M.AGR_DONE, M.VSTART)
    E["__lvl"] = "coop_l06_rostok"
    step(); step()
    lid2 = E["get_story_object_id"](M.NPC["lucky"])
    check("released Lucky: created first", lid2 is not None and flag("SOC_DUTY_NPC_LUCKY"))
    E["__ents"][lid2] = None
    E["__stories"][M.NPC["lucky"]] = None
    E["__time"] = E["__time"] + 6000
    step()
    check("released Lucky: counted as dead", flag(M.VKILLED))
    check("released Lucky: not created a second time", len(created("soc_vet_lucky")) == 1)

    # ============================================================================================
    # 7b. soc_mil_courier installed: it owns the Bulldog 6 job, this patch reads its done flag
    # ============================================================================================
    reset(); p1 = player(1, "alpha"); p2 = player(2, "beta")
    lua.execute("local E = ...; E.system_ini = function() return { section_exist = function(self, s) return s == 'mil_soc_cook' end } end", E)
    check("courier: Voronin job of this patch not offered", talk("bar_soc_vj_dialog", p1) is None)
    give(M.RSTART)
    E["__lvl"] = "coop_l07_military"
    step(); step()
    check("courier: no rifle created by this patch", len(created("wpn_rg-6")) == 0)
    check("courier: no rg6 task of this patch", given("bar_soc_rg6_task", 1) == 0)
    check("courier: no hand-in dialog of this patch", talk("bar_soc_vr_dialog", p1) is None)
    give("MIL_SOC_RG6_DONE")
    step()
    check("courier: its done flag is the Bulldog 6 step", flag(M.RDONE))
    lua.execute("local E = ...; E.system_ini = nil", E)
    reset(); p1 = player(1, "alpha")
    check("no courier: job of this patch offered again", talk("bar_soc_vj_dialog", p1) is not None)

    # ============================================================================================
    # 8. archive lines
    # ============================================================================================
    n_say = 0
    for did, D in DLG.items():
        for pid, q in D["phrases"].items():
            if q["text"]:
                n_say += 1
                if not any(a.startswith("coop_soc_duty_say.") for a in q["act"]):
                    check("say action on phrase %s/%s" % (did, pid), False)
    check("every spoken phrase has a PDA archive line (%d)" % n_say, True)

    print("\n%d checks passed, %d failed" % (npass, fails))
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
