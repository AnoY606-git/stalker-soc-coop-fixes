"""Offline check of the SoC zones of garbage_duty (coop_scn_garbage_duty.script), no game.
usage: python zones_mock_test.py     (needs `pip install lupa`, same package as the other mock tests)
Runs the REAL script in a Lua 5.1 VM with an engine mock and drives its 250 ms tick:
  1. box geometry of the five SoC restrictors (rotation convention: the long side of the checkpoint zones follows the road to the Bar)
  2. Gray's hangar (SoC gar_seryi_bandits): gar_seryi_igrok_durak_restrictor / gar_bandits_shuher start the attack at once, gar_seryi_factory
     30 s after the entry (also when the player leaves), any player counts, nothing else (no info, no task) is needed, a far player does nothing
  3. Duty checkpoint: without the pass the guard zone makes the Duty NPCs (not the commander) hostile to THAT player only; the warning voice
     plays for the local player in the warning zone (own language, cooldown); with the pass nobody is attacked and the hostility is undone;
     a hostile player that ran away is forgiven; a dead player's entry is dropped"""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "gamedata", "scripts", "coop_scn_garbage_duty.script")
SND = os.path.join(HERE, "..", "gamedata", "sounds", "characters_voice", "scenario", "coop_l02_garbage")

fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local src = ...
local E = { string = string, table = table, math = math, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber, tostring = tostring,
	type = type, setmetatable = setmetatable, rawget = rawget, error = error, select = select, unpack = unpack, next = next, print = print }
E._G = E
E.__time = 100000
E.__flags = {}
E.__log = {}
E.__sounds = {}
E.__side = "server"
E.__lang = "rus"
E.__local = nil
E.__level = "coop_l02_garbage"
E.__calls = {}
E.__objs = {}     -- id -> npc mock
E.__ids = {}      -- id -> server object mock
E.__existing = {}
local function noop() end
E.printf_msg = function(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
E.time_global = function() return E.__time end
E.OnServer = function() return E.__side == "server" end
E.OnClient = function() return E.__side == "client" end
E.getLocalActor = function() return E.__local end
E.getFS = function() return { exist = function(self, a, p) return E.__existing[(p:gsub("%.ogg$", ""))] == true end } end
E.story_flags = { has_flag = function(n) return E.__flags[n] == true end, give_flag = function(n) E.__flags[n] = true end }
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end,
	object = function() return nil end, object_by_id = function(id) return E.__objs[id] end }
E.alife = function() return { object = function(self, id) return E.__ids[id] end } end
E.db = { mp_actors = {} }
E.game_object = { enemy = "enemy", neutral = "neutral", friend = "friend" }
E.hit = setmetatable({ wound = 1 }, { __call = function() return {} end })
E.coop_scenes = { register = noop }
E.coop_soc_opening = { voice_lang = function() return E.__lang end }
E.game = { translate_string = function(s) return "Language" end }
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(_, path)
	local o = { path = path }
	function o:play(who, d, flags) E.__sounds[#E.__sounds + 1] = path end
	function o:playing() return false end
	function o:stop() end
	return o
end })
function E.__player(pid, x, y, z)
	local o = { __id = pid, __alive = true, __pos = { x = x, y = y, z = z } }
	function o:id() return self.__id end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	E.db.mp_actors[pid] = o
	return o
end
function E.__npc(id, section)
	local o = { rel = {}, hits = 0 }
	function o:alive() return true end
	function o:direction() return { x = 0, y = 0, z = 1 } end
	function o:set_relation(r, who) self.rel[who:id()] = r end
	function o:hit(h) self.hits = self.hits + 1 end
	E.__objs[id] = o
	E.__ids[id] = { section_name = function() return section end }
	return o
end
local env = setmetatable({}, { __index = E })
local f = assert(loadstring(src, "coop_scn_garbage_duty"))
setfenv(f, env)
f()
E.__env = env
function E.__tick(ms)
	E.__time = E.__time + ms
	for _, fn in ipairs(E.__calls) do fn() end
end
return E
'''


def fresh():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    src = open(SCRIPT, encoding="cp1251", errors="replace").read()
    E = lua.execute(PRELUDE, src)
    return lua, E


def run(E, ms=1000, step=250):
    t = 0
    while t < ms:
        E.__tick(step)
        t += step


def flag(E, n):
    return E["__flags"][n] is True


# ---------------------------------------------------------------- 1. geometry
lua, E = fresh()
z = E["__env"].zones_at
GRAY = "GAR_THE_ORDER_TO_KILL_GRAY_INFO"
check("warn zone centre", z(28.319, 4.23, 232.591)["warn"])
check("guard zone centre", z(21.027, 2.358, 237.084)["guard"])
# the guard zone's long side (12.9 m) is its local z axis (sin yaw, 0, cos yaw) = (-0.505, 0, 0.863): along the road to the Bar
check("guard zone: 5 m along the road (NW) is inside", z(21.027 - 0.505 * 5, 2.4, 237.084 + 0.863 * 5)["guard"])
check("guard zone: 5 m across the road is outside (3.15 m half width)", not z(21.027 + 0.863 * 5, 2.4, 237.084 + 0.505 * 5)["guard"])
check("guard zone: the mirrored direction is outside", not z(21.027 + 0.505 * 5, 2.4, 237.084 + 0.863 * 5)["guard"])
check("guard zone: 2 m across, 5 m along inside; height 6 m above is outside", z(21.027 + 0.863 * 2, 2.4, 237.084 + 0.505 * 2)["guard"] and not z(21.027, 8.5, 237.084)["guard"])
check("warn zone: 11 m along its long side is inside, 7 m across is outside",
      z(28.319 + 0.52 * 11, 4.2, 232.591 - 0.854 * 11)["warn"] and not z(28.319 + 0.854 * 7, 4.2, 232.591 + 0.52 * 7)["warn"])
check("far from the checkpoint: no zone", not any(z(100, 1, 100)[k] for k in ("warn", "guard")))
check("Gray's post is inside gar_seryi_factory", z(-63.7, 0.8, 8.4)["factory"])
check("the bandits' spot (-114, 0.4, 11.9) is inside gar_bandits_shuher and gar_seryi_factory", z(-114, 0.4, 11.9)["shuher"] and z(-114, 0.4, 11.9)["factory"])
check("the strip in front of Gray's firing line is gar_seryi_igrok_durak_restrictor", z(-76.5, 3.2, 20)["durak"] and not z(-70, 3.2, 20)["durak"])
check("the Garbage arrival (Cordon road) is in no Gray zone", not any(z(40, 0.5, 225)[k] for k in ("factory", "durak", "shuher")))

# ---------------------------------------------------------------- 2. Gray's hangar
def gray_case(positions, ms, level="coop_l02_garbage"):
    lua, E = fresh()
    E["__level"] = level
    for i, (x, y, z_) in enumerate(positions):
        E.__player(i + 1, x, y, z_)
    run(E, ms)
    return E


E = gray_case([(40, 0.5, 225)], 60000)
check("no player near: no attack, no flag", not flag(E, GRAY))
E = gray_case([(-76.5, 3.2, 20)], 1000)
check("player in gar_seryi_igrok_durak_restrictor: the attack starts at once", flag(E, GRAY))
E = gray_case([(-129, 5.5, 0)], 1000)
check("player in gar_bandits_shuher: the attack starts at once", flag(E, GRAY))
E = gray_case([(-100, 1, -30)], 20000)
check("player in gar_seryi_factory only: not before 30 s", not flag(E, GRAY))
run(E, 15000)
check("player in gar_seryi_factory: the attack follows 30 s after the entry", flag(E, GRAY))
lua, E = fresh()
p = E.__player(1, -100, 1, -30)
run(E, 5000)
p["__pos"]["x"], p["__pos"]["z"] = 40.0, 225.0           # he leaves the zone after 5 s
run(E, 20000)
check("he left after 5 s: not yet (25 s)", not flag(E, GRAY))
run(E, 8000)
check("he left: the timer still runs out (SoC sr_idle@time)", flag(E, GRAY))
lua, E = fresh()
E.__player(1, 40, 0.5, 225)
E.__player(2, -100, 1, -30)
run(E, 31000)
check("any player counts: the second one in the zone starts it", flag(E, GRAY))
lua, E = fresh()
p = E.__player(1, -100, 1, -30)
p["__alive"] = False
run(E, 40000)
check("a dead player does not start it", not flag(E, GRAY))
E = gray_case([(-76.5, 3.2, 20)], 1000, level="coop_l03_agroprom")
check("another level: nothing", not flag(E, GRAY))

# ---------------------------------------------------------------- 3. checkpoint
def setup():
    lua, E = fresh()
    E.__npc(10, "gar_dolg_blokpost")
    E.__npc(11, "gar_dolg_blokpost")
    E.__npc(12, "gar_smart_terrain_8_duty_prapor")       # the commander
    E.__npc(13, "stalker_bandit")
    a = E.__player(1, 40, 0.5, 225)
    b = E.__player(2, 40, 0.5, 225)
    return lua, E, a, b


lua, E, a, b = setup()
run(E, 1000)
check("nobody in a zone: nobody hostile", all(E["__objs"][i]["rel"][1] is None for i in (10, 11, 12, 13)))
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 21.0, 2.4, 237.0     # player 1 steps into the guard zone
run(E, 500)
o10, o11, o12, o13 = (E["__objs"][i] for i in (10, 11, 12, 13))
check("guard zone, no pass: both Duty guards are enemies of player 1", o10["rel"][1] == "enemy" and o11["rel"][1] == "enemy")
check("the other player is not touched", o10["rel"][2] is None and o11["rel"][2] is None)
check("the commander (pass dialog) and a bandit are not touched", o12["rel"][1] is None and o13["rel"][1] is None)
check("SoC zero-power hit is sent", o10["hits"] >= 1)
check("status() counts the hostile player", "hostile=1" in E["__env"].status())
E["__flags"]["GAR_FREE_PASS"] = True
run(E, 500)
check("the pass is given: the guards are neutral again", o10["rel"][1] == "neutral" and o11["rel"][1] == "neutral")
o10["rel"][1] = None
run(E, 1000)
check("with the pass nobody is attacked again", o10["rel"][1] is None)

lua, E, a, b = setup()
E["__flags"]["GAR_FREE_PASS"] = True
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 21.0, 2.4, 237.0
run(E, 1000)
check("pass already given: the guard zone is harmless", E["__objs"][10]["rel"][1] is None)

lua, E, a, b = setup()
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 28.3, 4.2, 232.6     # warning zone only
run(E, 1000)
check("warning zone only: nobody is attacked", E["__objs"][10]["rel"][1] is None)

# calm down: a hostile player that ran far away (and left the guard zone) is forgiven after 15 s
lua, E, a, b = setup()
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 21.0, 2.4, 237.0
run(E, 500)
check("hostile after entering", E["__objs"][10]["rel"][1] == "enemy")
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = -50.0, 0.5, 275.0
run(E, 10000)
check("ran away, 10 s: still hostile", E["__objs"][10]["rel"][1] == "enemy")
run(E, 7000)
check("ran away, 17 s: forgiven (no soft lock)", E["__objs"][10]["rel"][1] == "neutral")
# a dead player: the entry is dropped without touching the (gone) object
lua, E, a, b = setup()
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 21.0, 2.4, 237.0
run(E, 500)
a["__alive"] = False
run(E, 1000)
check("dead player: the hostile entry is gone", "hostile=0" in E["__env"].status())

# the warning voice of the local player (every machine; the host player of a listen host too)
for lang, sub in (("rus", ""), ("eng", "eng\\")):
    lua, E, a, b = setup()
    E["__side"] = "client"
    E["__lang"] = lang
    E["__local"] = a
    path = "characters_voice\\scenario\\coop_l02_garbage\\" + sub + "duty_zoneguard_1"
    E["__existing"][path] = True
    a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 28.3, 4.2, 232.6
    run(E, 1000)
    snd = [E["__sounds"][i] for i in range(1, len(E["__sounds"]) + 1)]
    check("warning voice (%s) plays once in the warning zone" % lang, snd == [path], snd)
    run(E, 10000)
    check("no repeat inside the 25 s cooldown", len(E["__sounds"]) == 1)
    run(E, 20000)
    check("repeats after the cooldown", len(E["__sounds"]) == 2)
    E["__flags"]["GAR_FREE_PASS"] = True
    run(E, 40000)
    check("with the pass: silent", len(E["__sounds"]) == 2)
lua, E, a, b = setup()
E["__side"] = "client"
E["__local"] = a
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 28.3, 4.2, 232.6
run(E, 1000)
check("recording missing: silent, no error", len(E["__sounds"]) == 0 and E["__env"].status() is not None)
lua, E, a, b = setup()
E["__side"] = "client"
E["__local"] = None
E["__existing"]["characters_voice\\scenario\\coop_l02_garbage\\duty_zoneguard_1"] = True
a["__pos"]["x"], a["__pos"]["y"], a["__pos"]["z"] = 28.3, 4.2, 232.6
run(E, 1000)
check("a machine without a local actor (dedicated server) plays nothing", len(E["__sounds"]) == 0)
check("a client machine does not change relations or flags", E["__objs"][10]["rel"][1] is None and not flag(E, GRAY))

# ---------------------------------------------------------------- 4. files
# Russian: duty_zoneguard_1.ogg is already in the mod (scenario\coop_l02_garbage\), English: Steam SoC, shipped by this patch under eng\
pth = os.path.join(SND, "eng", "duty_zoneguard_1.ogg")
d = open(pth, "rb").read() if os.path.isfile(pth) else b""
check("shipped: eng/duty_zoneguard_1.ogg (Ogg, SoC original, 27230 bytes)", d[:4] == b"OggS" and len(d) == 27230, len(d))

print("ALL PASS" if fails == 0 else "%d FAILED" % fails)
sys.exit(1 if fails else 0)
