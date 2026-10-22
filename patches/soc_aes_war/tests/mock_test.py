"""Offline check (no game) of coop_soc_aes_war.script.
usage: python mock_test.py     (needs `pip install lupa`, like patches\\soc_aes_military\\tests\\mock_test.py)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (players, helicopters with SetEnemy / ClearEnemy / isVisible, Monolith soldiers, the
server entity list with alife():create, a script car with a gun, story flags, the config file) and proves:
  * nothing happens off CNPP-1, or with no living player
  * the helicopters stay quiet until the go flag (party on the SoC actor_ready line, or already west of x 905); then
      - a helicopter shoots the nearest VISIBLE Monolith soldier within 250 m, never an invisible one, never one beyond 250 m
      - a player is only a target inside the four SoC helicopter zones, at most 2 helicopters hunt players at once, players outside the zones are left alone
      - helicopters farther than 350 m from every player are asleep (their enemy is cleared), at most 3 are armed, the nearest ones
      - a target is re-set after 4 s (a logic section switch clears the enemy), rockets are always off
      - a helicopter that is shot down is counted: SOC_AESW_DOWN_1..3 in order, once each, a 4th changes nothing
  * the BTR: created once (section, route point, flag), only when a player is within 450 m, never twice (new Lua VM, registry loss, existing entity),
      never when the section / route is missing, retried at most 3 times after errors; its gun fires at the nearest visible Monolith soldier within
      90 m and stops otherwise, never at players; a destroyed (released) BTR is not created again
  * the config switches (helicopters / btr) turn each part off
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
local script_path, keep_flags, cfg = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__calls = {}
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return true end
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
function E.__vec(x, y, z) return E.vector():set(x, y, z) end
local flags = keep_flags or {}
E.__flags = flags
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
E.__level = "coop_l11_stancia_1"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.__paths = {}
E.level.patrol_path_exists = function(n) return E.__paths[n] ~= nil end
function E.patrol(n)
	local p = E.__paths[n]
	return { count = function(self) return #p end, point = function(self, i) return p[i + 1].pos end,
		level_vertex_id = function(self, i) return p[i + 1].lv end, game_vertex_id = function(self, i) return p[i + 1].gv end }
end
E.clsid = { script_stalker = 7 }
E.CCar = { eWpnActivate = 3, eWpnAutoFire = 5, eWpnDesiredDir = 1, eWpnDesiredPos = 2, eWpnFire = 4 }
E.db = { mp_actors = {}, heli = {}, storage = {}, spawned_vertex_by_id = {} }
-- server entities
E.__ents = {}                 -- id -> entity
E.__story = {}                -- story id -> id
E.__created = {}
E.__next_id = 500
E.__create_fail = false
E.__create_throw = false
E.__sections = { soc_aes_btr = true }
function E.system_ini() return { section_exist = function(self, s) return E.__sections[s] == true end } end
function E.get_story_object_id(s) return E.__story[s] end
function E.unregister_story_id(s) E.__story[s] = nil end
function E.add_story_object(id, s) E.__story[s] = id end
function E.alife() return {
	object = function(self, i) return E.__ents[i] end,
	create = function(self, sect, pos, lv, gv)
		if E.__create_throw then error("boom") end
		if E.__create_fail then return nil end
		E.__next_id = E.__next_id + 1
		local se = { id = E.__next_id, __sect = sect, position = pos, lv = lv, gv = gv }
		function se:section_name() return self.__sect end
		E.__ents[se.id] = se
		E.__story[sect] = se.id
		E.__created[#E.__created + 1] = { sect = sect, pos = pos, lv = lv, gv = gv, id = se.id }
		return se
	end } end
-- config file
E.__cfg = cfg or { helicopters = true, btr = true }
function E.ini_file(n)
	return { section_exist = function(self, s) return s == "soc_aes_war" end,
		line_exist = function(self, s, k) return E.__cfg[k] ~= nil end,
		r_bool = function(self, s, k) return E.__cfg[k] end }
end
-- players
local function mk(id, name, x, y, z, alive)
	local o = { __id = id, __name = name, __alive = alive ~= false, __pos = E.vector():set(x, y, z) }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	return o
end
function E.__player(id, name, x, y, z)
	local o = mk(id, name, x, y, z)
	E.db.mp_actors[id] = o
	return o
end
function E.__setpos(o, x, y, z) o.__pos = E.vector():set(x, y, z) end
-- Monolith soldiers
function E.__monolith(id, x, y, z, community)
	local o = mk(id, "mono" .. id, x, y, z)
	function o:clsid() return 7 end
	function o:character_community() return community or "monolith" end
	E.db.storage[id] = { object = o }
	return o
end
-- helicopters
E.__visible = {}      -- "heliid|targetid" -> true
function E.__heli(id, n, x, y, z, fullname)
	local o = mk(id, fullname or ("aes_1_heli_attack_" .. n), x, y, z)
	local h = { m_dead = false, m_use_mgun_on_attack = false, m_use_rocket_on_attack = true, __enemy = nil, __set = 0, __clear = 0 }
	function h:SetEnemy(t) self.__enemy = t; self.__set = self.__set + 1 end
	function h:ClearEnemy() self.__enemy = nil; self.__clear = self.__clear + 1 end
	function h:isVisible(t) return E.__visible[id .. "|" .. t:id()] == true end
	function o:get_helicopter() return h end
	o.__h = h
	E.db.heli[id] = o
	return o
end
function E.__bad_heli(id, n, x, y, z)
	local o = mk(id, "aes_1_heli_attack_" .. n, x, y, z)
	function o:get_helicopter() error("broken helicopter") end
	E.db.heli[id] = o
	return o
end
-- the BTR (a script car with a gun)
E.__car_log = {}
function E.__btr(id, x, y, z, hasweapon)
	local o = mk(id, "btr", x, y, z)
	local car = { __weapon = hasweapon ~= false, __fire = 0, __pos = nil, __vis_throw = false }
	function car:HasWeapon() return self.__weapon end
	function car:Action(a, v) E.__car_log[#E.__car_log + 1] = a .. "=" .. v; if a == 4 then self.__fire = v end end
	function car:SetParam(a, v) if a == 2 then self.__pos = v end end
	function car:IsObjectVisible(t)
		if self.__vis_throw then error("no vis") end
		return E.__visible["car|" .. t:id()] == true
	end
	function o:get_car() return car end
	o.__car = car
	E.db.storage[id] = { object = o }
	return o
end
local f = io.open(script_path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_soc_aes_war"))
setfenv(fn, env)
fn()
E.__env = env
return E
'''

CNPP = "coop_l11_stancia_1"
PRI = "coop_l10_pripyat"
ARRIVE = (919.0, 0.0, -292.0)
READY = (926.0, -0.1, -170.6)
ROUTE = "aes_1_smart_terrain_5_walker_army_ordinary_7_walk"
SPOT = (412.0, 0.0, -128.0)


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    path = os.path.join(PATCH, "gamedata", "scripts", "coop_soc_aes_war.script")
    st = {}

    def tick(ms=1100):
        E = st["E"]
        E["__time"] = E["__time"] + ms
        for f in list(E["__calls"].values()):
            f()

    def reset(level=CNPP, keep=False, cfg=None, route=True, keep_ents=False):
        old = st.get("E")
        c = None
        if cfg is not None:
            c = lua.table_from(cfg)
        E = lua.execute(PRELUDE, path, old["__flags"] if keep and old is not None else None, c)
        E["__level"] = level
        if route:
            pts = [{"pos": E["__vec"](100.0 + i, 0.0, -50.0), "lv": 1000 + i, "gv": 50 + i} for i in range(12)]
            pts[9] = {"pos": E["__vec"](*SPOT), "lv": 4242, "gv": 77}
            E["__paths"][ROUTE] = lua.table_from([lua.table_from(p) for p in pts])
        if keep_ents and old is not None:
            E["__ents"] = old["__ents"]
            E["__story"] = old["__story"]
        st["E"] = E
        st["env"] = E["__env"]
        st["env"].install()

    def player(pid, name, pos=ARRIVE):
        return st["E"]["__player"](pid, name, pos[0], pos[1], pos[2])

    def put(o, pos):
        st["E"]["__setpos"](o, pos[0], pos[1], pos[2])

    def flag(n):
        return st["E"]["story_flags"]["has_flag"](n)

    def vis(hid, tid, yes=True):
        st["E"]["__visible"][str(hid) + "|" + str(tid)] = True if yes else None

    def enemy(h):
        e = h["__h"]["__enemy"]
        return None if e is None else int(e["id"](e))

    def created():
        return [st["E"]["__created"][i] for i in range(1, len(st["E"]["__created"]) + 1)]

    # ================================================================== off CNPP-1 / nobody
    reset(PRI)
    a = player(1, "qaa", READY)
    tick(); tick()
    check("off CNPP-1: no go flag, no BTR", not flag("SOC_AESW_GO") and len(created()) == 0)
    reset(CNPP)
    tick(); tick()
    check("no living player: no go flag", not flag("SOC_AESW_GO"))
    a = player(1, "qaa", ARRIVE)
    a["__alive"] = False
    tick()
    check("only a dead player: no go flag", not flag("SOC_AESW_GO"))

    # ================================================================== the go flag
    reset(CNPP)
    a = player(1, "qaa", ARRIVE)
    h1 = st["E"]["__heli"](201, 1, 905.0, 20.0, -150.0)
    m1 = st["E"]["__monolith"](301, 880.0, 0.0, -150.0)
    vis(201, 301)
    tick(); tick()
    check("arrival point: no go flag", not flag("SOC_AESW_GO"))
    check("before the go flag the helicopter has no enemy", enemy(h1) is None and h1["__h"]["__set"] == 0)
    put(a, READY)
    tick()
    check("the party on the SoC actor_ready line gives the go flag", flag("SOC_AESW_GO"))
    reset(CNPP)
    a = player(1, "qaa", (880.0, 0.0, -100.0))
    tick()
    check("a player already west of x 905 gives it too (teleport / late start)", flag("SOC_AESW_GO"))

    # ================================================================== helicopters vs Monolith
    reset(CNPP)
    a = player(1, "qaa", (850.0, 0.0, -150.0))
    h1 = st["E"]["__heli"](201, 1, 880.0, 20.0, -150.0)
    mA = st["E"]["__monolith"](301, 840.0, 0.0, -150.0)          # 40 m from the heli, 10 m from the player
    mB = st["E"]["__monolith"](302, 870.0, 0.0, -150.0)          # 10 m from the heli
    mC = st["E"]["__monolith"](303, 600.0, 0.0, -150.0)          # far
    mZ = st["E"]["__monolith"](304, 872.0, 0.0, -140.0, "zombied")
    tick()
    check("go flag given", flag("SOC_AESW_GO"))
    check("no visible target: the helicopter is not armed", enemy(h1) is None)
    vis(201, 301); vis(201, 303); vis(201, 304)
    tick()
    check("the nearest VISIBLE Monolith soldier is the target (the closer invisible one and the zombified one are not)", enemy(h1) == 301, enemy(h1))
    check("machine gun on, rockets off", h1["__h"]["m_use_mgun_on_attack"] is True and h1["__h"]["m_use_rocket_on_attack"] is False)
    sets = h1["__h"]["__set"]
    tick(1000)
    check("the same target is not set again at once", h1["__h"]["__set"] == sets, (sets, h1["__h"]["__set"]))
    tick(4000)
    check("it is set again after 4 s (a section switch clears the enemy)", h1["__h"]["__set"] == sets + 1, h1["__h"]["__set"])
    vis(201, 302)
    tick()
    check("a closer soldier that becomes visible takes over", enemy(h1) == 302, enemy(h1))
    vis(201, 302, False); vis(201, 301, False); vis(201, 303, False); vis(201, 304, False)
    tick()
    check("nothing visible: the enemy is cleared", enemy(h1) is None and h1["__h"]["__clear"] >= 1)
    mC["__pos"] = st["E"]["__vec"](640.0, 0.0, -150.0)    # 240 m from the heli
    vis(201, 303)
    tick()
    check("a visible soldier 240 m away is a target (range 250)", enemy(h1) == 303, enemy(h1))
    mC["__pos"] = st["E"]["__vec"](620.0, 0.0, -150.0)    # 260 m
    tick(5000)
    check("a visible soldier 260 m away is not", enemy(h1) is None, enemy(h1))

    # ================================================================== helicopters vs players
    reset(CNPP)
    a = player(1, "qaa", (860.0, 0.0, -150.0))                    # outside every SoC helicopter zone
    h1 = st["E"]["__heli"](201, 1, 880.0, 20.0, -150.0)
    vis(201, 1)
    tick(); tick()
    check("a player outside the SoC zones is never a target", enemy(h1) is None)
    ZONE1 = (781.8, 0.0, -162.2)                                  # centre of aes_actor_heli
    put(a, ZONE1)
    h1["__pos"] = st["E"]["__vec"](790.0, 20.0, -150.0)
    vis(201, 1)
    tick(); tick()
    check("a player inside the first SoC zone is a target", enemy(h1) == 1, enemy(h1))
    put(a, (781.8 + 135.8, 0.0, -162.2 + 137.7))                    # the third box of the same zone
    h1["__pos"] = st["E"]["__vec"](900.0, 20.0, -20.0)
    tick(5000)
    check("the offset boxes of a zone count too", enemy(h1) == 1, enemy(h1))
    put(a, (628.1, 0.0, -55.2))
    h1["__pos"] = st["E"]["__vec"](650.0, 20.0, -60.0)
    tick(5000)
    check("the third SoC zone too", enemy(h1) == 1, enemy(h1))
    put(a, (470.6, 0.0, -14.9))
    h1["__pos"] = st["E"]["__vec"](480.0, 20.0, -20.0)
    tick(5000)
    check("the fourth SoC zone too", enemy(h1) == 1, enemy(h1))
    put(a, (730.8, 12.0, -46.2))
    h1["__pos"] = st["E"]["__vec"](740.0, 20.0, -40.0)
    tick(5000)
    check("the second SoC zone (y 12 m up is still inside)", enemy(h1) == 1, enemy(h1))
    put(a, (730.8, 40.0, -46.2))
    tick(5000)
    check("a player 40 m above the zone is not", enemy(h1) is None, enemy(h1))
    put(a, ZONE1)
    h1["__pos"] = st["E"]["__vec"](1200.0, 20.0, -150.0)
    tick(5000)
    check("the helicopter is out of range (300 m) and asleep (350 m)", enemy(h1) is None)

    # at most 2 helicopters hunt players, the third one takes a Monolith soldier
    reset(CNPP)
    a = player(1, "qaa", ZONE1)
    hs = [st["E"]["__heli"](210 + i, i, 790.0 + i, 20.0, -150.0) for i in range(1, 4)]
    m = st["E"]["__monolith"](301, 800.0, 0.0, -160.0)
    for i in range(1, 4):
        vis(210 + i, 1)
        vis(210 + i, 301)
    tick(); tick()
    ens = [enemy(h) for h in hs]
    check("3 helicopters near one player: 2 hunt the player, the 3rd shoots the Monolith soldier", sorted([e for e in ens if e is not None]) == [1, 1, 301], ens)

    # at most 3 armed, the nearest ones
    reset(CNPP)
    a = player(1, "qaa", (840.0, 0.0, -60.0))
    m = st["E"]["__monolith"](301, 800.0, 0.0, -160.0)
    hs = []
    for i in range(1, 6):
        h = st["E"]["__heli"](220 + i, i, 800.0 + 20 * i, 20.0, -150.0)    # 20, 40, 60, 80, 100 m
        vis(220 + i, 301)
        hs.append(h)
    tick(); tick()
    ens = [enemy(h) for h in hs]
    check("5 helicopters in range: only the 3 nearest are armed", [e is not None for e in ens] == [True, True, True, False, False], ens)
    check("armed count", int(st["env"].armed_count()) == 3, st["env"].armed_count())
    # a helicopter of another mod object is ignored
    x = st["E"]["__heli"](299, 1, 801.0, 20.0, -150.0, "esc_helicopter_go_to_agroprom_1")
    vis(299, 301)
    tick(5000)
    check("only aes_1_heli_attack_* helicopters are used (a Cordon helicopter gets no enemy)", enemy(x) is None and int(st["env"].armed_count()) == 3)

    # asleep when far from every player
    reset(CNPP)
    a = player(1, "qaa", (500.0, 0.0, -150.0))
    h = st["E"]["__heli"](201, 1, 900.0, 20.0, -150.0)           # 400 m
    m = st["E"]["__monolith"](301, 880.0, 0.0, -150.0)
    vis(201, 301)
    tick(); tick()
    check("a helicopter 400 m from every player stays asleep", enemy(h) is None)
    put(a, (700.0, 0.0, -150.0))                                   # 200 m
    tick()
    check("200 m from a player it wakes up", enemy(h) == 301, enemy(h))
    put(a, (500.0, 0.0, -150.0))
    tick()
    check("when the player leaves it goes back to sleep and its enemy is cleared", enemy(h) is None)

    # ================================================================== shot down helicopters
    reset(CNPP)
    a = player(1, "qaa", (850.0, 0.0, -150.0))
    hs = [st["E"]["__heli"](230 + i, i, 880.0 + i, 20.0, -150.0) for i in range(1, 6)]
    tick()
    check("5 helicopters alive: no 'down' flag", not flag("SOC_AESW_DOWN_1"))
    for i, expect in enumerate([1, 2, 3], 1):
        h = hs[i - 1]
        h["__h"]["m_dead"] = True
        st["E"]["db"]["heli"][230 + i] = None          # bind_heli.heli_die removes it from db.heli
        tick()
        check("helicopter %d shot down: flag SOC_AESW_DOWN_%d" % (i, expect), flag("SOC_AESW_DOWN_%d" % expect) and (expect == 3 or not flag("SOC_AESW_DOWN_%d" % (expect + 1))))
    hs[3]["__h"]["m_dead"] = True
    st["E"]["db"]["heli"][234] = None
    tick(); tick()
    check("a 4th one changes nothing", flag("SOC_AESW_DOWN_3") and not flag("SOC_AESW_DOWN_4"))
    reset(CNPP)
    a = player(1, "qaa", (850.0, 0.0, -150.0))
    h = st["E"]["__heli"](240, 1, 880.0, 20.0, -150.0)
    tick()
    st["E"]["db"]["heli"][240] = None                  # went offline, not dead
    tick(); tick()
    check("a helicopter that only left the online list (not dead) is not counted", not flag("SOC_AESW_DOWN_1"))

    # ================================================================== the BTR
    reset(CNPP)
    a = player(1, "qaa", ARRIVE)
    tick(); tick()
    check("BTR: player 500+ m from the spot: not created", len(created()) == 0)
    put(a, (800.0, 0.0, -150.0))                               # 400 m from (412,-128)
    tick()
    cr = created()
    check("BTR: created once when a player is within 450 m", len(cr) == 1, len(cr))
    c = cr[0]
    check("BTR: section soc_aes_btr at the route point 9 with the route's own level / game vertex",
          c["sect"] == "soc_aes_btr" and abs(c["pos"]["x"] - SPOT[0]) < 0.01 and int(c["lv"]) == 4242 and int(c["gv"]) == 77, (c["sect"], c["lv"], c["gv"]))
    check("BTR: flag set, spawned vertex remembered", flag("SOC_AESW_BTR_MADE") and int(st["E"]["db"]["spawned_vertex_by_id"][c["id"]]) == 4242)
    tick(); tick(); tick()
    check("BTR: not created again", len(created()) == 1)
    # reload: new VM, flags and entities kept
    reset(CNPP, keep=True, keep_ents=True)
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    tick(); tick()
    check("BTR: after a reload (flag + entity) nothing new is created", len(created()) == 0)
    # the registry lost it but the entity and the flag are there
    st["E"]["__story"]["soc_aes_btr"] = None
    reset(CNPP, keep=True, keep_ents=True)
    st["E"]["__story"]["soc_aes_btr"] = None
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    tick(); tick()
    check("BTR: registry loss: the entity is found, nothing new is created", len(created()) == 0)
    # destroyed BTR (released) with the flag: stays gone
    for k in list(st["E"]["__ents"].keys()):
        st["E"]["__ents"][k] = None
    st["E"]["__story"]["soc_aes_btr"] = None
    tick(); tick()
    check("BTR: a destroyed (released) BTR is not created again", len(created()) == 0)
    # the flag is lost but the entity exists
    reset(CNPP)
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    st["E"]["__ents"][777] = lua.eval("function(i) local s = { id = i }; function s:section_name() return 'soc_aes_btr' end; return s end")(777)
    tick(); tick()
    check("BTR: flag lost but an entity of the section exists: no second one, flag restored", len(created()) == 0 and flag("SOC_AESW_BTR_MADE"))
    # missing things
    reset(CNPP, route=False)
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    tick(); tick()
    check("BTR: route missing: nothing created, no error", len(created()) == 0 and not flag("SOC_AESW_BTR_MADE"))
    reset(CNPP)
    st["E"]["__sections"]["soc_aes_btr"] = None
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    tick(); tick(); tick()
    check("BTR: section missing from system.ltx: nothing created", len(created()) == 0 and not flag("SOC_AESW_BTR_MADE"))
    reset(CNPP)
    st["E"]["__create_throw"] = True
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    for _ in range(12):
        tick(6000)
    check("BTR: alife():create raises: no flag, no crash, at most 3 tries", not flag("SOC_AESW_BTR_MADE") and len(created()) == 0)
    st["E"]["__create_throw"] = False
    st["E"]["__create_fail"] = True
    for _ in range(3):
        tick(6000)
    check("BTR: after 3 failed tries it gives up (create returning nil counted)", len(created()) == 0 and not flag("SOC_AESW_BTR_MADE"))
    st["E"]["__create_fail"] = False
    for _ in range(3):
        tick(6000)
    check("BTR: ... and does not try a 4th time", len(created()) == 0)

    # ================================================================== the BTR gun
    reset(CNPP)
    a = player(1, "qaa", (500.0, 0.0, -150.0))
    tick()
    bid = created()[0]["id"]
    ob = st["E"]["__btr"](bid, SPOT[0], SPOT[1], SPOT[2])
    car = ob["__car"]
    mA = st["E"]["__monolith"](301, 380.0, 0.0, -128.0)            # 32 m
    mB = st["E"]["__monolith"](302, 330.0, 0.0, -128.0)            # 82 m
    mC = st["E"]["__monolith"](303, 300.0, 0.0, -128.0)            # 112 m
    tick()
    check("BTR gun: nobody visible: not firing", int(car["__fire"]) == 0)
    st["E"]["__visible"]["car|303"] = True
    tick()
    check("BTR gun: a visible soldier beyond 90 m is not shot at", int(car["__fire"]) == 0)
    st["E"]["__visible"]["car|302"] = True
    tick()
    check("BTR gun: a visible soldier within 90 m: fire", int(car["__fire"]) == 1)
    check("BTR gun: aims at him", car["__pos"] is not None and abs(car["__pos"]["x"] - 330.0) < 0.01)
    st["E"]["__visible"]["car|301"] = True
    tick()
    check("BTR gun: the nearest visible one is chosen", car["__pos"] is not None and abs(car["__pos"]["x"] - 380.0) < 0.01)
    st["E"]["__visible"]["car|301"] = None
    st["E"]["__visible"]["car|302"] = None
    tick()
    check("BTR gun: stops firing when nobody is visible", int(car["__fire"]) == 0)
    # never at players / the army
    put(a, (SPOT[0] + 10.0, 0.0, SPOT[2]))
    st["E"]["__visible"]["car|1"] = True
    tick()
    check("BTR gun: never fires at a player", int(car["__fire"]) == 0)
    # visibility call raising: fall back to a 50 m limit
    car["__vis_throw"] = True
    tick()
    check("BTR gun: if the visibility call fails only soldiers within 50 m count (the nearest is 32 m)", int(car["__fire"]) == 1)
    mA["__pos"] = st["E"]["__vec"](340.0, 0.0, -128.0)      # 72 m
    tick()
    check("BTR gun: ... and the 72 m one does not", int(car["__fire"]) == 0)
    car["__vis_throw"] = False
    # a car without a gun
    st["E"]["db"]["storage"][bid]["object"]["__car"]["__weapon"] = False
    st["E"]["__visible"]["car|301"] = True
    mA["__pos"] = st["E"]["__vec"](380.0, 0.0, -128.0)
    tick()
    check("BTR gun: a car without a weapon does not error and does not fire", int(car["__fire"]) == 0)
    errs = [st["E"]["__log"][i] for i in range(1, len(st["E"]["__log"]) + 1) if "err" in st["E"]["__log"][i].lower()]
    check("no script error was logged in the whole BTR run", len(errs) == 0, errs[:3])

    # ================================================================== switches
    reset(CNPP, cfg={"helicopters": False, "btr": True})
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    h = st["E"]["__heli"](201, 1, 830.0, 20.0, -150.0)
    m = st["E"]["__monolith"](301, 800.0, 0.0, -160.0)
    vis(201, 301)
    tick(); tick()
    check("switch helicopters = false: no enemy, the BTR still comes", enemy(h) is None and len(created()) == 1)
    reset(CNPP, cfg={"helicopters": True, "btr": False})
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    h = st["E"]["__heli"](201, 1, 830.0, 20.0, -150.0)
    m = st["E"]["__monolith"](301, 800.0, 0.0, -160.0)
    vis(201, 301)
    tick(); tick()
    check("switch btr = false: the helicopter shoots, no BTR", enemy(h) == 301 and len(created()) == 0)

    # ================================================================== new Lua VM, errors
    reset(CNPP)
    a = player(1, "qaa", (800.0, 0.0, -150.0))
    st["E"]["__bad_heli"](201, 1, 830.0, 20.0, -150.0)
    m = st["E"]["__monolith"](301, 800.0, 0.0, -160.0)
    tick(); tick()
    check("a helicopter object that raises does not stop the BTR", len(created()) == 1)
    errs = [st["E"]["__log"][i] for i in range(1, len(st["E"]["__log"]) + 1) if "TICKERR" in st["E"]["__log"][i]]
    check("no tick error escaped", len(errs) == 0, errs[:2])
    reset(CNPP)
    st["env"].install()
    check("install() twice in one VM: the older tick ends itself, the newer keeps running",
          st["E"]["__calls"][1]() is True and st["E"]["__calls"][2]() is False)

    print("\n%d checks, %d FAIL" % (n_checks, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
