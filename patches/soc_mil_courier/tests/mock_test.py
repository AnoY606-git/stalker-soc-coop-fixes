"""Offline check (no game) of patch soc_mil_courier: the snitch Pavlik (mil_courier_job) and the Bulldog 6 order (mil_freedom_rg6_task).

  python mock_test.py [--repo <repo root>]        (needs `pip install lupa`; the repo must have apply_shared.py applied)

Runs the REAL scripts (coop_soc_milc.script, coop_soc_milc_say.script and, for the Lukash states, coop_soc_mil.script of soc_mil_quests) in a
Lua 5.1 VM with an engine mock (story flags, players with positions, server entities with alife():create / object / alive, level, tasks,
sound) and plays the REAL dialogs of the effective level files (dialogs_coop_l07_military.xml of freedom_duty, dialogs_coop_l05_bar.xml
of quest_dialogs): the phrase graph is walked like the engine does it (hidden phrases pick the first state whose precondition holds, actor
choices are filtered by their preconditions, actions and flags run)."""
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.dirname(os.path.dirname(PATCH))
if "--repo" in sys.argv:
    REPO = os.path.abspath(sys.argv[sys.argv.index("--repo") + 1])
sys.path.insert(0, os.path.join(PATCH, "tools"))
import milc_model as M

fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local paths = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}
E.__calls = {}
E.__client = false
E.__dedicated = false
E.__money = {}
E.__items = {}
E.__sounds = {}
E.__me = nil
E.__level = "coop_l07_military"
E.__auto_story = true
E.__create_fail = false
E.__nodepos = {}
E.__logic_started = {}
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return not E.__client end
function E.OnClient() return E.__client end
function E.IsDedicatedServer() return E.__dedicated end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
-- vector
function E.vector()
	local v = { x = 0, y = 0, z = 0 }
	function v:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
	function v:distance_to(o) return math.sqrt((self.x - o.x) ^ 2 + (self.y - o.y) ^ 2 + (self.z - o.z) ^ 2) end
	return v
end
-- level
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end,
	vertex_id = function(pos) return 777 end,
	vertex_position = function(lv) return E.__nodepos[lv] or { x = 1e6, y = 0, z = 0 } end }
E.sound_object = { s2d = 1 }
setmetatable(E.sound_object, { __call = function(t, path)
	local so = { path = path }
	function so:play(obj, delay, kind) E.__sounds[#E.__sounds + 1] = path end
	return so
end })
E.__sections = nil
function E.system_ini() return { section_exist = function(self, s) return E.__sections == nil or E.__sections[s] == true end } end
function E.getFS() return { exist = function(self, root, p) return E.__files == nil or E.__files[p] == true end } end
E.game = { translate_string = function(id) return E.__probe or "Language" end }
function E.game_graph()
	return { vertex = function(self, i) return { level_id = function() return 1 end, level_point = function() return E.vector():set(i * 10, 0, 0) end } end,
		valid_vertex_id = function(self, i) return i < 5 end }
end
-- server objects
E.__objs = {}
E.__next_id = 100
E.__story = {}
E.__sec_story = {}
E.__alife = {}
function E.__alife:create(section, pos, lv, gv)
	if E.__create_fail then return nil end
	E.__next_id = E.__next_id + 1
	local se = { id = E.__next_id, section = section, position = E.vector():set(pos.x, pos.y, pos.z), lv = lv, gv = gv, __alive = true }
	function se:section_name() return self.section end
	function se:alive() return self.__alive end
	E.__objs[se.id] = se
	if E.__auto_story and E.__sec_story[section] then E.__story[E.__sec_story[section]] = se.id end
	E.__created = (E.__created or 0) + 1
	return se
end
function E.__alife:object(id) return E.__objs[id] end
function E.alife() return E.__alife end
function E.get_story_object_id(s) return E.__story[s] end
function E.add_story_object(id, s) E.__story[s] = id end
E.db = { mp_actors = {}, storage = {}, spawned_vertex_by_id = {} }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = { x = x or 0, y = y or 0, z = z or 0 }, __inv = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec) if (self.__inv[sec] or 0) > 0 then return { section = sec } end return nil end
	function o:iterate_inventory(fn, arg)
		for sec, n in pairs(self.__inv) do for i = 1, n do fn(nil, { section = function() return sec end }) end end
	end
	E.db.mp_actors[id] = o
	return o
end
function E.getLocalActor() return E.__me end
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
E.__npc = { money = function(self) return 1000 end }
function E.__me_inv(sec) local n = 0; if E.__me then n = E.__me.__inv[sec] or 0 end; return n end
E.dialogs = {
	who_is_npc = function(a, b) if a == E.__npc then return a, b end return b, a end,
	relocate_money_to_actor = function(a, b, n) local me = E.__me:name(); E.__money[me] = (E.__money[me] or 0) + n end,
	relocate_item_section_from_actor = function(a, b, sec, n) E.__me.__inv[sec] = (E.__me.__inv[sec] or 0) - (n or 1) end,
	relocate_item_section_to_actor = function(a, b, sec, n) E.__me.__inv[sec] = (E.__me.__inv[sec] or 0) + (n or 1); E.__items[E.__me:name() .. ":" .. sec] = (E.__items[E.__me:name() .. ":" .. sec] or 0) + 1 end,
	break_dialog = function() end,
}
E.modules = { stype_stalker = 0 }
E.ini_file = function(p) return { file = p } end
E.xr_logic = {
	configure_schemes = function(npc, ini, file, st, sec, g) return ini end,
	determine_section_to_activate = function(npc, ini, sec, actor) return "remark@x" end,
	activate_by_section = function(npc, ini, sect, g, loading) E.__logic_started[#E.__logic_started + 1] = ini.file end,
}
E.game_object = { enemy = 2 }
E.coop_soc_opening = { voice_lang = function() return E.__voice end }
E.__voice = "rus"
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
E.coop_soc_mil = load(paths.mil, "coop_soc_mil")
E.coop_soc_mil_say = load(paths.mil_say, "coop_soc_mil_say")
E.coop_soc_milc = load(paths.milc, "coop_soc_milc")
E.coop_soc_milc_say = load(paths.milc_say, "coop_soc_milc_say")
return E
'''


def load_dialogs(path):
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
                has=[x.text.strip() for x in p.findall("has_flag")],
                dont=[x.text.strip() for x in p.findall("dont_has_flag")],
                nxt=[x.text.strip() for x in p.findall("next")])
        out[d.get("id")] = dict(
            phrases=ph, has=[x.text.strip() for x in d.findall("has_flag")], dont=[x.text.strip() for x in d.findall("dont_has_flag")],
            pre=[x.text.strip() for x in d.findall("precondition")])
    return out


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    gd = os.path.join(REPO, "patches", "freedom_duty", "gamedata", "configs", "gameplay", "dialogs_coop_l07_military.xml")
    bd = os.path.join(REPO, "patches", "quest_dialogs", "gamedata", "configs", "gameplay", "dialogs_coop_l05_bar.xml")
    DLG = load_dialogs(gd)
    DLG.update(load_dialogs(bd))
    if "mil_soc_cook_common1" not in DLG or "mil_soc_dolg_leader_join" not in DLG:
        print("apply_shared.py is not applied to this repo: run patches\\soc_mil_courier\\tools\\apply_shared.py first")
        return 2
    scripts = os.path.join(PATCH, "gamedata", "scripts")
    paths = lua.table_from({"milc": os.path.join(scripts, "coop_soc_milc.script"), "milc_say": os.path.join(scripts, "coop_soc_milc_say.script"),
                            "mil": os.path.join(REPO, "patches", "soc_mil_quests", "gamedata", "scripts", "coop_soc_mil.script"),
                            "mil_say": os.path.join(REPO, "patches", "soc_mil_quests", "gamedata", "scripts", "coop_soc_mil_say.script")})
    E = lua.execute(PRELUDE, paths)
    milc = E["coop_soc_milc"]
    say = E["coop_soc_milc_say"]
    mil = E["coop_soc_mil"]
    mil_say = E["coop_soc_mil_say"]
    npc = E["__npc"]
    sys.path.insert(0, os.path.join(REPO, "patches", "soc_mil_quests", "tools"))
    import mil_model as MM

    # node positions of the model NPCs (the engine knows where its AI nodes are)
    nodepos = {}
    for k, n in M.NPCS.items():
        nodepos[n["lvid"]] = n["pos"]
    nodepos[M.RG6["lvid"]] = M.RG6["pos"]
    sec_story = {n["section"]: n["story"] for n in M.NPCS.values()}

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(*ns):
        for n in ns:
            E["story_flags"]["give_flag"](n)

    def vec(x, y, z):
        return lua.table_from({"x": x, "y": y, "z": z})

    def reset(level="coop_l07_military"):
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["db"]["storage"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__money"] = lua.table_from({})
        E["__items"] = lua.table_from({})
        E["__sounds"] = lua.table_from({})
        E["__objs"] = lua.table_from({})
        E["__story"] = lua.table_from({})
        E["__created"] = 0
        E["__next_id"] = 100
        E["__time"] = 0
        E["__level"] = level
        E["__client"] = False
        E["__dedicated"] = False
        E["__auto_story"] = True
        E["__create_fail"] = False
        E["__files"] = None
        E["__sections"] = None
        E["__voice"] = "rus"
        E["__logic_started"] = lua.table_from({})
        E["__nodepos"] = lua.table_from({k: vec(*v) for k, v in nodepos.items()})
        E["__sec_story"] = lua.table_from(sec_story)
        E["SOCMILC_FORCE_DEAD"] = None
        E["SOCMIL_FORCE_DEAD"] = None
        milc["reset_vm"]()
        milc["reset_client"]()
        mil["reset_given"]()

    def player(pid, name=None, pos=(-100.0, -16.0, 300.0)):
        return E["__player"](pid, name or "p%d" % pid, *pos)

    def at(p, x, y, z):
        p["__pos"] = vec(x, y, z)

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def money(name):
        v = E["__money"][name]
        return int(v) if v else 0

    def created():
        return int(E["__created"] or 0)

    def adv(ms):
        E["__time"] = E["__time"] + ms

    def step(ms=1000):
        adv(ms)
        E["__client"] = False
        return milc["step"]()

    def ent(story):
        sid = E["get_story_object_id"](story)
        return E["__objs"][sid] if sid is not None else None

    def move(story, x, y, z):
        e = ent(story)
        e["position"] = vec(x, y, z)

    def kill(story):
        ent(story)["__alive"] = False

    def run(ticks, ms=1000):
        for _ in range(ticks):
            step(ms)

    def call(modname, fn, a, b):
        m = {"coop_soc_mil": mil, "coop_soc_mil_say": mil_say, "coop_soc_milc": milc, "coop_soc_milc_say": say}.get(modname)
        if m is None:
            return None
        f = m[fn]
        if f is None:
            raise RuntimeError("missing Lua function %s.%s" % (modname, fn))
        return f(a, b)

    def talk(dlg, me, picks=(), maxn=80):
        """One talk of player `me` with an NPC: returns the visited phrase ids (phrases with text)."""
        E["__me"] = me
        E["__client"] = True
        dd = DLG[dlg]
        ph = dd["phrases"]
        picks = list(picks)
        visited = []

        def pre_ok(q):
            for pre in q["pre"]:
                mod, fn = pre.split(".")
                if not call(mod, fn, npc, me):
                    return False
            return all(flag(h) for h in q["has"]) and not any(flag(h) for h in q["dont"])

        def run_ph(pid):
            q = ph[pid]
            for a in q["act"]:
                mod, fn = a.split(".")
                if mod != "dialogs":
                    call(mod, fn, npc, me)
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
                        run_ph(n)
                        out += sub
                else:
                    out.append(n)
            return out

        # dialog-level gate (an actor dialog is offered only when it holds)
        for pre in dd["pre"]:
            mod, fn = pre.split(".")
            if not call(mod, fn, npc, me):
                E["__client"] = False
                return None
        if not all(flag(h) for h in dd["has"]) or any(flag(h) for h in dd["dont"]):
            E["__client"] = False
            return None
        avail = expand(["0"])
        for _ in range(maxn):
            if not avail:
                break
            choice = next((pk for pk in picks if pk in avail), avail[0])
            run_ph(choice)
            visited.append(choice)
            q = ph[choice]
            if not q["nxt"] or "dialogs.break_dialog" in q["act"]:
                break
            avail = expand(q["nxt"])
        E["__client"] = False
        return visited

    def tasks_opened():
        return [s["id"] for s in milc["STAGES"].values() if s["open"]()]

    # --------------------------------------------------------------------------------------------
    # 0. the XML matches the model; every Lua function / say line exists; texts exist
    # --------------------------------------------------------------------------------------------
    texts = {}
    for lang in ("eng", "rus"):
        t = open(os.path.join(PATCH, "gamedata", "configs", "text", lang, "st_coop_soc_milc.xml"), "rb").read().decode("cp1251")
        texts[lang] = set(re.findall(r'<string id="([^"]+)">', t))
    mil_texts = set(re.findall(r'<string id="([^"]+)">', open(os.path.join(REPO, "patches", "soc_mil_quests", "gamedata", "configs", "text", "eng", "st_coop_soc_mil.xml"), "rb").read().decode("cp1251")))
    own = [d for d in DLG if d.startswith("mil_soc_cook") or d.startswith("mil_soc_dolg_leader") or d == "mil_soc_lukash_dialog"]
    bad_fn, bad_txt, bad_say, bad_next, bad_flag = [], [], [], [], []
    for did in own:
        dd = DLG[did]
        for pid, q in dd["phrases"].items():
            for ref in q["pre"] + [a for a in q["act"] if not a.startswith("dialogs.")]:
                mod, fn = ref.split(".")
                m = {"coop_soc_mil": mil, "coop_soc_mil_say": mil_say, "coop_soc_milc": milc, "coop_soc_milc_say": say}[mod]
                if m[fn] is None:
                    bad_fn.append(ref)
            if q["text"]:
                if not (q["text"] in texts["eng"] and q["text"] in texts["rus"]) and q["text"] not in mil_texts:
                    bad_txt.append(q["text"])
            for n in q["nxt"]:
                if n not in dd["phrases"]:
                    bad_next.append((did, pid, n))
            for f in q["flags"] + q["has"] + q["dont"]:
                if f != f.upper():
                    bad_flag.append(f)
        for pre in dd["pre"]:
            mod, fn = pre.split(".")
            if {"coop_soc_mil": mil, "coop_soc_milc": milc}[mod][fn] is None:
                bad_fn.append(pre)
        for f in dd["has"] + dd["dont"]:
            if f != f.upper():
                bad_flag.append(f)
    check("every Lua function of the dialogs exists", not bad_fn, sorted(set(bad_fn)))
    check("every phrase text exists (eng + rus, or in soc_mil_quests)", not bad_txt, bad_txt[:3])
    check("every next phrase exists, every flag is upper case", not bad_next and not bad_flag, (bad_next[:2], bad_flag[:2]))
    ids = set(DLG["mil_soc_lukash_dialog"]["phrases"].keys())
    expect = set(p[0] for p in MM.DIALOGS["lu"]["phrases"]) | set(p["id"] for p in M.LUKASH_NEW)
    check("Lukash dialog = soc_mil_quests phrases + courier phrases", ids == expect, (ids ^ expect))
    check("the Chef has 12 actor dialogs + greeting", all(("mil_soc_" + s[len("mil_"):]) in DLG for s in M.COOK_DIALOGS) and "mil_soc_cook_dialog" in DLG)
    stage_ids = [s["id"] for s in milc["STAGES"].values()]
    check("one stage per task of the model", sorted(stage_ids) == sorted(t["id"] for t in M.TASKS), stage_ids)
    tm = open(os.path.join(REPO, "patches", "freedom_duty", "gamedata", "configs", "misc", "tm_coop_l07_military.ltx"), "rb").read().decode("latin-1")
    sections = set(re.findall(r"^\[([^\]]+)\]", tm, re.M))
    check("every stage task has a section in tm_coop_l07_military.ltx", all(t["id"] in sections for t in M.TASKS), [t["id"] for t in M.TASKS if t["id"] not in sections])
    for lang in ("eng", "rus"):
        miss = [t["id"] for t in M.TASKS if ("st_" + t["id"][:-5] + "_name") not in texts[lang] or ("st_" + t["id"][:-5] + "_descr") not in texts[lang]]
        check("task texts exist (%s)" % lang, not miss, miss)

    # --------------------------------------------------------------------------------------------
    # 1. Lukash: exactly one greeting state for every flag combination (the courier states are layered on soc_mil_quests)
    # --------------------------------------------------------------------------------------------
    relevant = [MM.LK, MM.MAXF, MM.CP, MM.MD, MM.DD, MM.DONE, MM.BP, MM.END, MM.LD, M.CSTART, M.CFAIL, M.CDONE, M.CDEAD, M.ADEAD, M.CCALL]
    rnd = random.Random(11)
    bad = []
    for n in range(4000):
        reset()
        me = player(1, "tester")
        E["__me"] = me
        for f in relevant:
            if rnd.random() < 0.45:
                give(f)
        if rnd.random() < 0.3:
            give("MIL_SOC_PAID_C7_TESTER")
        ph0 = DLG["mil_soc_lukash_dialog"]["phrases"]["0"]
        holds = []
        for h in ph0["nxt"]:
            hp = DLG["mil_soc_lukash_dialog"]["phrases"][h]
            if all(call(*pre.split("."), npc, me) for pre in hp["pre"]):
                holds.append(h)
        if len(holds) != 1:
            bad.append((holds, [f for f in relevant if flag(f)]))
            break
    check("Lukash: exactly one greeting state per flag combination (4000 random combinations)", not bad, bad[:2])

    # --------------------------------------------------------------------------------------------
    # 2. the courier job, whole route through the real dialogs
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice")
    B = player(2, "bob")
    step()
    check("nothing given and nothing created before the job", created() == 2 and not tasks_opened(), (created(), tasks_opened()))
    step(2500)
    check("Chef and Bulldog 6 exist from the start (SoC: always there); the item has no story id of its own, the script registers it",
          ent("mil_soc_cook") is not None and ent("mil_soc_rg6") is not None)
    check("the Chef stands at the SoC table, the RG-6 in the village basement",
          abs(ent("mil_soc_cook")["position"]["x"] + 76.6) < 0.01 and abs(ent("mil_soc_rg6")["position"]["y"] + 27.47) < 0.01)
    # Duty destroyed, then the report
    give(MM.LK)
    for f in MM.DUTY_DEAD:
        give(f)
    step()
    v = talk("mil_soc_lukash_dialog", A, ["1301"])
    check("Lukash report: assignment complete, the snitch job is offered and taken",
          v == ["3001", "3002", "30021", "1223", "1300", "1301", "1500", "1501"], v)
    check("report flag DONE and the job flag START (the Barrier is not offered yet)", flag(MM.DONE) and flag(M.CSTART) and not flag(MM.BP))
    step()
    check("Pavlik created once, with a story id and the section", created() == 3 and ent("mil_soc_pavlik") is not None and ent("mil_soc_pavlik")["section"] == "mil_soc_pavlik")
    check("step 1 'Get to the farmstead' given to both players", given("mil_soc_courier_1_task", 1) == 1 and given("mil_soc_courier_1_task", 2) == 1)
    C = player(3, "carol")
    step()
    check("late joiner gets the open step", given("mil_soc_courier_1_task", 3) == 1)
    run(3)
    check("steps are given once per player, Pavlik is not created twice", given("mil_soc_courier_1_task", 1) == 1 and created() == 3)
    check("Lukash while the job runs: 'You're still here?'", talk("mil_soc_lukash_dialog", A) == ["4001"])
    check("hand-in not possible yet (no step 5)", given("mil_soc_courier_5_task", 1) == 0)
    # a player walks to the farmstead, far from Pavlik
    at(A, -179.9, -16.0, 330.0)         # 22.6 m south of Pavlik (352.7) and 34.8 m from the zone center (364.8): outside the 45 m sphere? inside
    step()
    check("a player inside the 45 m zone (still > 12 m from Pavlik): CKHUT", flag(M.CKHUT) and not flag(M.CSEEN) and not flag(M.CFAIL))
    step()
    check("step 2 'Wait until the snitch brings out his agent' given to all", all(given("mil_soc_courier_2_task", i) == 1 for i in (1, 2, 3)))
    # Pavlik walks to the meeting point
    move("mil_soc_pavlik", -175.9, -16.0, 381.7)
    step()
    check("Pavlik at the meeting point: IN_KHUTOR and the call cue", flag(M.CPIN) and flag(M.CUE_CALL) and not flag(M.CCALL))
    step(4000)
    check("the call is not over yet", not flag(M.CCALL))
    step(5000)
    check("call over (8.8 s): CCALL", flag(M.CCALL))
    step()
    check("Ara and three bodyguards created at the west", created() == 7 and ent("mil_soc_ara") is not None and all(ent("mil_soc_ara_guard_%d" % i) is not None for i in (1, 2, 3)),
          created())
    check("Ara starts about 97 m west of the farmstead (online)", abs(ent("mil_soc_ara")["position"]["x"] + 273.9) < 0.01)
    check("steps 3 'Get rid of the snitch' and 4 'Get rid of the agent' given to all",
          all(given("mil_soc_courier_3_task", i) == 1 and given("mil_soc_courier_4_task", i) == 1 for i in (1, 2, 3)))
    check("the meeting has not started", not flag(M.ARRIVE) and not flag(M.CUE_MEET))
    move("mil_soc_ara", -177.0, -16.0, 380.0)
    step()
    check("Ara at the meeting point: ARRIVE and the meeting cue", flag(M.ARRIVE) and flag(M.CUE_MEET) and not flag(M.CUE_AMBUSH))
    step(5000)
    check("the talk goes on", not flag(M.AEND))
    step(5000)
    check("talk over (9 s): AEND, Ara leaves", flag(M.AEND))
    kill("mil_soc_pavlik")
    step()
    check("Pavlik dead after the call: CDEAD, no failure", flag(M.CDEAD) and not flag(M.CFAIL))
    check("no report step before the agent is dead", given("mil_soc_courier_5_task", 1) == 0)
    kill("mil_soc_ara")
    step()
    check("Ara dead: ADEAD; step 5 'Report to Lukash' given to all", flag(M.ADEAD) and all(given("mil_soc_courier_5_task", i) == 1 for i in (1, 2, 3)))
    check("no more NPCs created", created() == 7)
    # Lukash pays every player once
    v = talk("mil_soc_lukash_dialog", A, ["7004"])
    check("Lukash pays the snitch job, then offers the Barrier", v == ["5001", "5002", "7003", "7004"], v)
    check("7000 to alice, flags DONE (courier) and BP", money("alice") == 7000 and flag(M.CDONE) and flag(MM.BP), money("alice"))
    v = talk("mil_soc_lukash_dialog", B, ["7006"])
    check("a second player is paid too (once)", v[:2] == ["5001", "5002"] and money("bob") == 7000, (v, money("bob")))
    check("alice is not paid twice", talk("mil_soc_lukash_dialog", A) != [] and money("alice") == 7000)
    check("the report step is closed", "mil_soc_courier_5_task" not in tasks_opened())

    # --------------------------------------------------------------------------------------------
    # 3. courier failures
    # --------------------------------------------------------------------------------------------
    def job(level="coop_l07_military"):
        reset(level)
        a = player(1, "alice")
        b = player(2, "bob")
        give(MM.LK, MM.DONE, M.CSTART)
        step()
        return a, b

    A, B = job()
    at(A, -178.0, -16.5, 360.0)        # 7.3 m from Pavlik (352.7): too close
    step()
    check("a player within 12 m of Pavlik before he left: SEEN and the job is lost", flag(M.CSEEN) and flag(M.CFAIL) and not flag(M.CKHUT))
    step()
    check("steps 2.. never given after the failure", given("mil_soc_courier_2_task", 1) == 0)
    check("Lukash after the failure: 'you screwed up', then the Barrier offer",
          talk("mil_soc_lukash_dialog", A, ["7004"]) == ["7001", "7002", "7003", "7004"])

    A, B = job()
    kill("mil_soc_pavlik")
    step()
    check("Pavlik killed before his call: the job is lost", flag(M.CDEAD) and flag(M.CFAIL) and not flag(M.CCALL))

    A, B = job()
    at(A, -179.9, -16.0, 330.0)
    step()
    move("mil_soc_pavlik", -175.9, -16.0, 381.7)
    step()
    step(10000)
    check("call done", flag(M.CCALL))
    move("mil_soc_pavlik", -176.0, -16.0, 381.0)
    step()
    check("Pavlik inside the zone: no failure", not flag(M.CFAIL))
    move("mil_soc_pavlik", -176.4, -16.1, 420.0)       # 42 m from the zone center
    step()
    check("Pavlik left the farmstead zone after he was in it: the job is lost", flag(M.CLEFT) and flag(M.CFAIL))

    A, B = job()
    at(A, -179.9, -16.0, 330.0)
    step()
    move("mil_soc_pavlik", -175.9, -16.0, 381.7)
    step()
    step(10000)
    step()
    # Ara never reaches the meeting point (frozen offline): arrives by timeout, talks, leaves, escapes
    step(81000)
    check("Ara frozen offline: ARRIVE by timeout (80 s)", flag(M.ARRIVE))
    step(9500)
    check("AEND after the talk", flag(M.AEND))
    step(50000)
    check("Ara still alive 50 s after the talk: not gone yet", not flag(M.ALEAVE))
    step(61000)
    check("Ara alive 110 s after the talk: he got away, the job is lost", flag(M.ALEAVE) and flag(M.CFAIL))

    A, B = job()
    at(A, -179.9, -16.0, 330.0)
    step()
    move("mil_soc_pavlik", -175.9, -16.0, 381.7)
    step()
    step(10000)
    step()
    move("mil_soc_ara", -380.0, -14.0, 398.0)     # reached the far end of the way out
    step()
    check("(before the talk) Ara far away is no escape yet", not flag(M.ALEAVE))
    move("mil_soc_ara", -177.0, -16.0, 380.0)
    step()
    step(9500)
    move("mil_soc_ara", -380.0, -14.0, 398.0)
    step()
    check("Ara reached the far end after the talk: ALEAVE", flag(M.ALEAVE) and flag(M.CFAIL))

    # Pavlik dead before Ara arrives: the agent shouts (ambush cue) and leaves
    A, B = job()
    at(A, -179.9, -16.0, 330.0)
    step()
    move("mil_soc_pavlik", -175.9, -16.0, 381.7)
    step()
    step(10000)
    step()
    kill("mil_soc_pavlik")
    step()
    check("Pavlik killed after the call: no failure, no ambush before Ara is there", flag(M.CDEAD) and not flag(M.CFAIL) and not flag(M.CUE_AMBUSH))
    move("mil_soc_ara", -177.0, -16.0, 380.0)
    step()
    check("Ara arrives and finds Pavlik dead: the ambush cue instead of the talk", flag(M.ARRIVE) and flag(M.CUE_AMBUSH) and not flag(M.CUE_MEET))
    step(4500)
    check("ambush over (4 s): AEND", flag(M.AEND))

    # Pavlik shot during the talk
    A, B = job()
    at(A, -179.9, -16.0, 330.0)
    step()
    move("mil_soc_pavlik", -175.9, -16.0, 381.7)
    step()
    step(10000)
    step()
    move("mil_soc_ara", -177.0, -16.0, 380.0)
    step()
    check("meeting cue", flag(M.CUE_MEET))
    kill("mil_soc_pavlik")
    step()
    check("Pavlik dies during the talk: the ambush cue follows at once", flag(M.CUE_AMBUSH))
    step(4500)
    check("the talk ends 4 s after the shot", flag(M.AEND))

    # --------------------------------------------------------------------------------------------
    # 4. NPC creation details
    # --------------------------------------------------------------------------------------------
    A, B = job()
    pid = ent("mil_soc_pavlik")["id"]
    milc["reset_vm"]()          # level change / death of a player: the Lua VM restarts
    step()
    check("VM restart: Pavlik is not created again", created() == 3 and ent("mil_soc_pavlik")["id"] == pid, created())
    check("VM restart: tasks of the stage are given again after the restart to every player once (the engine ignores duplicates)", given("mil_soc_courier_1_task", 1) >= 1)
    # created on another level: nothing happens until a player is on the military level
    reset("coop_l01_escape")
    A = player(1, "alice")
    give(MM.LK, MM.DONE, M.CSTART)
    step()
    check("not on the military level: nothing is created", created() == 0)
    E["__level"] = "coop_l07_military"
    step()
    check("on the military level: Pavlik, the Chef and the RG-6 are created", created() == 3)
    # the engine did not register the story id: the script does it
    reset()
    E["__auto_story"] = False
    A = player(1, "alice")
    give(MM.LK, MM.DONE, M.CSTART)
    step()
    check("story id not registered by the engine: not looked up yet", E["get_story_object_id"]("mil_soc_pavlik") is None)
    step(2500)
    check("story id registered by the script after 2 s", E["get_story_object_id"]("mil_soc_pavlik") is not None)
    # a failing create is retried, not flagged as made
    reset()
    E["__create_fail"] = True
    A = player(1, "alice")
    step()
    check("create failed: not flagged as made", not flag("MIL_SOC_MADE_COOK") and created() == 0)
    E["__create_fail"] = False
    step()
    check("create retried and made once", flag("MIL_SOC_MADE_COOK") and created() == 2)
    # a wrong AI node is replaced by the nearest one
    reset()
    E["__nodepos"] = lua.table_from({})
    A = player(1, "alice")
    step()
    check("AI node not where expected: nearest node (777) and nearest game vertex are used", ent("mil_soc_cook")["lv"] == 777 and ent("mil_soc_cook")["gv"] is not None)
    # the sections are not in the configs (apply_shared.py not applied): nothing is created, no crash, no flag, the RG-6 (a stock section) still is
    reset()
    E["__sections"] = lua.table_from({"wpn_rg-6": True})
    A = player(1, "alice")
    give(MM.LK, MM.DONE, M.CSTART)
    run(3)
    check("unknown spawn sections: no NPC created, no 'made' flag", created() == 1 and not flag("MIL_SOC_MADE_COOK") and not flag("MIL_SOC_MADE_PAVLIK"), created())
    E["__sections"] = None
    step()
    check("sections known again: the NPCs are created", created() == 3)
    # no players: nothing is created
    reset()
    step()
    check("no player: nothing created", created() == 0)
    # the logic is started by script when the engine did not run it (two idle ticks)
    reset()
    A = player(1, "alice")
    step()
    cid = ent("mil_soc_cook")["id"]
    E["db"]["storage"][cid] = lua.table_from({"object": lua.table_from({}), "active_scheme": None})
    step()
    check("one idle tick: logic not started yet", len(list(E["__logic_started"].values())) == 0)
    step()
    check("two idle ticks: the logic file of the Chef is started", [str(x) for x in E["__logic_started"].values()] == ["scripts\\coop_l07_military\\mil_soc_cook.ltx"])
    # a killed and released NPC is not replaced
    reset()
    A = player(1, "alice")
    step()
    cid = ent("mil_soc_cook")["id"]
    E["__objs"][cid] = None
    run(6)
    check("the Chef released after his death: not created again", created() == 2)

    # --------------------------------------------------------------------------------------------
    # 5. Bulldog 6
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice", (-100.0, -16.0, 300.0))
    B = player(2, "bob", (-100.0, -16.0, 300.0))
    step()
    check("no order, no task", not tasks_opened())
    v = talk("mil_soc_dolg_leader_join", A, ["1112"])
    check("Voronin: the order is offered, the player declines first", v == ["0", "1", "11", "111", "1112", "11121"], v)
    check("declined: no flag, no task", not flag(M.RSTART))
    v = talk("mil_soc_dolg_leader_join", A, ["1111"])
    check("Voronin: the player takes the order", v == ["0", "1", "11", "111", "1111", "11111"], v)
    check("RG6_START given", flag(M.RSTART))
    check("the order is not offered twice", talk("mil_soc_dolg_leader_join", B) is None)
    step()
    check("step 1 'Find the cook in the Freedom base' given to both players", given("mil_soc_rg6_1_task", 1) == 1 and given("mil_soc_rg6_1_task", 2) == 1)
    check("the Chef greets with the SoC line", talk("mil_soc_cook_dialog", A) == ["0"])
    # small talks
    for i in range(1, 6):
        d = "mil_soc_cook_common%d" % i
        v = talk(d, A)
        check("Chef small talk %d" % i, v is not None and len(v) >= 5, v)
        check("Chef small talk %d is told once" % i, talk(d, A) is None)
    check("small talk 6 needs the answer first", talk("mil_soc_cook_common6", A) is None)
    check("no vodka: no drink dialog", talk("mil_soc_cook_drink_for_rg6_1", A) is None)
    A["__inv"] = lua.table_from({"vodka": 3})
    v = talk("mil_soc_cook_drink_for_rg6_1", A)
    check("drink 1 (after all five small talks, with vodka)", v == ["0", "1", "2", "3", "4", "5", "6"], v)
    check("one bottle taken", A["__inv"]["vodka"] == 2)
    check("drink 1 once", talk("mil_soc_cook_drink_for_rg6_1", A) is None)
    check("question 2 before drink 2: not offered", talk("mil_soc_cook_drunk_question_about_rg6_2", A) is None)
    v = talk("mil_soc_cook_drunk_question_about_rg6_1", A)
    check("question 1: he refuses", v is not None and v[-1] == "6" and flag(M.COOK_RG6[0]), v)
    v = talk("mil_soc_cook_drink_for_rg6_2", A)
    check("drink 2", v is not None and flag(M.COOK_DRINK[1]) and A["__inv"]["vodka"] == 1, v)
    v = talk("mil_soc_cook_drunk_question_about_rg6_2", A)
    check("question 2: no can do", v is not None and flag(M.COOK_RG6[1]), v)
    check("question 3 not offered before drink 3", talk("mil_soc_cook_drunk_question_about_rg6_3", A) is None)
    v = talk("mil_soc_cook_drink_for_rg6_3", A)
    check("drink 3 (the last bottle)", v is not None and flag(M.COOK_DRINK[2]) and A["__inv"]["vodka"] == 0, v)
    check("the Bulldog 6 hint is not given yet", not flag(M.RASK))
    v = talk("mil_soc_cook_drunk_question_about_rg6_3", A)
    check("question 3: the Chef gives it away (in the village)", v is not None and flag(M.RASK) and flag(M.COOK_RG6[3]), v)
    step()
    check("steps 'talk to the Chef' / 'find the Bulldog 6': step 2 closed by RASK, step 3 given to both",
          all(given("mil_soc_rg6_3_task", i) == 1 for i in (1, 2)))
    check("Chef after the hint: the last small talk", talk("mil_soc_cook_common6", A) is not None)
    check("hand-in not possible yet: step 4 not given", given("mil_soc_rg6_4_task", 1) == 0)
    check("Voronin: no hand-in without the weapon", talk("mil_soc_dolg_leader_quest_rg6_finish", A) is None)
    B["__inv"] = lua.table_from({"wpn_rg-6": 1})
    step()
    check("a player picks up the Bulldog 6: RGOT; step 4 given to both", flag(M.RGOT) and all(given("mil_soc_rg6_4_task", i) == 1 for i in (1, 2)))
    check("Voronin: bob can hand it in, alice (no weapon) cannot", talk("mil_soc_dolg_leader_quest_rg6_finish", A) is None)
    v = talk("mil_soc_dolg_leader_quest_rg6_finish", B)
    check("Voronin: hand-in and the suit", v == ["0", "1"], v)
    check("weapon taken, suit given to bob, flag DONE", B["__inv"]["wpn_rg-6"] == 0 and int(E["__items"]["bob:dolg_scientific_outfit"]) == 1 and flag(M.RDONE))
    check("the hand-in is not repeated", talk("mil_soc_dolg_leader_quest_rg6_finish", B) is None)
    check("bob does not get a second suit", talk("mil_soc_dolg_leader_rg6_late", B) is None)
    v = talk("mil_soc_dolg_leader_rg6_late", A)
    check("alice (not there) gets the suit too", v == ["0", "1"] and int(E["__items"]["alice:dolg_scientific_outfit"]) == 1, v)
    check("alice once", talk("mil_soc_dolg_leader_rg6_late", A) is None)
    check("all RG-6 steps closed", not [t for t in tasks_opened() if "rg6" in t])
    # no soft-locks
    reset()
    A = player(1, "alice", (-100.0, -16.0, 300.0))
    step()
    give(M.RSTART)
    E["SOCMILC_FORCE_DEAD"] = lua.table_from({"cook": True})
    step()
    check("Chef dead before he talked: the hint is given anyway (RASK) and step 3 comes", flag(M.RASK) and flag(M.RMET) and given("mil_soc_rg6_3_task", 1) == 1)
    reset()
    A = player(1, "alice", (-100.0, -16.0, 300.0))
    step()
    give(M.RSTART)
    A["__inv"] = lua.table_from({"wpn_rg-6": 1})
    E["SOCMILC_FORCE_DEAD"] = lua.table_from({"bar_smart_terrain_4_duty_voronin": True})
    step()
    check("Voronin dead: the order is done when a player holds the weapon", flag(M.RGOT) and flag(M.RDONE))
    reset()
    A = player(1, "alice", (-100.0, -16.0, 300.0))
    step()
    give(M.RSTART)
    cp = ent("mil_soc_cook")["position"]
    at(A, cp["x"] + 5, cp["y"], cp["z"])
    step()
    check("a player within 12 m of the Chef: step 'find the cook' done (RMET), step 2 given", flag(M.RMET) and given("mil_soc_rg6_2_task", 1) == 1)
    reset()
    A = player(1, "alice", (-100.0, -16.0, 300.0))
    step()
    give(M.RSTART)
    A["__alive"] = False
    step()
    check("dead player: no task", given("mil_soc_rg6_1_task", 1) == 0)
    A["__alive"] = True
    step()
    check("respawned player: gets the open step", given("mil_soc_rg6_1_task", 1) == 1)

    # --------------------------------------------------------------------------------------------
    # 6. voice cues on a client
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice", (-170.0, -16.0, 380.0))
    E["__me"] = A
    give(M.CUE_CALL)                 # a cue that happened before this client joined: never replayed
    milc["client_tick"]()
    check("first client tick only records the flags", len(list(E["__sounds"].values())) == 0)
    give(M.CUE_MEET)
    milc["client_tick"]()
    sounds = [str(x) for x in E["__sounds"].values()]
    check("the meeting cue plays once, Russian path", sounds == ["characters_voice\\scenario\\coop_l07_military\\mil_soc_courier_meet"], sounds)
    milc["client_tick"]()
    milc["client_tick"]()
    check("not replayed", len(list(E["__sounds"].values())) == 1)
    reset()
    E["__voice"] = "eng"
    A = player(1, "alice", (-170.0, -16.0, 380.0))
    E["__me"] = A
    milc["client_tick"]()
    give(M.CUE_AMBUSH)
    milc["client_tick"]()
    sounds = [str(x) for x in E["__sounds"].values()]
    check("English voice language: the eng subfolder", sounds == ["characters_voice\\scenario\\coop_l07_military\\eng\\mil_soc_courier_ambush"], sounds)
    reset()
    A = player(1, "alice", (-170.0, -16.0, 380.0))
    E["__me"] = A
    E["__files"] = lua.table_from({})
    milc["client_tick"]()
    give(M.CUE_CALL)
    milc["client_tick"]()
    check("missing sound file: silent, no error", len(list(E["__sounds"].values())) == 0)
    reset()
    A = player(1, "alice", (900.0, -16.0, 380.0))      # far away
    E["__me"] = A
    milc["client_tick"]()
    give(M.CUE_CALL)
    milc["client_tick"]()
    check("player far from the farmstead hears nothing", len(list(E["__sounds"].values())) == 0)
    reset()
    E["__dedicated"] = True
    E["__me"] = None
    milc["client_tick"]()
    give(M.CUE_CALL)
    milc["client_tick"]()
    check("no local actor (dedicated server): nothing", len(list(E["__sounds"].values())) == 0)

    # --------------------------------------------------------------------------------------------
    # 7. Lukash dead: nobody to report to
    # --------------------------------------------------------------------------------------------
    reset()
    A = player(1, "alice")
    give(MM.LK, MM.DONE, M.CSTART, M.CCALL, M.CDEAD, M.ADEAD, MM.LD)
    step()
    check("Lukash dead after both kills: the job closes (CDONE) without a payment", flag(M.CDONE) and money("alice") == 0)

    print()
    print("ALL PASS" if fails == 0 else "FAILED: %d" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
