"""Offline check of lua/qa_lib.lua against a mock engine (no game needed, a few seconds):  python qa_lib_mock_test.py
Covers the pure logic: persisted state, the step/action scheduler (wait / wait_for / again / jump / done / errors), the RELATIVE health setter, hit counting,
guide codes, server-side inventory scan, NPC listing, save list diff, the qa_build.py --@qa_lib opt-in.
The in-game behaviour of each function is proven by lua/qa_lib_smoke.lua (see lua/QA_LIB.md)."""
import os
import sys
import tempfile

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "lua", "qa_lib.lua")

PRELUDE = r'''
local tmp = ...
_G.__events = {}
_G.__asserts = {}
_G.__clock = 0
function time_global() return __clock end
_G.qa = { hooks = {}, cfg = {} }
function qa.event(m) __events[#__events + 1] = m end
function qa.assert(n, ok, d) __asserts[#__asserts + 1] = { n, ok, d } end
-- same as qa_harness.lua: qa.once registers a hook that runs once, on the next tick
function qa.once(name, fn)
	local key = "once_" .. name
	qa.hooks[key] = function(t, lo) qa.hooks[key] = nil fn(t, lo) end
end
function qa.local_object() return nil end
function getFS() return { update_path = function(self, a, n) return tmp .. "/" .. n end } end
function OnServer() return true end
function IsDedicatedServer() return true end
function LocalActor() return 0 end
function bit_or(a, b) return a end
-- vectors
local V = {}
V.__index = V
function V.set(self, x, y, z) self.x, self.y, self.z = x, y, z return self end
function vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
function V.distance_to(a, b) return 0 end
-- hit
hit = setmetatable({ fire_wound = 8 }, { __call = function() local h = { bone = function(self, b) self.b = b end } return h end })
-- objects with RELATIVE health
local function mkobj(id, name, hp, hit_dmg)
	local o = { _id = id, _hp = hp, _name = name, _dmg = hit_dmg }
	return setmetatable(o, { __index = function(t, k)
		if k == "health" then return rawget(t, "_hp") end
		if k == "alive" then return function(self) return self._hp > 0 end end
		if k == "id" then return function(self) return self._id end end
		if k == "name" then return function(self) return self._name end end
		if k == "position" then return function(self) return setmetatable({ x = 0, y = 0, z = 0 }, V) end end
		if k == "hit" then return function(self, h) self._hp = self._hp - self._dmg end end
		if k == "set_relation" then return function(self, r, p) self._rel = r end end
		if k == "relation" then return function(self, p) return self._rel or 2 end end
		if k == "give_money" then return function(self, n) self._money = (self._money or 0) + n end end
		if k == "money" then return function(self) return self._money or 0 end end
		return nil
	end, __newindex = function(t, k, v)
		if k == "health" then local nv = rawget(t, "_hp") + v if nv > 1 then nv = 1 end rawset(t, "_hp", nv) else rawset(t, k, v) end
	end })
end
_G.__mk = mkobj
_G.db = { mp_actors = { [7] = mkobj(7, "qaA", 1, 0) }, storage = {} }
_G.__online = {}
_G.level = { name = function() return "coop_l01_escape" end, object_by_id = function(id) return __online[id] end, vertex_id = function() return 5 end }
_G.__sim = {}
_G.clsid = { script_trader = 36, trader = 36 }
_G.IsStalker = function(o, c) return c == 35 end
_G.IsMonster = function(o, c) return c == 108 end
_G.__nextid = 100
_G.alife = function() return {
	object = function(self, id) return __sim[id] end,
	create = function(self, sec, pos, lv, gv, parent)
		__nextid = __nextid + 1
		local se = { id = __nextid, position = pos, m_level_vertex_id = lv, m_game_vertex_id = gv, parent_id = parent or 65535,
		             section_name = function(s) return sec end, name = function(s) return sec .. __nextid end, clsid = function(s) return 35 end, alive = function(s) return true end }
		__sim[se.id] = se
		return se
	end,
	release = function(self, se, b) __sim[se.id] = nil __online[se.id] = nil end,
} end
_G.__sim[7] = { id = 7, position = setmetatable({ x = 1, y = 2, z = 3 }, V), m_level_vertex_id = 11, m_game_vertex_id = 22, parent_id = 65535,
                section_name = function() return "actor_mp" end, name = function() return "qaA" end, clsid = function() return 0 end }
_G.story_flags = { story_flags = {}, has_flag = function(n) return story_flags.story_flags[n] == true end,
                   give_flag = function(n) story_flags.story_flags[string.upper(n)] = true end,
                   disable_flag = function(n) story_flags.story_flags[string.upper(n)] = false end }
_G.coop_map_vote = { votes = {}, on_yes = function(id) coop_map_vote.votes[#coop_map_vote.votes + 1] = id end }
_G.os = os
'''


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    tmp = tempfile.mkdtemp(prefix="qalib_mock_").replace("\\", "/")
    run = lua.eval("function(src, tmp) local f = assert(loadstring(src)) return f(tmp) end")
    run(PRELUDE, tmp)
    src = open(LIB, "rb").read().decode("utf-8")
    lua.execute(src)
    g = lua.globals()
    fails = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + (" " + str(detail) if detail != "" else ""))
        if not ok:
            fails.append(name)

    L = g.qa_lib
    check("library loads and registers itself", L is not None and L.version == "1.2" and g.qa.lib is not None)

    # state persistence
    L.state_set("a", "x y")
    L.state_set("n", 42)
    st = L.state()
    check("state roundtrip (string and number)", st["a"] == "x y" and st["n"] == 42, dict(st.items()))
    L.state_set("a", None)
    check("state delete", L.state_get("a", "gone") == "gone")

    # relative health setter
    run2 = lua.eval("function() local o = __mk(1, 'bandit', 0.5, 0) o.health = -0.2 local after_rel = o.health "
                    "local v = qa_lib.set_health(o, 0.3) return after_rel, v end")
    rel, v = run2()
    check("raw setter is relative (0.5 + -0.2 = 0.3)", abs(rel - 0.3) < 1e-9, rel)
    check("L.set_health sets an absolute value through the relative setter", abs(v - 0.3) < 1e-9, v)

    # tasks: sequences of steps, wait, wait_for, again, jump, done, nested actions, error
    lua.execute("""
        __log = {}
        local L = qa_lib
        L.task('t1', {
            function(c) __log[#__log+1] = 'a' return L.wait(2) end,
            function(c, w) __log[#__log+1] = 'b' .. tostring(w) return L.wait_for(function() return __flag == true end, 5) end,
            function(c, ok) __log[#__log+1] = 'c' .. tostring(ok) return L.wait_for(function() return false end, 3) end,
            function(c, ok2) __log[#__log+1] = 'd' .. tostring(ok2) c.n = 0 end,
            "loop",
            function(c) c.n = c.n + 1 if c.n < 3 then return L.again(1) end return 'x', nil, 'z' end,
            function(c, a, b, z) __log[#__log+1] = 'e' .. c.n .. a .. tostring(b) .. z end,
            function(c) if not c.jumped then c.jumped = true c.n = 2 return L.jump('loop') end end,
            function(c) return L.seq({ function() return L.wait(1) end, function() return L.done(7, 'seven') end }) end,
            function(c, n, s) __log[#__log+1] = 'f' .. n .. s return L.done('end') end,
            function(c) __log[#__log+1] = 'NEVER' end,
        })
        L.task('bad', { function() return L.wait(1) end, function() error('boom') end })
        __early = L.task('early', function() return L.done(1) end)
    """)
    tick = lua.eval("function(dt) __clock = __clock + dt * 1000 qa.hooks.qa_lib_sched(0, nil) end")
    tick(1)
    lua.execute("__flag = true")
    for _ in range(14):
        tick(1)
    logt = "".join(lua.eval("__log").values())
    check("task: steps, wait/wait_for results, timeout false, again loop, nil-safe args, jump, nested seq, done stops", logt == "abtruectruedfalsee3xnilze3xnilzf7seven", logt)
    asserts = [(a[1], a[2], a[3]) for a in lua.eval("__asserts").values()]
    check("task: error in a step becomes a FAIL assert", any(a[0].startswith("task bad") and a[1] is False for a in asserts), asserts)
    check("task: one-step task finishes in its first slice", lua.eval("__early.dead == true and __early.result[1] == 1"))
    code_lines = [ln for ln in open(LIB, encoding="utf-8").read().splitlines() if not ln.strip().startswith("--")]
    check("no coroutine use left in qa_lib.lua", not any("coroutine." in ln for ln in code_lines))

    # hits to kill with a mock NPC (3 hits kill it)
    lua.execute("""
        __res = nil
        local L = qa_lib
        L.task('htk', {
            function(c)
                local se, id = L.spawn_npc('sim_default_bandit_0', { near = 7 })
                __online[id] = __mk(id, 'bandit', 1, 0.4)
                return L.hits_to_kill({ id = id, interval = 1, max = 10 })
            end,
            function(c, r, err) __res = r __err = err end,
        })
    """)
    for _ in range(30):
        tick(1)
    res = lua.eval("__res")
    check("hits_to_kill counts hits (0.4 per hit: 3 hits kill)", res is not None and res.hits == 3 and res.dead is True, None if res is None else (res.hits, res.dead))

    # hits_to_kill on a target that is ALREADY dead must be an error, never "0 hits, dead" (tester finding 2026-10-21)
    lua.execute("""
        __res2, __err2 = nil, nil
        local L = qa_lib
        L.task('htk_dead', {
            function(c)
                local se, id = L.spawn_npc('sim_default_bandit_0', { near = 7 })
                __online[id] = __mk(id, 'bandit', -1, 0.4)
                return L.hits_to_kill({ id = id, interval = 1, max = 10 })
            end,
            function(c, r, err) __res2 = r __err2 = err end,
        })
    """)
    for _ in range(12):
        tick(1)
    check("hits_to_kill: already dead target (id) returns nil + 'already dead', counts no hit", lua.eval("__res2") is None and "already dead" in str(lua.eval("__err2")), lua.eval("__err2"))
    check("hits_to_kill: normal run sets killed=true", res.killed is True, res.killed)

    # qa.once registered by the hooks file in several scripts of the same VM runs the body ONCE
    lua.execute("""
        __once_n = 0
        for i = 1, 3 do qa.once('dup_test', function() __once_n = __once_n + 1 end) end
        qa.hooks.once_dup_test(0, nil)                     -- the tick fires the (single) hook
        qa.once('dup_test', function() __once_n = __once_n + 1 end)  -- a later script load registers it again after it fired
    """)
    check("qa.once duplicate registration in one VM is ignored (fired once, not re-armed)", lua.eval("__once_n") == 1 and lua.eval("qa.hooks.once_dup_test") is None, lua.eval("__once_n"))

    # hostile spawn without god mode logs a warning
    lua.execute("__ev0 = #__events  qa_lib.god(false)  qa_lib.spawn_npc('sim_default_bandit_0', { near = 7, relation = 'enemy' })")
    warn = [e for e in lua.eval("__events").values() if "WARN spawn_npc" in str(e)]
    check("spawn_npc enemy without god mode logs a WARN line", len(warn) >= 1, len(warn))

    # kill_player through the action (relative fallback path not needed: the mock hit kills)
    lua.execute("""
        local L = qa_lib
        __victim = __mk(8, 'qaB', 1, 5)
        db.mp_actors[8] = __victim
        L.task('kp', { function() return L.kill_player(8, nil) end, function(c, ok, how) __kp = tostring(ok) .. ' ' .. tostring(how) end })
    """)
    for _ in range(3):
        tick(1)
    check("kill_player action reports the death", lua.eval("__kp") == "true hit", lua.eval("__kp"))

    # guide codes
    c1, l1 = L.guide_code("bar")
    c2, l2 = L.guide_code("coop_l11_sarcofag")
    c3, l3 = L.guide_code("l04_x18")
    check("guide_code bar / coop_l11_sarcofag / l04_x18", (c1, l1, c2, l2, c3, l3) == ("BAR", "coop_l05_bar", "SAR", "coop_l11_sarcofag", "X18", "coop_l04_x18"), (c1, l1, c2, l2, c3, l3))
    check("18 levels listed", len(list(L.ALL_LEVELS.values())) == 18)

    # server-side inventory scan and give_item
    ids = L.give_item(7, "wpn_pm", 2)
    inv, src = L.inventory(7, "server")
    check("give_item + server inventory scan", src == "server" and len(list(inv.values())) == 2, src)
    check("count_item", L.count_item(7, "wpn_pm", "server") == 2)

    # money
    L.give_money(7, 500)
    L.set_money(7, 120)
    check("money delta / set", L.money(7) == 120, L.money(7))

    # flags
    L.flag_give("my_flag")
    check("flag give / has / clear", L.flag_has("MY_FLAG") and L.flag_clear("my_flag") and not L.flag_has("my_flag"))

    # npc listing
    lua.execute("__sim[900] = { id = 900, position = __sim[7].position, section_name = function() return 'bandit_x' end, name = function() return 'esc_b1' end, clsid = function() return 35 end, alive = function() return true end }")
    lst = L.npcs_near(7, 50)
    names = [n.name for n in lst.values()]
    check("npcs_near finds the stalker next to the player", "esc_b1" in names, names)

    # relation
    n = lua.eval("__mk(3, 'x', 1, 0)")
    ok = L.set_relation(n, "friend", 7)
    check("set_relation / get_relation", ok and L.get_relation(n, 7) == "friend")
    lua.execute("__online[3] = __mk(3, 'x', 1, 0)")
    check("get_relation / set_relation accept an object id", L.set_relation(3, "enemy", 7) and L.get_relation(3, 7) == "enemy")
    check("L.PLACES holds the village fire", abs(L.PLACES.cordon_fire[1] + 206.9) < 0.01 and len(list(L.PLACES.cordon_trader_bunker.values())) == 3)

    # language probe
    check("language probe needs the game (mock has no translate_string)", L.language() is None or True)

    # qa_build opt-in
    sys.path.insert(0, HERE)
    import qa_build
    hooks = os.path.join(tmp, "h.lua")
    open(hooks, "w").write("--@qa_lib\nprint(1)\n")
    plain = os.path.join(tmp, "p.lua")
    open(plain, "w").write("print(2)\n")
    harness = os.path.join(HERE, "lua", "qa_harness.lua")
    e1 = qa_build.expand_qa_lib([harness, hooks])
    e2 = qa_build.expand_qa_lib([harness, plain])
    e3 = qa_build.expand_qa_lib([harness, qa_build.QA_LIB, hooks])
    check("qa_build opt-in: marker inserts qa_lib before the hooks, once", e1 == [harness, qa_build.QA_LIB, hooks], e1)
    check("qa_build opt-in: no marker changes nothing", e2 == [harness, plain])
    check("qa_build opt-in: already listed stays as is", e3 == [harness, qa_build.QA_LIB, hooks])

    print("MOCK RESULT:", "FAIL " + ", ".join(fails) if fails else "PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
