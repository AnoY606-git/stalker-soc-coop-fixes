"""Offline scenario test of coop_scn_inventory_carry.script with a mocked engine (lupa, Lua 5.1).
usage: python mock_test.py [script]  (needs the lupa package)  -> prints PASS/FAIL per scenario.  Mocks only what the script touches."""
import sys, os
import lupa.lua51 as lupa51

SCRIPT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gamedata", "scripts", "coop_scn_inventory_carry.script")

PRELUDE = r'''
T = 0
function time_global() return T end
function printf(...) end
function OnServer() return true end
function getFS() return { update_path = function(_, a, b) return b end } end
io = { open = function() return nil end }
local calls = {}
level = { add_call = function(f, g) calls[#calls + 1] = f end,
          object_by_id = function(id) return ITEMS[id] or BODIES[id] end }
function run_calls() for _, f in ipairs(calls) do f() end end
function clear_calls() calls = {} end
db = { mp_actors = {} }
ITEMS = {}
BODIES = {}      -- id -> body table
SEFLAGS = {}
story_flags = { story_flags = {}, set_flag = function(n, v) story_flags.story_flags[n] = v end }
game_sv = {}
game_cl = { executeFunctionOnServer = function(n) end }
LOCAL = 0
function LocalActor() return LOCAL end
RELEASED = {}
function alife() return { object = function(_, id) if BODIES[id] and not RELEASED[id] then return { id = id } end end,
                           release = function(_, se, f) RELEASED[se.id] = true; db.mp_actors[se.id] = nil; BODIES[se.id] = nil end } end
bind_stalker = nil

local nextid = 1000
function new_item(sect, owner)
  nextid = nextid + 1
  local it = { _id = nextid, _sect = sect, _parent = owner }
  function it:id() return self._id end
  function it:section() return self._sect end
  function it:parent() return self._parent end
  ITEMS[it._id] = it
  return it
end
function new_body(id, name, slots)
  local b = { _id = id, _name = name, _items = {}, _money = 0, _slots = {}, _alive = true }
  function b:id() return self._id end
  function b:name() return self._name end
  function b:alive() return self._alive end
  function b:section() return "actor" end
  function b:money() return self._money end
  function b:give_money(m) self._money = self._money + m end
  function b:iterate_inventory(f, o) local c = {} for _, it in ipairs(self._items) do c[#c+1] = it end for _, it in ipairs(c) do f(o, it) end end
  function b:item_in_slot(s) return self._slots[s] end
  function b:transfer_item(it, to)
    local keep = {}
    for _, x in ipairs(self._items) do if x ~= it then keep[#keep+1] = x end end
    self._items = keep
    for s, x in pairs(self._slots) do if x == it then self._slots[s] = nil end end
    to._items[#to._items + 1] = it
    it._parent = to
    -- the engine auto-slots into an empty slot when it arrives
    local want = AUTOSLOT[it._sect]
    if want and to._slots[want] == nil then to._slots[want] = it end
  end
  BODIES[id] = b
  db.mp_actors[id] = b
  return b
end
AUTOSLOT = { wpn_ak74 = 3, wpn_pm = 2, specops_outfit = 7, merc_outfit = 7 }
function give(b, sect)
  local it = new_item(sect, b)
  b._items[#b._items + 1] = it
  local want = AUTOSLOT[sect]
  if want and b._slots[want] == nil then b._slots[want] = it end
  return it
end
function kit(b) for _, s in ipairs({ "wpn_knife", "device_torch", "wpn_binoc", "device_pda", "bolt" }) do give(b, s) end end
function slotsig(b) local o = {} for _, s in ipairs({2,3,7}) do local it = b._slots[s] o[#o+1] = s .. "=" .. (it and (it._sect .. "#" .. it._id) or "none") end return table.concat(o, ",") end
function count_bodies() local n = 0 for _ in pairs(db.mp_actors) do n = n + 1 end return n end
function advance(sec) for i = 1, sec * 2 do T = T + 500; run_calls() end end
'''

def run(name, body_lua, check_lua):
    rt = lupa51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(PRELUDE)
    src = open(SCRIPT, encoding='utf-8').read()
    rt.globals().SRC = src
    rt.execute("assert(loadstring(SRC))()")
    rt.execute(body_lua)
    res = rt.eval(check_lua)
    print(("PASS " if res is True else "FAIL ") + name, "" if res is True else res)
    return res is True

ok = True

# 1) dedicated, 1 client: engine spawns a new body (named after the player); the client first still points at the old body, then at the new one
ok &= run("one client, new body, transient ping on old body", r'''
  old = new_body(100, "qaa"); kit(old); give(old, "wpn_ak74"); give(old, "wpn_pm"); give(old, "specops_outfit"); give(old, "merc_outfit"); old._money = 5000
  OLDSIG = slotsig(old)
  game_cl.executeFunctionOnServer = function(n) end
  -- client pings
  function ping(id) game_sv.coop_inv_ping_QAA(id) end
  advance(1)
  ping(100); advance(2); ping(100); advance(2); ping(100); advance(2)       -- normal play, flagged
  -- LOAD: server VM restarts (flags survive in story_flags); simulate by renaming the saved body and spawning a new one
  old._name = "actor_the_main_character"
  new = new_body(200, "qaa"); kit(new)
  for i = 1, 10 do ping(100); advance(2) end       -- client still points at the old body for 20 s
  for i = 1, 30 do ping(200); advance(2) end       -- then at the new one
''', r'''
  (function()
    if count_bodies() ~= 1 then return "bodies=" .. count_bodies() end
    local b = BODIES[200]
    if not b then return "new body gone" end
    if slotsig(b) ~= OLDSIG then return "slots " .. slotsig(b) .. " vs " .. OLDSIG end
    if b._money ~= 5000 then return "money " .. b._money end
    return true
  end)()
''')

# 2) dedicated, 1 client, second load: engine binds the client to the SAVED body and also spawns a fresh spare body (generic name)
ok &= run("one client, client keeps the saved body, spare start-kit body", r'''
  old = new_body(100, "actor_the_main_character"); kit(old); give(old, "wpn_ak74"); give(old, "specops_outfit"); old._money = 7000
  story_flags.set_flag("PBODY_QAA_100", true)
  OLDSIG = slotsig(old)
  spare = new_body(200, "actor_the_main_character"); kit(spare)
  function ping(id) game_sv.coop_inv_ping_QAA(id) end
  advance(1)
  for i = 1, 40 do ping(100); advance(2) end
''', r'''
  (function()
    if count_bodies() ~= 1 then return "bodies=" .. count_bodies() end
    if not BODIES[100] then return "saved body gone" end
    if slotsig(BODIES[100]) ~= OLDSIG or BODIES[100]._money ~= 7000 then return "content changed" end
    return true
  end)()
''')

# 3) two clients, the engine initially points client A at B's saved body (transient), new bodies carry wrong names (same address)
ok &= run("two clients, cross pings and equal names", r'''
  bA = new_body(300, "actor_partner_regular"); kit(bA); give(bA, "wpn_pm"); give(bA, "merc_outfit"); bA._money = 111
  bB = new_body(100, "actor_the_main_character"); kit(bB); give(bB, "wpn_ak74"); give(bB, "specops_outfit"); bB._money = 222
  story_flags.set_flag("PBODY_QAA_300", true); story_flags.set_flag("PBODY_QAB_100", true)
  SIGA, SIGB = slotsig(bA), slotsig(bB)
  nA = new_body(400, "qab"); kit(nA)
  nB = new_body(410, "qab"); kit(nB)
  function pingA(id) game_sv.coop_inv_ping_QAA(id) end
  function pingB(id) game_sv.coop_inv_ping_QAB(id) end
  advance(1)
  for i = 1, 8 do pingA(100); pingB(100); advance(2) end        -- A wrongly points at B's old body
  for i = 1, 30 do pingA(400); pingB(410); advance(2) end
''', r'''
  (function()
    if count_bodies() ~= 2 then return "bodies=" .. count_bodies() end
    if not BODIES[400] or not BODIES[410] then return "new bodies missing" end
    if slotsig(BODIES[400]) ~= SIGA or BODIES[400]._money ~= 111 then return "A: " .. slotsig(BODIES[400]) .. " m=" .. BODIES[400]._money end
    if slotsig(BODIES[410]) ~= SIGB or BODIES[410]._money ~= 222 then return "B: " .. slotsig(BODIES[410]) .. " m=" .. BODIES[410]._money end
    return true
  end)()
''')

# 4) a fresh player joining a running game must never lose his start-kit body
ok &= run("new player is not released", r'''
  a = new_body(100, "qaa"); kit(a)
  b = new_body(200, "qab"); kit(b)
  function pingA(id) game_sv.coop_inv_ping_QAA(id) end
  advance(1)
  for i = 1, 40 do pingA(100); advance(2) end       -- B never pings (client not ready), 80 s
''', r'''
  (function() if count_bodies() ~= 2 then return "bodies=" .. count_bodies() end return true end)()
''')

# 5) listen game: both bodies carry the player's name, host points at the new one
ok &= run("listen: both bodies named alike", r'''
  old = new_body(100, "host"); kit(old); give(old, "wpn_ak74"); give(old, "specops_outfit"); old._money = 900
  story_flags.set_flag("PBODY_HOST_100", true)
  OLDSIG = slotsig(old)
  new = new_body(200, "host"); kit(new)
  LOCAL = 200
  function ping(id) game_sv.coop_inv_ping_HOST(id) end
  game_sv.coop_inv_ping_HOST = game_sv.coop_inv_ping_HOST or function() end
  for i = 1, 40 do advance(2) end
''', r'''
  (function()
    if count_bodies() ~= 1 then return "bodies=" .. count_bodies() end
    local b = BODIES[200]
    if not b or slotsig(b) ~= OLDSIG or b._money ~= 900 then return "not restored" end
    return true
  end)()
''')
sys.exit(0 if ok else 1)
