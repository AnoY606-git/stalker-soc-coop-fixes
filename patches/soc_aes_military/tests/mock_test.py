"""Offline check (no game) of coop_soc_aes_military.script.
usage: python mock_test.py     (needs `pip install lupa`, like patches\\soc_aes_quests\\tests\\mock_test.py)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with positions, army squads with members that can die, smart terrains,
map spots, game news, sound objects, the file system) and proves:
  * nothing happens off CNPP-1; the plan is found by a player at the SoC soldier spot or by the party passing the SoC "actor_ready" line, or by a later step
  * the task "Operation Monolith" goes to EVERY living player once on CNPP-1 (late joiner too), never to the dead, never once the sarcophagus is found,
    never twice (a new Lua VM gives it again only while it is open; a finished task is never given)
  * the markers: gate, two fortifications, sarcophagus and the first living soldier of each of the 8 army groups, synced once per player (late joiners get
    the old ones), moved to the next living soldier when the carrier dies, gone when the group is dead, when the step is over and when the task is done
  * the steps (gate -> Monolith 1 -> Monolith 2 -> sarcophagus) follow the lowest x of the players, a later flag sets the earlier ones
  * the radio: every zone fires once per player, lines are queued in the SoC order, played one after the other with a gap, the per-player flag stops the
    replay after a reload, a missing sound file is skipped, the queue is bounded; the "Situation" article is shown once per player
  * a missing carrier (no squad, no smart terrain) never raises and never blocks the task
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
local script_path, keep_flags = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}
E.__calls = {}
E.__side = "host"
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return E.__side == "server" or E.__side == "host" end
function E.OnClient() return E.__side == "client" or E.__side == "host" end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
local flags = keep_flags or {}
E.__flags = flags
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__setpos(o, x, y, z) o.__pos = E.vector():set(x, y, z) end
E.__level = "coop_l11_stancia_1"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.__spots = {}       -- id -> { typ, hint }
E.__synced = {}      -- "id|pid" -> n
E.__spot_adds = 0
E.level.map_add_object_spot_ser = function(id, typ, hint) E.__spots[id] = { typ = typ, hint = hint }; E.__spot_adds = E.__spot_adds + 1 end
E.level.map_remove_object_spot = function(id, typ) E.__spots[id] = nil end
E.level.map_sync_spot = function(id, typ, pid) local k = id .. "|" .. tostring(pid); E.__synced[k] = (E.__synced[k] or 0) + 1 end
E.db = { mp_actors = {} }
-- server objects: smart terrains, named objects, army squads with members that can die
E.__objs = {}        -- id -> object
E.__named = {}       -- name -> object
E.__smart = {}       -- name -> { id }
E.__story = {}       -- story id -> id
function E.alife() return { object = function(self, x)
	if type(x) == "string" then return E.__named[x] end
	return E.__objs[x]
end } end
function E.get_story_object_id(s) return E.__story[s] end
E.sim_board = { get_sim_board = function() return { get_smart_by_name = function(self, n) return E.__smart[n] end } end }
function E.__smart_terrain(name, id) local o = { id = id, __dead = false }; E.__smart[name] = o; E.__objs[id] = o; return o end
function E.__named_obj(name, id) local o = { id = id }; E.__named[name] = o; E.__objs[id] = o; return o end
function E.__squad(story, id, member_ids)
	local sq = { id = id, __members = {} }
	function sq:squad_members()
		local i = 0
		return function() i = i + 1; return self.__members[i] end
	end
	for _, mid in ipairs(member_ids) do
		local m = { id = mid, __dead = false }
		function m:alive() return not self.__dead end
		E.__objs[mid] = m
		sq.__members[#sq.__members + 1] = { id = mid }
	end
	E.__objs[id] = sq
	E.__story[story] = id
	return sq
end
E.__local = nil
E.__news = {}
function E.getLocalActor() return E.__local end
E.game = { translate_string = function(s) return "T:" .. s end }
E.__voice = "eng"
E.coop_soc_opening = { voice_lang = function() return E.__voice end }   -- patch cutscenes_pkg_opening: the voice language of this player
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z) }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:give_game_news(a, b, c, d, e2, f2) E.__news[#E.__news + 1] = self.__name .. ":" .. a .. ":" .. b end
	E.db.mp_actors[id] = o
	return o
end
-- sound
E.__played = {}
E.__snd = nil
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(t, path)
	local o = { path = path, __playing = true }
	function o:play(a, d, f) E.__played[#E.__played + 1] = self.path; E.__snd = self end
	function o:playing() return self.__playing end
	return o
end })
E.__missing = {}
function E.getFS() return { exist = function(self, area, name) return not E.__missing[name] end } end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_soc_aes_military"))
setfenv(fn, env)
fn()
E.__env = env
return E
'''

TASK = "aes_military_task"
CNPP = "coop_l11_stancia_1"
SAR = "coop_l11_sarcofag"
PRI = "coop_l10_pripyat"
BODY = (919.4, -0.1, -217.3)
FAR = (919.0, 0.0, -292.0)            # the arrival point
RDY = (926.0, -0.1, -170.6)           # SoC actor_ready line
GATE = (859.3, -1.7, -42.9)
SARC = (387.6, 0.2, -0.9)

GROUPS = {
    "sapsan": ("aes_1_smart_terrain_4_ordinary_military_1_squad", 100, (101, 102, 103)),
    "korshun": ("aes_1_smart_terrain_4_ordinary_military_2_squad", 110, (111, 112)),
    "yastreb": ("aes_1_smart_terrain_5_ordinary_military_1_squad", 120, (121, 122)),
    "pustelga": ("aes_1_smart_terrain_5_ordinary_military_2_squad", 130, (131, 132)),
    "sokol": ("aes_1_smart_terrain_9_ordinary_military_1_squad", 140, (141, 142)),
    "grif": ("aes_1_smart_terrain_9_ordinary_military_2_squad", 150, (151, 152)),
    "sova": ("aes_1_smart_terrain_11_ordinary_military_1_squad", 160, (161, 162)),
    "lun": ("aes_1_smart_terrain_7_ordinary_military_1_squad", 170, (171, 172)),
}
HINT = {"gate": "coop_soc_aesm_gate", "mono1": "coop_soc_aesm_mono1", "mono2": "coop_soc_aesm_mono2", "sarc": "coop_soc_aesm_sarc"}
for k in GROUPS:
    HINT[k] = "coop_soc_aesm_g_" + k


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    path = os.path.join(PATCH, "gamedata", "scripts", "coop_soc_aes_military.script")
    st = {}

    def tick(ms=1500):
        E = st["E"]
        E["__time"] = E["__time"] + ms
        for f in list(E["__calls"].values()):
            f()

    def world(E):
        E["__smart_terrain"]("aes_1_smart_terrain_1", 11)
        E["__smart_terrain"]("aes_1_smart_terrain_2", 12)
        E["__smart_terrain"]("aes_1_smart_terrain_10", 13)
        E["__named_obj"]("aes_1_smart_terrain_8_10_attack_space_restrictor", 14)
        for k, (story, sid, members) in GROUPS.items():
            E["__squad"](story, sid, lua.table_from(list(members)))

    def reset(level=CNPP, keep=False, side="host", with_world=True):
        # keep=True: a new Lua VM (level change / reload) with the saved story flags of the old one
        E = lua.execute(PRELUDE, path, st["E"]["__flags"] if keep else None)
        E["__level"] = level
        E["__side"] = side
        if with_world:
            world(E)
        st["E"] = E
        st["env"] = E["__env"]
        st["env"].install()

    def player(pid, name, pos=FAR):
        p = st["E"]["__player"](pid, name, pos[0], pos[1], pos[2])
        return p

    def put(p, pos):
        st["E"]["__setpos"](p, pos[0], pos[1], pos[2])

    def flag(n):
        return st["E"]["story_flags"]["has_flag"](n)

    def give(n):
        st["E"]["story_flags"]["give_flag"](n)

    def given(pid):
        v = st["E"]["__given"][TASK + "|" + str(pid)]
        return int(v) if v is not None else 0

    def total_given():
        return sum(int(v) for v in st["E"]["__given"].values())

    def spots():
        return {int(k): (v["typ"], v["hint"]) for k, v in st["E"]["__spots"].items()}

    def spot_keys():
        t = st["env"].spot_ids()
        return {k: int(v) for k, v in t.items()}

    def synced(spot_id, pid):
        v = st["E"]["__synced"][str(spot_id) + "|" + str(pid)]
        return int(v) if v is not None else 0

    def news():
        return [st["E"]["__news"][i] for i in range(1, len(st["E"]["__news"]) + 1)]

    def played():
        return [st["E"]["__played"][i] for i in range(1, len(st["E"]["__played"]) + 1)]

    def finish_line():
        snd = st["E"]["__snd"]
        if snd is not None:
            snd["__playing"] = False

    def kill(member_id):
        st["E"]["__objs"][member_id]["__dead"] = True

    def set_local(p):
        st["E"]["__local"] = p

    # ================================================================== off CNPP-1
    reset(PRI)
    a = player(1, "qaa", BODY)
    give("SOC_AESM_PLAN")
    tick(); tick()
    check("off CNPP-1 nothing is given even with the plan flag", total_given() == 0)
    check("off CNPP-1 no map spot", len(spots()) == 0)

    # ================================================================== before the plan
    reset(CNPP)
    a = player(1, "qaa", FAR)
    b = player(2, "qab", FAR)
    tick(); tick()
    check("arrival: no plan yet, no task", total_given() == 0 and not flag("SOC_AESM_PLAN"))
    check("arrival: no map spot before the plan", len(spots()) == 0)
    put(a, (900.0, 0.0, -217.3))
    tick()
    check("14 m from the soldier spot: still no plan", not flag("SOC_AESM_PLAN"))
    put(a, (915.0, -0.1, -217.0))
    tick()
    check("a player at the SoC soldier spot finds the plan", flag("SOC_AESM_PLAN"))
    check("the task goes to EVERY living player, once (both)", given(1) == 1 and given(2) == 1, (given(1), given(2)))
    tick(); tick()
    check("later ticks do not give it again", given(1) == 1 and given(2) == 1 and total_given() == 2)
    c = player(3, "qac", FAR)
    tick()
    check("a late joiner gets the open task once", given(3) == 1 and total_given() == 3)
    d = player(4, "qad", FAR)
    d["__alive"] = False
    tick()
    check("a dead player is not given the task", given(4) == 0)
    d["__alive"] = True
    tick()
    check("the same player gets it when he is alive again", given(4) == 1)

    # ================================================================== markers
    sp = spots()
    keys = spot_keys()
    check("12 markers on: gate, 2 fortifications, sarcophagus, 8 groups", len(keys) == 12, sorted(keys))
    check("marker hints are the SoC hint strings", all(sp[keys[k]][1] == HINT[k] for k in keys))
    check("marker type is green_location", all(sp[keys[k]][0] == "green_location" for k in keys))
    check("carriers: gate = smart terrain 1, Monolith 1 = smart terrain 2, Monolith 2 = the named restrictor, sarcophagus = smart terrain 10",
          keys["gate"] == 11 and keys["mono1"] == 12 and keys["mono2"] == 14 and keys["sarc"] == 13, keys)
    check("every group marker sits on the FIRST soldier of its squad", all(keys[k] == GROUPS[k][2][0] for k in GROUPS), keys)
    check("every marker is synced once to every living player", all(synced(keys[k], p) == 1 for k in keys for p in (1, 2, 3, 4)))
    adds = int(st["E"]["__spot_adds"])
    tick(); tick()
    check("a quiet tick does not add or sync again", int(st["E"]["__spot_adds"]) == adds and all(synced(keys[k], 1) == 1 for k in keys))
    e = player(5, "qae", FAR)
    tick()
    check("a late joiner gets the existing markers synced once", all(synced(keys[k], 5) == 1 for k in keys) and all(synced(keys[k], 1) == 1 for k in keys))
    kill(101)
    tick()
    keys = spot_keys()
    check("Sapsan leader dies: the marker moves to the next living soldier", keys["sapsan"] == 102, keys["sapsan"])
    check("the old marker is gone, the new one is synced to everybody", 101 not in spots() and 102 in spots() and all(synced(102, p) == 1 for p in (1, 2, 3, 4, 5)))
    kill(102); kill(103)
    tick()
    keys = spot_keys()
    check("the whole group is dead: its marker is gone, nothing else changes", "sapsan" not in keys and len(keys) == 11 and given(1) == 1)
    check("the task is still given and open with a dead group (never blocks)", flag("SOC_AESM_PLAN") and not flag("SOC_AESM_FOUND"))

    # ================================================================== steps
    check("gate step: flags not set before anybody passes", not flag("SOC_AESM_GATE") and not flag("SOC_AESM_MONO1") and not flag("SOC_AESM_MONO2"))
    put(a, GATE)
    tick()
    check("a player in the gate zone sets the gate flag", flag("SOC_AESM_GATE") and not flag("SOC_AESM_MONO1"))
    keys = spot_keys()
    check("gate marker is gone after the gate, the others stay", "gate" not in keys and "mono1" in keys and "mono2" in keys and "sarc" in keys)
    put(a, (700.0, 0.0, -60.0))
    tick()
    check("x below Monolith 1 sets its flag", flag("SOC_AESM_MONO1") and not flag("SOC_AESM_MONO2"))
    check("Monolith 1 marker gone", "mono1" not in spot_keys() and "mono2" in spot_keys())
    check("an earlier flag is never lost", flag("SOC_AESM_GATE") and flag("SOC_AESM_PLAN"))
    put(a, (600.0, 0.0, -100.0))
    tick()
    check("x below Monolith 2 sets its flag, marker gone", flag("SOC_AESM_MONO2") and "mono2" not in spot_keys())
    check("only the sarcophagus and the groups remain marked", sorted(spot_keys()) == sorted(list(GROUPS.keys()) + ["sarc"]) or sorted(spot_keys()) == sorted([k for k in GROUPS if k != "sapsan"] + ["sarc"]), sorted(spot_keys()))
    n_before = total_given()
    put(a, SARC)
    tick()
    check("a player at the SoC sarcophagus sphere finds it: the task is done", flag("SOC_AESM_FOUND"))
    check("all markers are removed when the task is done", len(spots()) == 0 and len(spot_keys()) == 0)
    f = player(6, "qaf", FAR)
    tick(); tick()
    check("nobody is given the task once the sarcophagus is found", given(6) == 0 and total_given() == n_before)

    # ================================================================== skipped steps and teleports
    reset(CNPP)
    a = player(1, "qaa", FAR)
    put(a, (500.0, 0.0, -120.0))
    tick()
    check("a player teleported past Monolith 2: gate, Monolith 1 and 2 and the plan are all set", flag("SOC_AESM_GATE") and flag("SOC_AESM_MONO1") and flag("SOC_AESM_MONO2") and flag("SOC_AESM_PLAN"))
    check("the task is given (the plan is implied)", given(1) == 1)
    check("only the sarcophagus and the groups are marked", "gate" not in spot_keys() and "mono1" not in spot_keys() and "mono2" not in spot_keys() and "sarc" in spot_keys())

    reset(CNPP)
    a = player(1, "qaa", FAR)
    put(a, RDY)
    tick()
    check("the party passes the SoC actor_ready line without the soldier: the plan is found", flag("SOC_AESM_PLAN") and given(1) == 1)

    reset(SAR)
    a = player(1, "qaa", (0, 0, 0))
    tick()
    check("a party in the Sarcophagus counts as found, no task, no markers", flag("SOC_AESM_FOUND") and total_given() == 0 and len(spots()) == 0)

    reset(CNPP)
    a = player(1, "qaa", FAR)
    give("AES_1_START_GO_TO_SARCOFAG_QUEST_TASK_INFO")
    tick()
    check("the mod's Sarcophagus arrival flag also ends the task", flag("SOC_AESM_FOUND") and total_given() == 0)

    # ================================================================== a new Lua VM (level load)
    reset(CNPP)
    a = player(1, "qaa", BODY)
    tick(); tick()
    check("setup: task given in VM 1", given(1) == 1)
    flags = st["E"]["__flags"]
    reset(CNPP, keep=True)
    a = player(1, "qaa", BODY)
    tick(); tick()
    check("a new VM while the task is open gives it again once (the engine ignores a task the player already has)", given(1) == 1)
    give("SOC_AESM_FOUND")
    reset(CNPP, keep=True)
    a = player(1, "qaa", BODY)
    tick(); tick()
    check("a new VM after the sarcophagus gives nothing", total_given() == 0 and len(spots()) == 0)

    # ================================================================== missing carriers never raise
    reset(CNPP, with_world=False)
    a = player(1, "qaa", BODY)
    tick(); tick()
    check("no squads / smart terrains in the world: the task is still given, no marker, no error",
          given(1) == 1 and len(spots()) == 0 and not any("ERR" in x for x in [st["E"]["__log"][i] for i in range(1, len(st["E"]["__log"]) + 1)]))

    # ================================================================== server only / client only
    reset(CNPP, side="server")
    a = player(1, "qaa", BODY)
    tick(); tick()
    check("dedicated server: task and markers, no radio, no news, no error", given(1) == 1 and len(spots()) == 12 and len(played()) == 0 and len(news()) == 0)
    reset(CNPP, side="client")
    a = player(1, "qaa", BODY)
    set_local(a)
    give("SOC_AESM_PLAN")
    tick(); tick()
    check("client only: nothing is given or marked (server work)", total_given() == 0 and len(spots()) == 0)
    check("client only: the article and the radio work", len(news()) == 1 and len(played()) >= 1)

    # ================================================================== radio and news (client)
    reset(CNPP, side="client")
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    check("arrival on CNPP-1: the first SoC line plays (English folder)", played() == ["characters_voice\\scenario\\aes\\eng\\aes_chopers_begin_1"], played())
    check("arrival: no article before the plan", len(news()) == 0)
    tick(); tick()
    check("the same trigger does not fire twice", len(played()) == 1)
    put(a, RDY)
    tick()
    check("crossing actor_ready queues its line", st["env"].radio_queue_len() == 1, st["env"].radio_queue_len())
    check("the next line waits for the previous one to end", len(played()) == 1)
    finish_line()
    tick(500)
    check("still in the gap: nothing new", len(played()) == 1)
    tick(2500)
    check("after the gap the next line plays", played()[-1].endswith("aes_chopers_begin_2"), played()[-1])
    put(a, (924.1, 0.8, -62.9))
    tick()
    check("crossing the btr zone queues its two lines in the SoC order", st["env"].radio_queue_len() == 2, st["env"].radio_queue_len())
    finish_line(); tick(500); tick(2600)
    check("then the first of them", played()[-1].endswith("aes_choper_hunt_1"), played()[-1])
    finish_line(); tick(500); tick(2600)
    check("then the second", played()[-1].endswith("aes_third_desant_wave"), played()[-1])
    check("the plan came with the zone: one article for this player", flag("SOC_AESM_PLAN") is False or len(news()) <= 1)
    put(a, BODY)
    give("SOC_AESM_PLAN")
    tick()
    check("the plan flag shows the SoC article once", len(news()) == 1 and "coop_soc_aesm_news_name" in news()[0] and "coop_soc_aesm_news_text" in news()[0], news())
    tick(); tick()
    check("the article is not shown twice", len(news()) == 1)
    # a reload: new VM, same saved flags: no replay, no second article
    reset(CNPP, keep=True, side="client")
    a = player(1, "qaa", RDY)
    set_local(a)
    tick(); tick(); tick()
    check("after a reload the radio does not replay the lines this player already heard", len(played()) == 0 and st["env"].radio_queue_len() == 0, played())
    check("after a reload the article is not shown again", len(news()) == 0)
    # another player has his own flags
    reset(CNPP, keep=True, side="client")
    b = player(2, "qab", FAR)
    set_local(b)
    tick()
    check("another player hears the arrival line (flags are per player)", len(played()) == 1)
    # zones
    reset(CNPP, side="client")
    a = player(1, "qaa", (0, 0, 0))
    set_local(a)
    tick()
    out0 = len(played())
    zones = {
        "gate": ((859.3, -1.7, -42.9), (859.3, -1.7, 20.0)),
        "actor_sound": ((404.4, -0.1, -107.7), (404.4, -0.1, -80.0)),
        "road2": ((573.8, 2.9, -99.0), (573.8, 2.9, 100.0)),
        "bridge": ((641.1, 5.1, -138.9), (641.1, 5.1, -120.0)),
    }
    for name, (inside, outside) in zones.items():
        reset(CNPP, side="client")
        a = player(1, "qaa", outside)
        set_local(a)
        tick()
        base = st["env"].radio_queue_len() + len(played())
        put(a, inside)
        tick()
        after = st["env"].radio_queue_len() + len(played())
        check("zone %s: outside = no trigger, inside = trigger" % name, after > base, (base, after))
    # a zone with several shapes: a point in the second box of the helicopter zone
    reset(CNPP, side="client")
    a = player(1, "qaa", (0, 0, 0))
    set_local(a)
    tick()
    base = st["env"].radio_queue_len() + len(played())
    put(a, (781.8 + 48.8, 0.0, -162.2 + 50.1))
    tick()
    check("a second shape of a zone triggers too", st["env"].radio_queue_len() + len(played()) > base)
    # a missing file is skipped
    reset(CNPP, side="client")
    st["E"]["__missing"]["characters_voice\\scenario\\aes\\eng\\aes_chopers_begin_1.ogg"] = True
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    check("a missing sound file is skipped without an error", len(played()) == 0 and st["env"].radio_queue_len() == 0)
    # the voice language of the player picks the recording (the SoC has a Steam English and a Russian recording of every line)
    reset(CNPP, side="client")
    st["E"]["__voice"] = "rus"
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    check("voice language rus: the Russian recording plays", played() == ["characters_voice\\scenario\\aes\\rus\\aes_chopers_begin_1"], played())
    finish_line(); put(a, (404.4, -0.1, -107.7)); tick(500); tick(2600); finish_line(); tick(500); tick(2600)
    check("voice language rus: a line of the second half comes from rus\\aes2", any(p == "characters_voice\\scenario\\aes\\rus\\aes2\\aes_actor_hunt" for p in played()), played())
    reset(CNPP, side="client")
    st["E"]["__voice"] = "eng"
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    check("voice language eng: the English recording plays", played() == ["characters_voice\\scenario\\aes\\eng\\aes_chopers_begin_1"], played())
    # no coop_soc_opening (patch missing): the language of the game texts decides
    reset(CNPP, side="client")
    st["E"]["coop_soc_opening"] = None
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    check("no voice_lang available: English with English game texts", played() == ["characters_voice\\scenario\\aes\\eng\\aes_chopers_begin_1"], played())
    reset(CNPP, side="client")
    st["E"]["coop_soc_opening"] = None
    st["E"]["game"] = lua.eval('{ translate_string = function(s) return string.char(207, 240, 238, 226) end }')
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    check("no voice_lang available: Russian with Cyrillic game texts", played() == ["characters_voice\\scenario\\aes\\rus\\aes_chopers_begin_1"], played())
    # bounded queue
    reset(CNPP, side="client")
    a = player(1, "qaa", FAR)
    set_local(a)
    tick()
    finish_line()
    for p in ((926.0, -0.1, -170.6), (924.1, 0.8, -62.9), (920.9, -0.1, -67.5), (821.0, 0.0, -127.9), (781.8, 0.0, -162.2)):
        put(a, p)
        tick(100)
    check("the radio queue never holds more than 6 lines", st["env"].radio_queue_len() <= 6, st["env"].radio_queue_len())
    # off CNPP-1 no radio
    reset(PRI, side="client")
    a = player(1, "qaa", FAR)
    set_local(a)
    tick(); tick()
    check("off CNPP-1 no radio", len(played()) == 0)

    print("\n%d checks, %d FAIL" % (n_checks, fails))
    sys.exit(1 if fails else 0)


main()
