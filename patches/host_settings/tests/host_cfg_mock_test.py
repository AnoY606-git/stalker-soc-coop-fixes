"""Offline check of patches/host_settings against a mock engine (no game, a few seconds):  python host_cfg_mock_test.py
Runs the REAL scripts (coop_host_cfg, coop_balance, player_scaling, stash_loot, mutant_loot, coop_repeat_quests, alife_roaming and, from optional/,
sar_fps_cfg) in a Lua 5.1 VM (lupa) with a tiny engine mock: ini_file reads the real ltx files of the patches, getFS():update_path maps to a temp folder,
OnServer() is switchable. Proves: the file is created with every setting on the first server start, the overrides reach every consumer, bad values and
missing keys fall back to the defaults without an error, a client (OnServer false) never reads or writes the file.
Needs `pip install lupa` (the same package qa_lib_mock_test.py uses)."""
import glob
import os
import shutil
import sys
import tempfile

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

PRELUDE = r'''
local find_file, tmp = ...
local G = {}
for _, k in ipairs({ "string", "table", "math", "io", "os", "pairs", "ipairs", "pcall", "tonumber", "tostring", "type", "setmetatable", "getmetatable",
	"error", "select", "unpack", "next", "assert", "loadfile", "setfenv", "getfenv", "rawget", "rawset", "print", "xpcall" }) do G[k] = _G[k] end
G.__log = {}
G.__server = true
function G.printf_msg(fmt, ...) G.__log[#G.__log + 1] = string.format(fmt, ...) end
G.printf = G.printf_msg
G.__t = 0
function G.time_global() G.__t = G.__t + 3000 return G.__t end
function G.OnServer() return G.__server end
function G.IsDedicatedServer() return false end
function G.getFS() return { update_path = function(self, a, n) return tmp .. "/" .. a:gsub("%$", "") .. "_" .. n end } end

-- ltx reader over the real files
local function read_ltx(name)
	local path = find_file(name)
	if not path then return nil end
	local f = io.open(path, "r")
	local text = f:read("*a")
	f:close()
	local secs, order, cur = {}, {}, nil
	for line in (text .. "\n"):gmatch("([^\n]*)\n") do
		line = line:gsub("\r", "")
		local sc = line:find(";", 1, true)
		if sc then line = line:sub(1, sc - 1) end
		line = line:match("^%s*(.-)%s*$")
		if line ~= "" then
			local s = line:match("^%[(.-)%]")
			if s then
				cur = { name = s, lines = {}, map = {} }
				secs[s] = cur
				order[#order + 1] = s
			elseif cur then
				local k, v = line:match("^([^=]-)%s*=%s*(.*)$")
				if k then
					cur.lines[#cur.lines + 1] = { k, v }
					cur.map[k] = v
				else
					cur.lines[#cur.lines + 1] = { line, "" }
					cur.map[line] = ""
				end
			end
		end
	end
	return secs
end
local ini_class = {}
ini_class.__index = ini_class
function ini_class:section_exist(s) return self.secs[s] ~= nil end
function ini_class:line_exist(s, k) return self.secs[s] ~= nil and self.secs[s].map[k] ~= nil end
function ini_class:r_string(s, k) return self.secs[s].map[k] end
function ini_class:r_float(s, k) return tonumber(self.secs[s].map[k]) end
function ini_class:r_bool(s, k) local v = self.secs[s].map[k]; return v == "true" or v == "1" end
function ini_class:line_count(s) return #self.secs[s].lines end
function ini_class:r_line(s, i, a, b) local l = self.secs[s].lines[i + 1]; return true, l[1], l[2] end
function G.ini_file(name)
	local secs = read_ltx(name)
	if not secs then error("ini_file: no file " .. name) end
	return setmetatable({ secs = secs }, ini_class)
end
function G.system_ini() return { section_exist = function() return true end, line_exist = function() return false end } end
G.db = { mp_actors = {} }
G.level = { name = function() return "coop_l01_escape" end }
function G.get_players_count() return 1 end
function G.class(name) return function() getfenv(2)[name] = {} end end
G.object_binder = {}

-- script modules, loaded on first use like the engine does
local mods = {}
local load_module
local function new_env(name)
	local env
	env = setmetatable({}, { __index = function(t, k)
		local v = G[k]
		if v ~= nil then return v end
		return load_module(k)
	end })
	return env
end
function load_module(name)
	if mods[name] ~= nil then return mods[name] or nil end
	local path = find_file("scripts\\" .. name .. ".script")
	if not path then mods[name] = false return nil end
	local env = new_env(name)
	mods[name] = env
	local f, err = loadfile(path)
	if not f then error(err) end
	setfenv(f, env)
	f()
	return env
end
G.__load_module = load_module
function G.__set_actors() G.db.mp_actors = { [1] = true } end
G.__reset_modules = function() mods = {} end
return G
'''


HOOK_STUB = r'''
local G, hook_path = ...
G.__asserts = {}
G.qa = { cfg = {}, hooks = {} }
function G.qa.assert(n, ok, d) G.__asserts[#G.__asserts + 1] = { n, ok, d } end
function G.qa.event(m) end
function G.qa.once(name, fn) G.__once = fn end
local L = {}
function L.god(on) end
function L.wait(sec)
	local rq = G.__load_module("coop_repeat_quests")
	rq.update()
	return nil
end
-- hits to kill: a stand-in that follows the multiplier (3 hits at 1.0, 1 at 3.0), like the real probe does
function L.hits_to_kill(o)
	local m = G.__load_module("coop_balance").cfg().player_damage_mult
	local hits = math.max(1, math.ceil(3 / math.max(m, 1)))
	return { hits = hits, killed = true }
end
function L.task(name, steps)
	local args = {}
	for i, fn in ipairs(steps) do
		args = { fn({}, unpack(args)) }
	end
end
G.qa_lib = L
local env = setmetatable({}, { __index = function(t, k)
	local v = G[k]
	if v ~= nil then return v end
	return G.__load_module(k)
end })
local f = assert(loadfile(hook_path))
setfenv(f, env)
f()
G.__once(0, nil)
'''

OPTIONAL = False   # the optional/ packages are only mounted for the sarcophagus_fps check


def find_file(name):
    name = name.replace("\\", "/")
    pats = [os.path.join(REPO, "patches", "*", "gamedata", name if name.startswith("scripts/") else "configs/" + name)]
    if OPTIONAL:
        pats.append(os.path.join(REPO, "optional", "*", "gamedata", name if name.startswith("scripts/") else "configs/" + name))
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[0]
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="hostcfg_")
    fails = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + ((" : " + str(detail)) if detail != "" else ""))
        if not ok:
            fails.append(name)

    try:
        lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
        G = lua.execute(PRELUDE, find_file, tmp)
        # the app data folder is a flat temp folder: app_data_root_coop_settings.ltx
        cfg_path = os.path.join(tmp, "app_data_root_coop_settings.ltx")

        def mod(name):
            m = G["__load_module"](name)
            if m is None:
                raise RuntimeError("module not found: " + name)
            return m

        host = mod("coop_host_cfg")

        # ---- 1. first server start: the file is created with every setting
        check("no file before the first read", not os.path.exists(cfg_path))
        v = host.num("damage", "player_damage_mult", 1.5)
        check("first read returns the default", v == 1.5, v)
        check("file created on first server start", os.path.exists(cfg_path))
        text = open(cfg_path, "rb").read().decode("utf-8")
        for needle in ("[damage]", "player_damage_mult = 1.5", "[ammo]", "max_players = 4", "[enemy_scaling]", "human_extra_per_player = 0.5",
                       "skip_levels = coop_l11_sarcofag", "[box_loot]", "wood_chance = 30", "[box_loot_items]", "medkit = 8", "[repeat_quests]",
                       "cooldown_min = 1440", "timeout_mult = 1", "item_rewards = true", "[mutant_loot]", "mutant_dog_part = 0.2", "take_distance = 6",
                       "[roaming]", "stay_min = 240", "allow_online_move = true", "Урон игроков", "Множитель урона"):
            check("created file contains '%s'" % needle, needle in text)
        check("sarcophagus section only with the optional package", "[sarcophagus_fps]" not in text)
        check("summary line logged, nothing from the file", "0 value(s) from the file" in host.last_line and "damage.player_damage_mult=1.5" in host.last_line, host.last_line[:200])
        check("summary line is in host_cfg.log too", os.path.exists(os.path.join(tmp, "logs_host_cfg.log")))
        n_keys = len([l for l in text.splitlines() if l and not l.startswith(";") and " = " in l])
        print("   created file has %d settings, %d bytes" % (n_keys, len(text.encode("utf-8"))))
        # a freshly created file must read back as the defaults for every consumer
        bal = mod("coop_balance")
        c = bal.cfg()
        check("coop_balance defaults with the fresh file", c.player_damage_mult == 1.5 and c.max_players == 4 and c.ammo_per_extra_player == 1.0 and c.log is True)

        # ---- 2. overrides reach every consumer
        override = (
            "﻿; test file\r\n"
            "[damage]\r\n"
            "player_damage_mult = 2.0   ; trailing comment\r\n"
            "log = off\r\n"
            "[ammo]\r\n"
            "ammo_per_extra_player = 0,5\r\n"          # comma decimal
            "max_players = abc\r\n"                     # bad value -> default
            "[Enemy_Scaling]\r\n"                       # case-insensitive section
            "MAX_FACTOR = 1.75\r\n"
            "human_extra_per_player = 0.25\r\n"
            "skip_levels = coop_l11_sarcofag, coop_l01_escape\r\n"
            "slot_fraction = 99\r\n"                    # not host-editable: ignored
            "[box_loot]\r\n"
            "wood_chance = 100\r\n"
            "metal_chance = 0\r\n"
            "[box_loot_items]\r\n"
            "medkit = 0\r\n"
            "vodka = 77\r\n"
            "[repeat_quests]\r\n"
            "cooldown_min = 60\r\n"
            "timeout_mult = 2\r\n"
            "item_rewards = false\r\n"
            "[mutant_loot]\r\n"
            "mutant_dog_part = 1\r\n"
            "take_distance = 12\r\n"
            "[roaming]\r\n"
            "enabled = false\r\n"
            "stay_min = 10\r\n"
            "max_npc_per_smart = 99\r\n"               # not host-editable: ignored
            "garbage line without equals\r\n"
        )
        open(cfg_path, "wb").write(override.encode("utf-8"))
        line = host.reload()
        check("reload reports the file values", "damage.player_damage_mult=2(file)" in line, line[:120])
        check("summary counts bad values", "1 bad" in line, line[:200])
        check("bad value is named in the summary", "ammo.max_players=4(bad value 'abc', default used)" in line)
        check("host.num with comment and BOM", host.num("damage", "player_damage_mult", 9) == 2.0)
        check("host.bool accepts off", host.bool("damage", "log", True) is False)
        check("host.num accepts a decimal comma", abs(host.num("ammo", "ammo_per_extra_player", 9) - 0.5) < 1e-9)
        check("host.num bad value gives the default", host.num("ammo", "max_players", 7) == 7)
        check("host.num missing key gives the default", host.num("nope", "nothing", 5) == 5)
        check("host.str missing key gives the default", host.str("nope", "nothing", "d") == "d")
        check("host.bool bad value gives the default", host.bool("ammo", "max_players", True) is True)
        check("bad_count counts the bad value", host.bad_count() >= 1, host.bad_count())

        c = bal.cfg()
        check("coop_balance: player_damage_mult 2.0", c.player_damage_mult == 2.0, c.player_damage_mult)
        check("coop_balance: log false", c.log is False)
        check("coop_balance: ammo 0.5", abs(c.ammo_per_extra_player - 0.5) < 1e-9)
        check("coop_balance: bad max_players keeps 4", c.max_players == 4)

        ps = mod("player_scaling")
        p = ps.cfg()
        check("player_scaling: max_factor 1.75", p.max_factor == 1.75, p.max_factor)
        check("player_scaling: human_extra 0.25", p.human_extra_per_player == 0.25)
        check("player_scaling: skip_levels list", p.skip_level_set["coop_l01_escape"] and p.skip_level_set["coop_l11_sarcofag"])
        check("player_scaling: slot_fraction is NOT host-editable", p.slot_fraction == 0.6, p.slot_fraction)
        check("player_scaling: untouched keys keep the db value", p.mutant_extra_per_player == 0.5 and p.reinforce_cooldown_s == 300)

        sl = mod("stash_loot")
        s = sl.config()
        check("stash_loot: wood 100 / metal 0 / inventory 50", s.chance.w == 100 and s.chance.m == 0 and s.chance.i == 50, "%s %s %s" % (s.chance.w, s.chance.m, s.chance.i))
        items = {}
        for i in range(1, len(s["items"]) + 1):
            items[s["items"][i][1]] = s["items"][i][2]
        check("stash_loot: medkit weight 0 removes it", "medkit" not in items)
        check("stash_loot: vodka weight 77", items.get("vodka") == 77, items.get("vodka"))
        check("stash_loot: bread keeps the db weight", items.get("bread") == 20)

        ml = mod("mutant_loot")
        check("mutant_loot: dog part chance 1", ml.chance_for("mutant_dog_part") == 1)
        check("mutant_loot: flesh part keeps 0.2", abs(ml.chance_for("mutant_flesh_part") - 0.2) < 1e-6)

        rq = mod("coop_repeat_quests")
        G["__set_actors"]()
        rq.host_reload()
        # load_cfg is local: run it through update(); stub the per-tick work
        rq.update()   # the per-quest ticks fail inside pcall (no engine); only the config load matters here
        q = rq.quests
        check("repeat quests: loaded", q is not None and len(q) > 0)
        if q is not None:
            q1 = q[1]
            check("repeat quests: cooldown 60 for every quest", q1.cd == 60, q1.cd)
            gen_timeouts = sorted(set(q[i].timeout for i in range(1, len(q) + 1)))
            check("repeat quests: timeout_mult 2 doubles 60 -> 120 and 2880 -> 5760", gen_timeouts == [120, 5760], gen_timeouts)

        ar = mod("alife_roaming")
        ar.host_reload()
        check("alife_roaming module loads", ar is not None)

        # ---- 3. the file is read again at reload; a deleted file is created again
        os.remove(cfg_path)
        line = host.reload()
        check("deleted file is created again", os.path.exists(cfg_path) and "file created with the defaults" in line)
        check("fresh file: defaults again", bal.cfg().player_damage_mult == 1.5)

        # ---- 4. a client never reads or writes the file
        os.remove(cfg_path)
        G["__server"] = False
        check("client: num returns the default", host.num("damage", "player_damage_mult", 1.5) == 1.5)
        check("client: bool returns the default", host.bool("damage", "log", True) is True)
        check("client: no file created", not os.path.exists(cfg_path))
        open(cfg_path, "wb").write(b"[damage]\nplayer_damage_mult = 5\n")
        host.reload()
        check("client: an existing file is ignored", host.num("damage", "player_damage_mult", 1.5) == 1.5)
        G["__server"] = True

        # ---- 5. unwritable folder: no error, defaults
        G2 = lua.execute(PRELUDE, find_file, os.path.join(tmp, "no", "such", "folder"))
        h2 = G2["__load_module"]("coop_host_cfg")
        check("unwritable folder: default and no error", h2.num("damage", "player_damage_mult", 1.5) == 1.5)
        check("unwritable folder: summary says so", "could not be created" in h2.last_line, h2.last_line[:160])

        # ---- 6. optional sarcophagus package: its section is written and read
        global OPTIONAL
        OPTIONAL = True
        G3 = lua.execute(PRELUDE, find_file, tmp)
        os.remove(cfg_path)
        sar = G3["__load_module"]("sar_fps_cfg")
        h3 = G3["__load_module"]("coop_host_cfg")
        h3.num("x", "y", 0)
        text3 = open(cfg_path, "rb").read().decode("utf-8")
        check("sarcophagus package: section written with its defaults", "[sarcophagus_fps]" in text3 and "corpse_limit = 30" in text3 and "sarcophagus_wave_percent = 100" in text3)
        with open(cfg_path, "r", encoding="utf-8") as f:
            t = f.read().replace("corpse_limit = 30", "corpse_limit = 55")
        open(cfg_path, "wb").write(t.encode("utf-8"))
        h3.reload()
        check("sarcophagus package: host value wins", sar.get("corpse_limit") == 55, sar.get("corpse_limit"))
        check("sarcophagus package: other values keep the default", sar.get("sarcophagus_corpse_limit") == 12)

        # ---- 7. the in-game hook (host_cfg_test.lua) against the same mock, with a stub test-bot library
        OPTIONAL = False
        G4 = lua.execute(PRELUDE, find_file, tmp)
        G4["__set_actors"]()
        lua.execute(HOOK_STUB, G4, os.path.join(HERE, "host_cfg_test.lua"))
        asserts = G4["__asserts"]
        n_pass = n_fail = 0
        for i in range(1, len(asserts) + 1):
            name, ok, detail = asserts[i][1], asserts[i][2], asserts[i][3]
            if ok:
                n_pass += 1
            else:
                n_fail += 1
                check("hook: " + name, False, detail)
        check("hook host_cfg_test.lua ran %d asserts, all PASS against the mock" % (n_pass + n_fail), n_fail == 0 and n_pass >= 30, "pass %d fail %d" % (n_pass, n_fail))

        print("\nlog sample:")
        for l in [G["__log"][i] for i in range(1, 5)]:
            print("  " + str(l)[:160])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s (%d failed)" % ("ALL PASS" if not fails else "FAILED", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
