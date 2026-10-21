"""Offline check of patches/corpse_artifacts (no game, a few seconds):
    python corpse_roll_test.py <mod gamedata.db0\\configs\\misc folder> [<SoC reference folder with config\\misc + scripts\\death_manager.script>]
Runs the REAL death_manager.script of this patch (and, optionally, the original Shadow of Chernobyl one) in a Lua 5.1 VM (lupa) with a small engine mock
(ini_file with #include and section inheritance, a fake NPC, alife():create that records what is created). Proves:
  * the original SoC script + SoC configs never drop an artifact of the 0.5% tier, however many corpses (the bug);
  * the stock mod (xrMPE death_manager + the mod's tables) never drops any artifact;
  * the patched script drops each of the 12 last-tier artifacts at 0.5% per corpse on the late levels, on no other level,
    never from army / zombied / monolith, only once per corpse (a second call changes nothing);
  * the host settings (chance_mult, all_levels) and the test override work, and a missing coop_host_cfg module is harmless.
Needs `pip install lupa` (same package as qa_lib_mock_test.py)."""
import math
import os
import random
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
MOD_MISC = sys.argv[1] if len(sys.argv) > 1 else None
SOC_REF = sys.argv[2] if len(sys.argv) > 2 else None
if not MOD_MISC or not os.path.isdir(MOD_MISC):
    sys.exit("usage: corpse_roll_test.py <mod gamedata.db0\\configs\\misc folder> [<SoC reference folder>]")

LAST_TIER = ["af_night_star", "af_gold_fish", "af_soul", "af_electra_moonlight", "af_rusty_sea-urchin", "af_ameba_mica",
             "af_cristall", "af_dummy_glassbeads", "af_dummy_pellicle", "af_dummy_battery", "af_dummy_spring", "af_fuzz_kolobok"]
IDS = [a + "_soc" for a in LAST_TIER]

PRELUDE = r'''
local read_file, script_src, soc_style = ...
local G = {}
for _, k in ipairs({ "string", "table", "math", "pairs", "ipairs", "pcall", "tonumber", "tostring", "type", "setmetatable", "getmetatable",
	"error", "select", "unpack", "next", "assert", "loadstring", "setfenv", "getfenv", "rawget", "rawset", "print" }) do G[k] = _G[k] end
G._G = G
G.t_log = {}
function G.printf(fmt, ...) G.t_log[#G.t_log + 1] = string.format(fmt, ...) end
function G.abort(fmt, ...) error(string.format(fmt, ...)) end
G.t_created = {}
G.t_ammo = 0
G.t_level = "coop_l09_radar"
G.t_diff = 0

-- ini with #include and inheritance (inherited lines first, a child line replaces the parent's)
local cache = {}
local function parse(name)
	if cache[name] then return cache[name] end
	local text = read_file(name)
	local secs, cur = {}, nil
	local lines = {}
	for line in (text .. "\n"):gmatch("([^\n]*)\n") do lines[#lines + 1] = (line:gsub("\r", "")) end
	local function add(line)
		local inc = line:match('^#include%s+"(.-)"')
		if inc then
			for k, v in pairs(parse(inc)) do secs[k] = v end
			return
		end
		local sc = line:find(";", 1, true)
		if sc then line = line:sub(1, sc - 1) end
		line = line:match("^%s*(.-)%s*$")
		if line == "" then return end
		local nm, parent = line:match("^%[(.-)%]%s*:?%s*(%S*)")
		if nm then
			cur = { lines = {}, map = {} }
			if parent ~= "" and secs[parent:lower()] then
				for _, l in ipairs(secs[parent:lower()].lines) do cur.lines[#cur.lines + 1] = { l[1], l[2] }; cur.map[l[1]] = #cur.lines end
			end
			secs[nm:lower()] = cur
			return
		end
		if not cur then return end
		local k, v = line:match("^([^=]-)%s*=%s*(.*)$")
		if not k then k, v = line, "" end
		if cur.map[k] then cur.lines[cur.map[k]][2] = v
		else cur.lines[#cur.lines + 1] = { k, v }; cur.map[k] = #cur.lines end
	end
	for _, l in ipairs(lines) do add(l) end
	cache[name] = secs
	return secs
end
local ini = {}
ini.__index = ini
function ini:section_exist(s) return self.secs[s:lower()] ~= nil end
function ini:line_count(s) return #self.secs[s:lower()].lines end
function ini:r_line(s, i) local l = self.secs[s:lower()].lines[i + 1]; return true, l[1], l[2] end
function G.ini_file(name) return setmetatable({ secs = parse(name) }, ini) end

function G.parse_names(s) local t = {} for w in tostring(s):gmatch("[^,%s]+") do t[#t + 1] = w end return t end
function G.parse_nums(s) local t = {} for w in tostring(s):gmatch("[^,%s]+") do t[#t + 1] = tonumber(w) end return t end
G.level = { name = function() return G.t_level end, get_game_difficulty = function() return G.t_diff end }
G.alife_obj = {}
G.alife = function()
	return {
		object = function(self, id) return G.alife_obj[id] end,
		create = function(self, section, pos, lv, gv, parent) G.t_created[#G.t_created + 1] = { section = section, parent = parent } end,
		release = function() end,
	}
end
G.create_ammo = function() G.t_ammo = G.t_ammo + 1 end
G.se_respawn = { create_ammo = function() G.t_ammo = G.t_ammo + 1 end }
G.db = { storage = {} }
G.isArtefact = function() return false end
G.isWeapon = function() return false end
G.xr_corpse_detection = { lootable_table = {} }
G.character_community = function(npc) return npc:character_community() end
G.clsid = {}
G.get_clsid = function() return 0 end

function G.class(name)
	local c = {}
	c.__index = c
	setmetatable(c, { __call = function(cls, ...) local o = setmetatable({}, cls) if cls.__init then cls.__init(o, ...) end return o end })
	G[name] = c
end
local chunk = assert(loadstring(script_src, "death_manager"))
setfenv(chunk, G)
chunk()
if soc_style then G.t_soc = true end

local npc_id = 0
function G.new_npc(community)
	npc_id = npc_id + 1
	local id = npc_id
	G.alife_obj[id] = { death_droped = false }
	local npc = {}
	function npc:id() return id end
	function npc:name() return "npc_" .. id end
	function npc:position() return {} end
	function npc:level_vertex_id() return 1 end
	function npc:game_vertex_id() return 1 end
	function npc:character_community() return community end
	function npc:spawn_ini() return nil end
	function npc:iterate_inventory() end
	function npc:object() return {} end
	function npc:marked_dropped() return false end
	return npc
end
function G.kill(community)
	local npc = G.new_npc(community)
	local dm = G.drop_manager(npc)
	dm:create_release_item()
	return npc, dm
end
return G
'''


def make_vm(root_misc, script_path, soc_style=False, extra_globals=None):
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)

    def read_file(name):
        for base in root_misc:
            p = os.path.join(base, name.replace("misc\\", "").replace("\\", os.sep))
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    return f.read().decode("cp1251", errors="replace")
        raise FileNotFoundError(name)

    with open(script_path, "rb") as f:
        src = f.read().decode("cp1251", errors="replace")
    runner = lua.execute("return function(...) " + PRELUDE + " end")
    G = runner(read_file, src, soc_style)
    return lua, G


def run_deaths(lua, G, community, n, level=None, init=True):
    """kill n NPCs of `community` and count what the roll created; returns Counter-like dict"""
    if level:
        G.t_level = level
    if init:
        G.init_drop_settings()
    counts = {}
    corpses_with = 0
    for _ in range(n):
        before = len(G.t_created)
        G.kill(community)
        made = [G.t_created[i + 1].section for i in range(before, len(G.t_created))]
        arts = [m for m in made if m.startswith("af_")]
        if arts:
            corpses_with += 1
        for m in made:
            counts[m] = counts.get(m, 0) + 1
    return counts, corpses_with


def wilson(p, n, z=4.0):
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + info if info else ""))
    if not ok:
        fails += 1


random.seed(7)
N = 40000
PATCH_MISC = os.path.join(PATCH, "gamedata", "configs", "misc")

# ---- 1. original SoC script + SoC configs: the bug (optional)
if SOC_REF:
    soc_misc = os.path.join(SOC_REF, "config", "misc")
    lua, G = make_vm([soc_misc], os.path.join(SOC_REF, "scripts", "death_manager.script"), True)
    G.t_level = "l10_radar"
    G.init_drop_settings()
    lua.execute("math.randomseed(11)")
    counts, with_art = run_deaths(lua, G, "stalker", N, "l10_radar", init=False)
    tier = [a[:-4] for a in IDS]
    drops05 = {a: counts.get(a, 0) for a in tier}
    print("SoC original, l10_radar, stalker, %d corpses: 0.5%% tier drops = %s" % (N, drops05))
    check("SoC original: the 0.5% artifacts never drop (the bug)", sum(drops05.values()) == 0)
    n_med = counts.get("af_medusa", 0)
    check("SoC original: af_medusa (ltx 0.015) drops at 1%, not 1.5%", 0.008 < n_med / N < 0.0125, "rate %.4f" % (n_med / N))
    G.t_level = "l01_escape"
    G.init_drop_settings()
    counts, _ = run_deaths(lua, G, "stalker", 5000, "l01_escape", init=False)
    print("SoC original on Escape: af_medusa %.4f per corpse (the 1%% tier drops, level multiplier 1), 0.5%% tier %d" % (
        counts.get("af_medusa", 0) / 5000, sum(counts.get(a, 0) for a in tier)))

# ---- 2. stock mod: xrMPE script + the mod's tables
# the stock xrMPE script is not stored in the repo: give its path in XRMPE_DEATH_MANAGER to run this part
base_script = os.environ.get("XRMPE_DEATH_MANAGER")
if base_script and os.path.isfile(base_script):
    lua, G = make_vm([MOD_MISC], base_script)
    lua.execute("math.randomseed(21)")
    counts, with_art = run_deaths(lua, G, "stalker", 5000, "coop_l09_radar")
    check("stock mod: no artifact on Radar", with_art == 0)
    print("stock mod, Radar, 5000 stalker corpses: bread %.3f medkit %.3f bandage %.3f" % (counts.get("bread", 0) / 5000, counts.get("medkit", 0) / 5000, counts.get("bandage", 0) / 5000))

# ---- 3. patched script, patched tables over the mod's death_generic.ltx
lua, G = make_vm([PATCH_MISC, MOD_MISC], os.path.join(PATCH, "gamedata", "scripts", "death_manager.script"))
lua.execute("math.randomseed(33)")
LATE = ["coop_l09_radar", "coop_l10_pripyat", "coop_l11_stancia_1", "coop_l11_stancia_2", "coop_l11_control_monolith", "coop_l11_sarcofag"]
EARLY = ["coop_l01_escape", "coop_l02_garbage", "coop_l03_agroprom", "coop_l03_agroprom_underground", "coop_l04_darkvalley", "coop_l04_x18",
         "coop_l05_bar", "coop_l06_rostok", "coop_l07_military", "coop_l08_x16", "coop_l08_yantar", "coop_l09_x10"]

counts, with_art = run_deaths(lua, G, "stalker", N, "coop_l09_radar")
p_corpse = with_art / N
exp = 1 - (1 - 0.005) ** 12
lo, hi = wilson(exp, N)
print("patched, Radar, stalker, %d corpses: corpses with an artifact %d (%.4f, expected %.4f), per artifact %s" % (
    N, with_art, p_corpse, exp, {k[3:-4]: v for k, v in sorted(counts.items()) if k.startswith("af_")}))
check("patched: corpses with an artifact match 12 x 0.5%", lo <= p_corpse <= hi, "%.4f in [%.4f, %.4f]" % (p_corpse, lo, hi))
for a in IDS:
    r = counts.get(a, 0) / N
    l2, h2 = wilson(0.005, N)
    check("patched: %s about 0.5%% per corpse" % a, l2 <= r <= h2, "%.4f" % r)
other = [k for k in counts if k.startswith("af_") and k not in IDS]
check("patched: no other artifact id is ever created", not other, str(other))
check("patched: battery id is among them", "af_dummy_battery_soc" in IDS and counts.get("af_dummy_battery_soc", 0) > 0)
st = G.corpse_art_stats
check("stats: deaths counted once per corpse, rolls = 12 per corpse", st.deaths == N and st.rolls == 12 * N, "deaths %d rolls %d drops %d" % (st.deaths, st.rolls, st.drops))

for comm in ("bandit", "killer", "ecolog", "dolg", "freedom"):
    c, w = run_deaths(lua, G, comm, 20000, "coop_l10_pripyat")
    r = w / 20000
    l2, h2 = wilson(exp, 20000)
    check("patched: %s on Pripyat drops like stalker" % comm, l2 <= r <= h2, "%.4f" % r)
for comm in ("army", "zombied", "monolith"):
    c, w = run_deaths(lua, G, comm, 20000, "coop_l11_stancia_1")
    check("patched: %s never carries an artifact (SoC)" % comm, w == 0)
for lv in LATE:
    c, w = run_deaths(lua, G, "stalker", 8000, lv)
    l2, h2 = wilson(exp, 8000)
    check("patched: late level %s drops" % lv, l2 <= w / 8000 <= h2, "%.4f" % (w / 8000))
for lv in EARLY:
    c, w = run_deaths(lua, G, "stalker", 8000, lv)
    check("patched: early level %s never drops (SoC)" % lv, w == 0)

# once per corpse: a second create_release_item on the same corpse (save load, first update) creates nothing more
lua.execute("math.randomseed(5)")
before = len(G.t_created)
dm_total = 0
for _ in range(2000):
    npc, dm = G.kill("stalker")
    n1 = len(G.t_created)
    dm.create_release_item(dm)
    G.drop_manager(npc).create_release_item(G.drop_manager(npc))
    if len(G.t_created) != n1:
        dm_total += 1
check("not re-rolled: a second call on the same corpse creates nothing", dm_total == 0)

# ---- 4. host settings and the test override
G.t_level = "coop_l09_radar"
G.corpse_art_test = lua.table(chance_mult=200)  # 0.5% x 200 = 100%
c, w = run_deaths(lua, G, "stalker", 500, "coop_l09_radar")
check("chance_mult 200: every corpse carries all 12 artifacts", w == 500 and all(c.get(a, 0) == 500 for a in IDS), "corpses with %d of 500" % w)
G.corpse_art_test = lua.table(chance_mult=0)
c, w = run_deaths(lua, G, "stalker", 3000, "coop_l09_radar")
check("chance_mult 0: nothing drops", w == 0)
G.corpse_art_test = lua.table(chance_mult=200, all_levels=True)
c, w = run_deaths(lua, G, "stalker", 300, "coop_l01_escape")
check("all_levels override: Escape corpses carry them too", w == 300)
c, w = run_deaths(lua, G, "army", 300, "coop_l01_escape")
check("all_levels override: army still none", w == 0)
G.corpse_art_test = None
c, w = run_deaths(lua, G, "stalker", 3000, "coop_l01_escape")
check("override removed: Escape back to none", w == 0)

# coop_host_cfg module present (host file values), throwing, absent
G.coop_host_cfg = lua.eval('{ num = function(sec, key, d) if sec == "corpse_artifacts" and key == "chance_mult" then return 10 end return d end, '
                           'bool = function(sec, key, d) if sec == "corpse_artifacts" and key == "all_levels" then return true end return d end }')
c, w = run_deaths(lua, G, "stalker", 20000, "coop_l01_escape")
e10 = 1 - (1 - 0.05) ** 12
l2, h2 = wilson(e10, 20000)
check("host file chance_mult 10 + all_levels true: Escape corpses 12 x 5%", l2 <= w / 20000 <= h2, "%.4f expected %.4f" % (w / 20000, e10))
G.coop_host_cfg = lua.eval('{ num = function() error("boom") end, bool = function() error("boom") end }')
c, w = run_deaths(lua, G, "stalker", 20000, "coop_l09_radar")
l2, h2 = wilson(exp, 20000)
check("coop_host_cfg that throws: defaults (1x, late levels only)", l2 <= w / 20000 <= h2, "%.4f" % (w / 20000))
G.coop_host_cfg = None
c, w = run_deaths(lua, G, "stalker", 20000, "coop_l09_radar")
check("no coop_host_cfg module: defaults", l2 <= w / 20000 <= h2, "%.4f" % (w / 20000))

# other loot is untouched: ammo/food/medicine counts per corpse stay in the stock range
c, w = run_deaths(lua, G, "stalker", 3000, "coop_l01_escape")
check("ordinary loot unchanged (bread 1 x 10%, medkit 2 x 15%, bandage 2 x 25%)", 0.07 < c.get("bread", 0) / 3000 < 0.13 and 0.26 < c.get("medkit", 0) / 3000 < 0.33
      and 0.45 < c.get("bandage", 0) / 3000 < 0.53, "bread %.3f medkit %.3f bandage %.3f" % (c.get("bread", 0) / 3000, c.get("medkit", 0) / 3000, c.get("bandage", 0) / 3000))

print("RESULT:", "PASS" if fails == 0 else "FAIL (%d)" % fails)
sys.exit(1 if fails else 0)
