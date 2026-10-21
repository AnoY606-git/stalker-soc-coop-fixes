"""Offline check (no game) of coop_soc_aes.script.
usage: python mock_test.py     (needs `pip install lupa`, like patches\\garbage_soc_quests\\tests\\garbage_chain_mock_test.py)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with position and inventory, level tick, alife():create, map
spots, game news) and proves:
  * every task of the Radar / X-10 / Pripyat / CNPP / Sarcophagus / Control Monolith chain is handed to EVERY player, once, at the right stage; a late
    joiner (and a respawned player) gets the tasks of the stage that is open now, never a finished one
  * the stash: the decoder is spawned in the hotel room once (coordinates, level vertex, game vertex), the map spot goes to every player, the three
    stash steps follow the hotel zone / the room zone / the decoder in an inventory, the diary text is shown once per player
  * the Sarcophagus fallback: a party that never found the decoder has the flag unset (the restrictor spawns the copy); a replacement is spawned when
    the holder is gone; no replacement while someone holds it or after the door was used
  * Sarcophagus steps: sneak in / Wish Granter / bunker / hidden door / door opened / Control Monolith level
  * Control Monolith: one "Solve the Monolith's secret" step done by all six generators, then the talk with C-Consciousness; the level maker's
    five other generator steps and the kill-all step are never given
  * skipped steps never block: a later flag also ends the earlier tasks; a new Lua VM (a level load) gives nothing that is already done
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
E.__side = "server"
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
E.__level = "coop_l10_pripyat"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.__spots = {}       -- id -> true
E.__synced = {}      -- "id|pid" -> n
E.level.map_add_object_spot_ser = function(id, typ, hint) E.__spots[id] = { typ = typ, hint = hint } end
E.level.map_remove_object_spot = function(id, typ) E.__spots[id] = nil end
E.level.map_sync_spot = function(id, typ, pid) local k = id .. "|" .. tostring(pid); E.__synced[k] = (E.__synced[k] or 0) + 1 end
E.db = { mp_actors = {} }
E.__created = {}     -- { section, x, y, z, lvid, gvid, id }
E.__next_id = 9000
E.__fail_create = false
function E.alife() return { create = function(self, section, pos, lvid, gvid)
	if E.__fail_create then error("create failed") end
	E.__next_id = E.__next_id + 1
	local r = { section = section, x = pos.x, y = pos.y, z = pos.z, lvid = lvid, gvid = gvid, id = E.__next_id }
	E.__created[#E.__created + 1] = r
	return r
end } end
E.__local = nil
E.__news = {}
function E.getLocalActor() return E.__local end
E.game = { translate_string = function(s) return "T:" .. s end }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z), __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:level_vertex_id() return 5 end
	function o:game_vertex_id() return 6 end
	function o:object(sec) local it = self.__items[sec]; if it then return { id = function() return it end } end return nil end
	function o:give_game_news(a, b, c, d, e2, f2) E.__news[#E.__news + 1] = self.__name .. ":" .. a .. ":" .. b end
	E.db.mp_actors[id] = o
	return o
end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_soc_aes"))
setfenv(fn, env)
fn()
E.__env = env
return E
'''

T = {
    "X10A": "x10_start_turn_off_the_radar_quest_task",
    "X10B": "x10_start_leave_the_bunker_and_go_to_pripyat_quest_task",
    "MEET": "pri_start_meet_a_group_of_stalkers_quest_task",
    "FOLLOW": "pri_start_help_the_stalkers_get_to_the_underground_parking_quest_task",
    "CNPP": "pri_start_go_to_cnpp_quest_task",
    "S1": "pri_soc_stash_1_task",
    "S2": "pri_soc_stash_2_task",
    "S3": "pri_soc_stash_3_task",
    "AES": "aes_1_start_go_to_sarcofag_quest_task",
    "W0": "sar_start_get_to_the_monolith_quest_task",
    "W1": "sar_soc_sneak_in_task",
    "W2": "sar_soc_find_wish_task",
    "L1": "sar_soc_lab_1_task",
    "L2": "sar_soc_lab_2_task",
    "L3": "sar_start_open_the_door_to_monolith_management_quest_task",
    "L4": "sar_soc_lab_4_task",
    "C0": "con_start_sneak_into_the_control_room_quest_task",
    "C1": "con_start_destroy_the_monolith_installation_1_quest_task",
    "C2": "con_start_talk_to_the_representative_awareness_quest_task",
}
HIDDEN = ["sar_start_kill_the_monolith_preacher_quest_task", "sar_start_search_the_preacher_body_and_retrieve_the_decoder_quest_task",
          "con_start_destroy_the_monolith_installation_2_quest_task", "con_start_destroy_the_monolith_installation_3_quest_task",
          "con_start_destroy_the_monolith_installation_4_quest_task", "con_start_destroy_the_monolith_installation_5_quest_task",
          "con_start_destroy_the_monolith_installation_6_quest_task", "con_start_kill_all_representatives_of_awareness_quest_task"]

PRI = "coop_l10_pripyat"
CNPP = "coop_l11_stancia_1"
SAR = "coop_l11_sarcofag"
CON = "coop_l11_control_monolith"
GENS = ["CON_MONOLITH_GENERATOR_%d_INFO" % i for i in range(1, 7)]


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    path = os.path.join(PATCH, "gamedata", "scripts", "coop_soc_aes.script")
    st = {}

    def tick(ms=1500):
        E = st["E"]
        E["__time"] = E["__time"] + ms
        for f in list(E["__calls"].values()):
            f()

    def reset(level, keep=False):
        # keep=True: a new Lua VM (level change / reload) with the saved story flags of the old one
        E = lua.execute(PRELUDE, path, st["E"]["__flags"] if keep else None)
        E["__level"] = level
        st["E"] = E
        st["env"] = E["__env"]
        st["env"].install()

    def player(pid, name, x=0.0, y=0.0, z=0.0):
        return st["E"]["__player"](pid, name, x, y, z)

    def put(p, x, y, z):
        st["E"]["__setpos"](p, x, y, z)

    def flag(n):
        return st["E"]["story_flags"]["has_flag"](n)

    def give(n):
        st["E"]["story_flags"]["give_flag"](n)

    def given(task, pid):
        v = st["E"]["__given"][task + "|" + str(pid)]
        return int(v) if v is not None else 0

    def once(key, pids):
        return all(given(T[key], p) == 1 for p in pids)

    def none(key, pids):
        return all(given(T[key], p) == 0 for p in pids)

    def only(keys, pids):
        """exactly these task keys have been given to these players, nothing else"""
        return all(none(k, pids) for k in T if k not in keys) and all(once(k, pids) for k in keys)

    def set_level(lv):
        st["E"]["__level"] = lv

    def created():
        return [(c["section"], round(c["x"], 2), round(c["y"], 2), round(c["z"], 2), int(c["lvid"]), int(c["gvid"]), int(c["id"]))
                for c in st["E"]["__created"].values()]

    def hold(p, section, oid=777):
        p["__items"][section] = oid

    def drop(p, section):
        p["__items"][section] = None

    def news():
        return [st["E"]["__news"][i] for i in range(1, len(st["E"]["__news"]) + 1)]

    # ================================================================== Radar / X-10
    reset("coop_l09_x10")
    a = player(1, "qaa", 0, 0, 0)
    b = player(2, "qab", 0, 0, 0)
    tick()
    check("X-10 before anything: nothing is given", only([], (1, 2)))
    give("RAD_START_GO_TO_RADAR_QUEST_TASK_INFO")
    tick()
    check("Radar step over (X-10 entered): 'Deactivate the Brain Scorcher' for EVERY player, once", only(["X10A"], (1, 2)))
    tick(); tick()
    check("later ticks do not give again", only(["X10A"], (1, 2)))
    c = player(3, "qac")
    tick()
    check("a late joiner gets the open step once", once("X10A", (3,)) and none("X10B", (3,)))
    give("X10_LAB_PRIMARY_SWITCHER_1_DEACTIVATE_INFO")
    tick()
    check("one switcher off: the second step does not start", none("X10B", (1, 2, 3)))
    give("X10_LAB_PRIMARY_SWITCHER_2_DEACTIVATE_INFO")
    d = player(4, "qad")
    tick()
    check("Brain Scorcher off: 'Reach the power plant' (Barkeep's briefing step) for EVERY player incl. the joiner, once", once("X10B", (1, 2, 3, 4)))
    check("Brain Scorcher off: a joiner does not get the finished X-10 step", none("X10A", (4,)))
    give("PRI_FOLLOWERS_LEADER_PHRASE1_1_INFO")
    e = player(5, "qae")
    tick()
    check("Pripyat reached: a joiner does not get the X-10 steps any more", none("X10A", (5,)) and none("X10B", (5,)))

    # ================================================================== Pripyat
    reset(PRI)
    a = player(1, "qaa", 20.0, -2.0, -290.0)
    b = player(2, "qab", 21.0, -2.0, -290.0)
    tick()
    # the party is on Pripyat: the decoder is spawned in the hotel room, the Doctor's task starts
    cr = created()
    check("Pripyat: the decoder is spawned once, in the hotel room (SoC pri_decoder position, node 215353, game vertex 2210)",
          cr == [("dev_decoder", 99.65, 4.9, 123.0, 215353, 2210, 9001)], cr)
    check("Pripyat: flag SOC_AES_DECODER_SPAWNED is set", flag("SOC_AES_DECODER_SPAWNED"))
    check("Pripyat: the stash spot is on the decoder and synced to every player",
          st["E"]["__spots"][9001] is not None and st["E"]["__spots"][9001]["hint"] == "coop_soc_aes_stash_hint"
          and all(st["E"]["__synced"]["9001|%d" % p] is not None for p in (1, 2)))
    check("Pripyat arrival: 'Secret stash at Pripyat' (hotel step) for EVERY player, once, nothing else", only(["S1"], (1, 2)))
    tick(); tick()
    check("no second decoder, no second give", len(created()) == 1 and only(["S1"], (1, 2)))
    # the meeting zone (Pripyat restrictor)
    give("PRI_FOLLOWERS_LEADER_PHRASE1_1_INFO")
    c = player(3, "qac", 20.0, -2.0, -290.0)
    tick()
    check("meeting zone: 'Meet the group' and 'Find the path to the CNPP' for EVERY player, once", once("MEET", (1, 2, 3)) and once("CNPP", (1, 2, 3)))
    check("meeting zone: the follow step is not open yet", none("FOLLOW", (1, 2, 3)))
    check("a late joiner also gets the stash hotel step and its map spot", once("S1", (3,)) and st["E"]["__synced"]["9001|3"] is not None)
    give("PRI_SMART_TERRAIN_1_WALKER_LEADER_IDLE_INFO")
    d = player(4, "qad", 20.0, -2.0, -290.0)
    tick()
    check("the leader spoke: 'Follow the group' for EVERY player incl. the joiner, once", once("FOLLOW", (1, 2, 3, 4)))
    check("the leader spoke: a joiner does not get the finished meeting step", none("MEET", (4,)))
    give("PRI_SMART_TERRAIN_19_ORDINARY_MONOLITH_1_SQUAD_DEAD")
    e = player(5, "qae", 20.0, -2.0, -290.0)
    tick()
    check("one ambush squad dead: the follow step is still open", once("FOLLOW", (5,)))
    give("PRI_SMART_TERRAIN_19_ORDINARY_MONOLITH_2_SQUAD_DEAD")
    f = player(6, "qaf", 20.0, -2.0, -290.0)
    tick()
    check("both ambush squads dead: a joiner does not get the follow step", none("FOLLOW", (6,)))

    # the hotel and the room
    put(a, 104.0, 4.0, 128.0)
    tick()
    check("a player enters the hotel: flag PRI_ACTOR_IN_HOTEL", flag("PRI_ACTOR_IN_HOTEL"))
    check("hotel reached: 'Find the room with the secret stash' for EVERY player, once", once("S2", (1, 2, 3, 4, 5, 6)))
    h = player(8, "qah", 20.0, -2.0, -290.0)
    tick()
    check("hotel reached: a joiner gets the room step and not the finished hotel step", once("S2", (8,)) and none("S1", (8,)))
    check("the room is not entered yet", not flag("PRI_ACTOR_IN_HIDING_PLACE") and none("S3", (1, 2)))
    put(a, 101.0, 4.2, 127.0)
    tick()
    check("a player stands in the room: flag PRI_ACTOR_IN_HIDING_PLACE", flag("PRI_ACTOR_IN_HIDING_PLACE"))
    check("room reached: 'Look the secret stash over' for EVERY player, once", once("S3", (1, 2, 3, 4, 5, 6)))
    check("the decoder is not taken yet", not flag("PRI_MONOLITH_DECODER_GOT"))
    # a player takes the decoder
    hold(a, "dev_decoder", 9001)
    tick()
    check("a player holds the decoder: flag PRI_MONOLITH_DECODER_GOT", flag("PRI_MONOLITH_DECODER_GOT"))
    check("the stash spot is removed", st["E"]["__spots"][9001] is None)
    g = player(7, "qag", 20.0, -2.0, -290.0)
    tick()
    check("decoder got: a joiner gets none of the stash steps", none("S1", (7,)) and none("S2", (7,)) and none("S3", (7,)))
    check("decoder got: 'Secret lab' (enter the secret bunker) is given to EVERY player, once, even on Pripyat", once("L1", (1, 2, 3, 4, 5, 6, 7)))
    # the diary line: every machine shows it once (client side)
    st["E"]["__side"] = "client"
    st["E"]["__local"] = b
    tick(2500); tick(2500)
    check("the diary text 'Pripyat stash' is shown to the local player once", news() == ["qab:T:coop_soc_aes_stash_news_name:T:coop_soc_aes_stash_news_text"], news())
    check("the diary flag of that player is set", flag("SOC_AES_NEWS_QAB"))
    st["E"]["__side"] = "server"
    check("no second decoder after the pickup", len(created()) == 1)
    # a Lua VM restart (level change and back): nothing is spawned again, nothing given again to a ready player is a problem for the engine only
    reset(PRI, keep=True)
    a = player(1, "qaa", 20.0, -2.0, -290.0)
    tick()
    check("a new VM on Pripyat does not spawn a second decoder", len(created()) == 0)
    st["E"]["__side"] = "client"
    st["E"]["__local"] = a
    tick(2500)
    st["E"]["__side"] = "server"
    check("a new VM shows the diary text to a player who has not seen it", len(news()) == 1)
    # the party leaves with the decoder (hotel step already over): CNPP
    reset(CNPP)
    a = player(1, "qaa")
    b = player(2, "qab")
    tick()
    check("CNPP-1: 'Find the entrance to the Sarcophagus' for EVERY player, once; no Pripyat step", only(["AES"], (1, 2)))
    check("CNPP-1: the tick sets its own arrival flag, not the mod's (the level restrictor owns that one)",
          flag("SOC_AES_CNPP_ARRIVED") and not flag("PRI_START_GO_TO_CNPP_QUEST_TASK_INFO"))
    check("CNPP-1: no spawn on this level", len(created()) == 0)

    # party jumped past the stash (no decoder): the stash tasks are never handed out after CNPP-1
    reset(PRI)
    give("PRI_START_GO_TO_CNPP_QUEST_TASK_INFO")
    a = player(1, "qaa", 20.0, -2.0, -290.0)
    tick()
    check("Pripyat after the party reached CNPP-1: no stash step is handed out", none("S1", (1,)) and none("S2", (1,)) and none("S3", (1,)))

    # failed spawn: no flag, so the Sarcophagus restrictor still spawns its copy
    reset(PRI)
    st["E"]["__fail_create"] = True
    a = player(1, "qaa", 20.0, -2.0, -290.0)
    tick()
    check("a failed spawn sets no SPAWNED flag (tried again next tick)", not flag("SOC_AES_DECODER_SPAWNED"))
    st["E"]["__fail_create"] = False
    tick()
    check("the next tick spawns it", flag("SOC_AES_DECODER_SPAWNED") and len(created()) == 1)
    check("no decoder flag without a holder (the Sarcophagus restrictor then spawns the copy)", not flag("PRI_MONOLITH_DECODER_GOT"))

    # ================================================================== Sarcophagus
    reset(SAR)
    a = player(1, "qaa", -29.0, 0.2, 40.0)
    b = player(2, "qab", -29.0, 0.2, 41.0)
    tick()
    check("Sarcophagus arrival: the tick sets its own flag and leaves the mod's one (with its autosave) to the restrictor",
          flag("SOC_AES_SAR_ARRIVED") and not flag("AES_1_START_GO_TO_SARCOFAG_QUEST_TASK_INFO"))
    check("Sarcophagus arrival: 'Get to Monolith' and 'Sneak in to the sarcophagus' for EVERY player, once", only(["W0", "W1"], (1, 2)))
    check("Sarcophagus arrival: no decoder spawn here (the restrictor owns the fallback copy)", len(created()) == 0)
    check("Sarcophagus arrival: no lab step without the decoder", none("L1", (1, 2)))
    put(a, 34.0, 13.0, -16.0)
    c = player(3, "qac", -29.0, 0.2, 40.0)
    tick()
    check("a player is inside the sarcophagus: flag SAR_MONOLITH_FIND", flag("SAR_MONOLITH_FIND"))
    check("inside: 'Find the Wish Granter' for EVERY player incl. the joiner, once", once("W2", (1, 2, 3)))
    check("inside: a joiner does not get the finished 'Sneak in' step", none("W1", (3,)))
    # the secret lab needs the decoder
    put(a, 27.0, 18.0, 28.0)
    tick()
    check("in the bunker corridor WITHOUT the decoder nothing happens", not flag("SAR_SOC_BUNKER") and none("L2", (1, 2, 3)))
    hold(a, "dev_decoder", 4242)
    tick()
    check("a player holds the decoder: flag PRI_MONOLITH_DECODER_GOT (found on the level)", flag("PRI_MONOLITH_DECODER_GOT"))
    check("decoder + bunker: flag SAR_SOC_BUNKER, the 'Find the hidden door' step for EVERY player, once", flag("SAR_SOC_BUNKER") and once("L2", (1, 2, 3)))
    check("decoder + bunker: the 'Enter the secret bunker' step is not handed out any more", none("L1", (1, 2, 3)))
    d = player(4, "qad", -29.0, 0.2, 40.0)
    tick()
    check("a joiner now gets 'Find the hidden door' (the open step), not the bunker step", once("L2", (4,)) and none("L1", (4,)))
    put(a, 49.0, 17.0, 27.0)
    tick()
    check("at the hidden door with the decoder: flag SAR_SECRET_DOOR_FIND", flag("SAR_SECRET_DOOR_FIND"))
    check("at the door: 'Open it using the decoder' for EVERY player, once", once("L3", (1, 2, 3, 4)))
    give("LOCKED_START_OPEN_INFO")
    e = player(5, "qae", -29.0, 0.2, 40.0)
    tick()
    check("the door was opened: 'Find out what is behind the door' for EVERY player incl. the joiner, once", once("L4", (1, 2, 3, 4, 5)))
    check("the door was opened: a joiner does not get 'Open it using the decoder'", none("L3", (5,)))
    give("SAR_MONOLITH_WISH_SPACE_RESTRICTOR_INFO")
    f = player(6, "qaf", -29.0, 0.2, 40.0)
    tick()
    check("the Wish Granter was reached: a joiner gets none of the Wish Granter steps", none("W0", (6,)) and none("W1", (6,)) and none("W2", (6,)))
    check("the Preacher steps are never given", all(given(h, p) == 0 for h in HIDDEN for p in (1, 2, 3, 4, 5, 6)))

    # skipped steps: a door opened by somebody who never entered the zones
    reset(SAR)
    a = player(1, "qaa", -29.0, 0.2, 40.0)
    give("AES_1_START_GO_TO_SARCOFAG_QUEST_TASK_INFO")
    give("LOCKED_START_OPEN_INFO")
    tick()
    check("door opened without any zone: the chain is monotonic (decoder, bunker, door found are set)",
          flag("PRI_MONOLITH_DECODER_GOT") and flag("SAR_SOC_BUNKER") and flag("SAR_SECRET_DOOR_FIND"))
    check("door opened without any zone: only 'what is behind the door' and the open Wish Granter steps are handed out",
          once("L4", (1,)) and none("L1", (1,)) and none("L2", (1,)) and none("L3", (1,)))

    # ---- the decoder insurance
    reset(SAR)
    a = player(1, "qaa", -29.0, 0.2, 40.0)
    b = player(2, "qab", -29.0, 0.2, 41.0)
    give("PRI_MONOLITH_DECODER_GOT")      # a player found it on Pripyat, and is gone with it
    tick(1000)
    for _ in range(100):
        tick(1000)
    check("nobody holds the decoder for 100 s: no replacement yet", len(created()) == 0)
    for _ in range(25):
        tick(1000)
    cr = created()
    check("after 120 s without a holder a replacement is spawned next to a player, once",
          len(cr) == 1 and cr[0][0] == "dev_decoder" and cr[0][4] == 5 and cr[0][5] == 6, cr)
    check("the replacement sets the flag, no second one follows", flag("SOC_AES_DECODER_REPLACED"))
    for _ in range(150):
        tick(1000)
    check("no further replacement", len(created()) == 1)
    reset(SAR)
    a = player(1, "qaa", -29.0, 0.2, 40.0)
    give("PRI_MONOLITH_DECODER_GOT")
    hold(a, "dev_decoder")
    for _ in range(200):
        tick(1000)
    check("a holder in the party: no replacement", len(created()) == 0)
    drop(a, "dev_decoder")
    for _ in range(60):
        tick(1000)
    hold(a, "dev_decoder")
    for _ in range(100):
        tick(1000)
    drop(a, "dev_decoder")
    for _ in range(100):
        tick(1000)
    check("the timer restarts when somebody held it in between (100 s + 100 s apart: no replacement)", len(created()) == 0)
    reset(SAR)
    a = player(1, "qaa", -29.0, 0.2, 40.0)
    give("PRI_MONOLITH_DECODER_GOT")
    give("LOCKED_START_OPEN_INFO")
    for _ in range(300):
        tick(1000)
    check("door already used: no replacement", len(created()) == 0)
    reset(SAR)
    a = player(1, "qaa", -29.0, 0.2, 40.0)
    for _ in range(300):
        tick(1000)
    check("decoder never found (restrictor copy case): the tick spawns nothing", len(created()) == 0)

    # ================================================================== Control Monolith
    reset(CON)
    a = player(1, "qaa", 0, 0, 0)
    b = player(2, "qab", 0, 0, 0)
    tick()
    check("Control Monolith arrival: flag SAR_ENTER_COMMAND_CENTER (SoC sar_enter_command_center)", flag("SAR_ENTER_COMMAND_CENTER"))
    check("Control Monolith arrival: 'Infiltrate the secret lab' for EVERY player, once, nothing else", only(["C0"], (1, 2)))
    give("CON_LAB_PRIMARY_SWITCHER_DEACTIVATE_INFO")
    c = player(3, "qac", 0, 0, 0)
    tick()
    check("control room open: 'Solve the Monolith's secret' for EVERY player incl. the joiner, once", once("C1", (1, 2, 3)))
    check("control room open: a joiner does not get the finished 'Infiltrate' step", none("C0", (3,)))
    for i in range(5):
        give(GENS[i])
    d = player(4, "qad", 0, 0, 0)
    tick()
    check("five generators down: the secret is still open for a joiner, the talk is not", once("C1", (4,)) and none("C2", (1, 2, 3, 4)))
    give(GENS[5])
    e = player(5, "qae", 0, 0, 0)
    tick()
    check("all six generators down: the talk with whoever is behind the Monolith for EVERY player, once", once("C2", (1, 2, 3, 4, 5)))
    check("all six generators down: a joiner does not get the finished 'secret' step", none("C1", (5,)))
    give("CON_SMART_TERRAIN_13_ECOLOG_REPRESENTATIVE_AWARENESS_6_DIALOG_STOP_INFO")
    f = player(6, "qaf", 0, 0, 0)
    tick()
    check("the talk is over (refused): a joiner gets none of the Control Monolith steps", none("C0", (6,)) and none("C1", (6,)) and none("C2", (6,)))
    check("the level maker's other generator steps and the kill-all step are never given", all(given(h, p) == 0 for h in HIDDEN for p in (1, 2, 3, 4, 5, 6)))
    check("the true ending trigger flag is not touched by this patch", not flag("AES_2_THE_END_SPACE_RESTRICTOR_INFO") and not flag("SCN_END_PEACE_PLAYED"))

    # dead / respawned players
    reset(CON)
    a = player(1, "qaa")
    a["__alive"] = False
    give("SAR_ENTER_COMMAND_CENTER")
    tick()
    check("a dead player gets nothing while dead", none("C0", (1,)))
    a["__alive"] = True
    tick()
    check("the same player gets the open step after the respawn, once", once("C0", (1,)))

    print("\n%d checks, %d failed" % (n_checks, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
