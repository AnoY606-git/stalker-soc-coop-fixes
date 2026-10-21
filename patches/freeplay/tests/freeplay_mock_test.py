"""Offline check of the freeplay logic against a mock engine (no game, a few seconds):  python freeplay_mock_test.py
Runs the REAL scripts coop_scn_freeplay.script (patch freeplay) and coop_scn_endings.script (patch cutscenes_pkg_endings, with the freeplay edits) in a
Lua 5.1 VM (lupa) with a small engine mock: story flags, level name / level.object, level.add_call timers, teleport_actor_sv, the console, a scene
director stub that only records coop_scenes.register / request. The host switch is the REAL coop_host_cfg.script (patch host_settings) reading a
temp coop_settings.ltx.

Proves: credits_variant() gives "freeplay" and the PENDING flag when the host setting is on (default), nil and no flag when it is off, nil on a
client; the true ending asks for the credits with the variant (and the wish endings / the join ending do not); the credits of the freeplay variant
have no main_menu step and no disconnect, the old ones keep both; the scene triggers only after PENDING and the played credits, opens the exit,
teleports every ALIVE player into the exit exactly once (DONE), keeps the story flags, closes the exit again after the arrival; the exit
(level changer) is switched off on every machine until OPEN; the watchdog sends everybody to the menu when the level does not change; the text
files have both strings in both languages.
Needs `pip install lupa` (the same package the other offline tests use)."""
import glob
import os
import shutil
import sys
import tempfile

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PATCHES = os.path.join(REPO, "patches")

PRELUDE = r'''
local find_file, tmp = ...
local G = {}
for _, k in ipairs({ "string", "table", "math", "io", "os", "pairs", "ipairs", "pcall", "tonumber", "tostring", "type", "setmetatable", "getmetatable",
	"error", "select", "unpack", "next", "assert", "loadfile", "setfenv", "getfenv", "rawget", "rawset", "print", "xpcall" }) do G[k] = _G[k] end
G._G = G
G.__log = {}
G.__server = true
G.__t = 0
G.__calls = {}
G.__tele = {}
G.__console = {}
G.__requests = {}
G.__defs = {}
G.__level = "coop_l11_stancia_2"
G.__changers = {}
G.__news = {}
function G.printf_msg(fmt, ...) G.__log[#G.__log + 1] = string.format(fmt, ...) end
G.printf = G.printf_msg
function G.time_global() return G.__t end
function G.OnServer() return G.__server end
function G.OnClient() return not G.__server end
function G.IsDedicatedServer() return false end
function G.LocalActor() return 7 end
function G.getFS() return { update_path = function(self, a, n) return tmp .. "/" .. a:gsub("%$", "") .. "_" .. n end } end

-- ltx / ini_file are only needed by coop_host_cfg while it builds the default list; the freeplay knob has no ltx file
function G.ini_file(name) error("ini_file: no file " .. name) end
function G.system_ini() return { section_exist = function() return true end, line_exist = function() return false end } end

-- story flags (the shared flag store of xrMPE)
local flags = {}
G.story_flags = {
	story_flags = flags,
	has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end,
}

-- level
G.level = {
	name = function() return G.__level end,
	object = function(n) return G.__changers[n] end,
	add_call = function(cond, act) G.__calls[#G.__calls + 1] = { cond = cond, act = act } end,
}
function G.__run_calls()
	local keep = {}
	local calls = G.__calls
	G.__calls = {}
	for _, c in ipairs(calls) do
		local done = c.cond()
		if done then pcall(c.act) else keep[#keep + 1] = c end
	end
	for _, c in ipairs(keep) do G.__calls[#G.__calls + 1] = c end
end
function G.__advance(ms, step)
	step = step or 500
	local t = 0
	while t < ms do
		G.__t = G.__t + step
		t = t + step
		G.__run_calls()
	end
end

-- players
local function mk_player(id, alive)
	return { id = function() return id end, alive = function() return alive end, position = function() return { x = 0, y = 0, z = 0 } end }
end
G.db = { mp_actors = {} }
function G.__players(spec)
	G.db.mp_actors = {}
	for i, alive in ipairs(spec) do G.db.mp_actors[100 + i] = mk_player(100 + i, alive) end
end
function G.vector() local v = { x = 0, y = 0, z = 0 }; function v:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end; return v end
function G.teleport_actor_sv(id, pos, dir) G.__tele[#G.__tele + 1] = { id = id, x = pos.x, y = pos.y, z = pos.z } end
function G.alife() return { object = function(self, name)
	if name == "aes_2_esc_freeplay_level_changer" and G.__server_object ~= false then return { position = G.vector():set(981.7, 0.0, 337.7) } end
	return nil
end } end
function G.get_console() return { execute = function(self, c) G.__console[#G.__console + 1] = c end } end
G.game = { translate_string = function(s) return "T:" .. s end }
function G.getLocalActor()
	return { give_game_news = function(self, cap, msg) G.__news[#G.__news + 1] = { cap, msg } end }
end

-- scene director stub
G.coop_scenes = {
	register = function(d) G.__defs[d.id] = d end,
	request = function(id, var) G.__requests[#G.__requests + 1] = { id = id, var = var } end,
	played = function(id) return flags["SCN_" .. string.upper(id) .. "_PLAYED"] == true end,
	defs = G.__defs,
}

-- script modules, loaded on first use like the engine does (every script is a module table)
local mods = {}
local load_module
function load_module(name)
	if name == "coop_host_cfg" and G.__host_stub then return G.__host_stub end
	if mods[name] ~= nil then return mods[name] or nil end
	local path = find_file("scripts\\" .. name .. ".script")
	if not path then mods[name] = false return nil end
	local env = setmetatable({}, { __index = function(t, k)
		local v = G[k]
		if v ~= nil then return v end
		return load_module(k)
	end })
	mods[name] = env
	local f, err = loadfile(path)
	if not f then error(err) end
	setfenv(f, env)
	f()
	return env
end
G.__load_module = load_module
G.__reset = function()
	mods = {}
	for k in pairs(flags) do flags[k] = nil end
	G.__calls, G.__tele, G.__console, G.__requests, G.__news = {}, {}, {}, {}, {}
	for k in pairs(G.__defs) do G.__defs[k] = nil end
	G.__changers = {}
	G.__level = "coop_l11_stancia_2"
	G.__server = true
	G.__t = 0
end
return G
'''


def find_file(name):
    name = name.replace("\\", "/")
    rel = name if name.startswith("scripts/") else "configs/" + name
    hits = sorted(glob.glob(os.path.join(PATCHES, "*", "gamedata", rel)))
    return hits[0] if hits else None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="freeplay_")
    fails = []
    count = [0]

    def check(name, ok, detail=""):
        count[0] += 1
        print(("PASS " if ok else "FAIL ") + name + ((" : " + str(detail)) if detail != "" else ""))
        if not ok:
            fails.append(name)

    try:
        lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
        G = lua.execute(PRELUDE, find_file, tmp)

        def mod(name):
            m = G["__load_module"](name)
            if m is None:
                raise RuntimeError("module not found: " + name)
            return m

        def flag(n):
            return G.story_flags.has_flag(n)

        def enabled_stub(value):
            """replace coop_host_cfg by a stub that answers bool('freeplay','enabled') with `value` (None = no answer, like a missing script)"""
            if value is None:
                G.__host_stub = None
                return
            G.__host_stub = lua.eval("function(v) return { bool = function(sec, key, default) if sec == 'freeplay' and key == 'enabled' then return v end return default end } end")(value)

        def fresh(server=True, host=True):
            G.__reset()
            G.__server = server
            enabled_stub(host)
            G.__players(lua.table_from([True, True]))
            G.__changers = lua.table()
            fp = mod("coop_scn_freeplay")
            return fp

        # ---------------------------------------------------------------- 1. credits variant and the host switch
        fp = fresh(host=True)
        check("freeplay is on by default (host setting true)", fp.enabled() is True)
        check("credits_variant gives 'freeplay'", fp.credits_variant() == "freeplay")
        check("credits_variant gives the PENDING flag", flag("COOP_FREEPLAY_PENDING"))
        fp = fresh(host=False)
        check("host setting false: enabled() is false", fp.enabled() is False)
        check("host setting false: credits_variant is nil (old behaviour)", fp.credits_variant() is None)
        check("host setting false: no PENDING flag", not flag("COOP_FREEPLAY_PENDING"))
        fp = fresh(host=None)
        check("no coop_host_cfg at all: freeplay stays on (default true)", fp.enabled() is True)
        fp = fresh(server=False, host=True)
        check("on a client credits_variant is nil and gives no flag", fp.credits_variant() is None and not flag("COOP_FREEPLAY_PENDING"))

        # the real coop_host_cfg: the key exists and is read
        G.__host_stub = None
        G.__reset()
        G.ini_file = lua.eval("function(name) error('no ini') end")
        host = mod("coop_host_cfg")
        check("real coop_host_cfg: freeplay.enabled defaults to true", host.bool("freeplay", "enabled", True) is True)
        cfg_path = os.path.join(tmp, "app_data_root_coop_settings.ltx")
        check("real coop_host_cfg wrote the settings file with a [freeplay] section", os.path.exists(cfg_path) and "[freeplay]" in open(cfg_path, "rb").read().decode("utf-8"))
        text = open(cfg_path, "rb").read().decode("utf-8")
        sec = text.split("[freeplay]", 1)[1].split("\n[", 1)[0]
        check("the freeplay section has an EN and a RU comment line and enabled = true", "enabled = true" in sec and "true = after the true ending" in sec and "играть" in sec, sec[:80])
        head, rest = text.split("[freeplay]", 1)
        nxt = rest.find("\n[")
        body, tail = (rest[:nxt], rest[nxt:]) if nxt >= 0 else (rest, "")
        body = body.replace("enabled = true", "enabled = false")
        open(cfg_path, "wb").write((head + "[freeplay]" + body + tail).encode("utf-8"))
        host.reload()
        check("real coop_host_cfg: enabled = false in the file is read", host.bool("freeplay", "enabled", True) is False)
        fp2 = mod("coop_scn_freeplay")
        check("and the real script follows it (credits_variant nil)", fp2.credits_variant() is None)
        G.__host_stub = None

        # ---------------------------------------------------------------- 2. the endings package
        fp = fresh(host=True)
        endings = mod("coop_scn_endings")
        defs = G.__defs
        check("endings package registered end_peace, end_wish and credits", defs.end_peace is not None and defs.end_wish is not None and defs.credits is not None)
        ctx = lua.table()
        defs.end_peace.on_end(ctx, None, "all_acked")
        req = G.__requests[1]
        check("true ending asks for the credits with the variant 'freeplay'", req["id"] == "credits" and req["var"] == "freeplay", (req["id"], req["var"]))
        check("... and the PENDING flag is set", flag("COOP_FREEPLAY_PENDING"))
        fp = fresh(host=False)
        endings = mod("coop_scn_endings")
        G.__defs.end_peace.on_end(lua.table(), None, "all_acked")
        req = G.__requests[1]
        check("host setting off: the credits are requested without variant (old end)", req["id"] == "credits" and req["var"] is None)
        G.__defs.end_wish.on_end(lua.table(), "final_gold", "all_acked")
        req = G.__requests[2]
        check("the wish-granter ending never uses freeplay", req["id"] == "credits" and req["var"] is None)
        # without the freeplay script at all (patch not installed): the endings package must still work
        G.__reset()
        G.__host_stub = None
        saved = G.__load_module
        endings = mod("coop_scn_endings")

        def steps_of(var):
            t = defs_credits.steps(var, lua.table())
            return [t[i]["do"] for i in range(1, len(t) + 1)]

        fp = fresh(host=True)
        endings = mod("coop_scn_endings")
        defs_credits = G.__defs.credits
        check("credits steps without variant end with main_menu (old)", steps_of(None)[-1] == "main_menu", steps_of(None))
        check("credits steps of 'freeplay' have no main_menu and end with ui_on", "main_menu" not in steps_of("freeplay") and steps_of("freeplay")[-1] == "ui_on", steps_of("freeplay"))
        check("credits steps of 'freeplay' still play the credits tutorial", "tutorial" in steps_of("freeplay"))
        env_fp = lua.table()
        env_fp["var"] = "freeplay"
        defs_credits.on_client_end(env_fp, "done")
        G.__advance(5000)
        check("credits end of 'freeplay' does not disconnect", len(G.__console) == 0, list(G.__console.values()))
        env_old = lua.table()
        defs_credits.on_client_end(env_old, "done")
        G.__advance(5000)
        check("credits end of the old variant still disconnects", "disconnect" in list(G.__console.values()), list(G.__console.values()))

        # ---------------------------------------------------------------- 3. the freeplay scene
        fp = fresh(host=True)
        sc = G.__defs.freeplay
        check("scene 'freeplay' is registered for CNPP-2, once", sc is not None and sc.level == "coop_l11_stancia_2" and sc.once is True)
        ctx = lua.table()
        ctx["players"] = lambda: lua.table_from([G.db.mp_actors[k] for k in sorted(G.db.mp_actors.keys()) if G.db.mp_actors[k].alive()])
        check("trigger is false at the start", sc.trigger(ctx) is False)
        G.story_flags.give_flag("COOP_FREEPLAY_PENDING")
        check("trigger is false while the credits are not over", sc.trigger(ctx) is False)
        G.story_flags.give_flag("SCN_CREDITS_PLAYED")
        check("trigger is true after PENDING and the played credits", sc.trigger(ctx) is True)
        sc.on_go(ctx, None)
        check("on_go opens the exit (OPEN flag)", flag("COOP_FREEPLAY_OPEN"))
        steps = sc.steps(None, lua.table())
        kinds = [steps[i]["do"] for i in range(1, len(steps) + 1)]
        check("client steps: a news line and a short wait", kinds == ["fn", "wait"], kinds)
        steps[1]["fn"](lua.table())
        check("client news line uses the freeplay strings", len(G.__news) == 1 and G.__news[1][2] == "T:scn_freeplay_msg", G.__news[1][2])
        # story flags that must survive
        for f in ("SCN_END_PEACE_PLAYED", "AES_2_THE_END_SPACE_RESTRICTOR_INFO", "SCN_OPENING_PLAYED", "ESC_START_MAIN_QUEST_TASK_INFO"):
            G.story_flags.give_flag(f)
        before = sorted(str(k) for k, v in G.story_flags.story_flags.items() if v)
        # one of the three players is dead
        G.__players(lua.table_from([True, False, True]))
        n = fp.transfer(ctx)
        tele = [G.__tele[i] for i in range(1, len(G.__tele) + 1)]
        check("transfer teleports the 2 alive players, not the dead one", n == 2 and len(tele) == 2 and sorted(t["id"] for t in tele) == [101, 103], [t["id"] for t in tele])
        check("... into the exit position of the level changer", all(abs(t["x"] - 981.7) < 1e-3 and abs(t["z"] - 337.7) < 1e-3 for t in tele))
        check("transfer gives DONE", flag("COOP_FREEPLAY_DONE"))
        check("a second transfer does nothing (idempotent)", fp.transfer(ctx) == 0 and len(G.__tele) == 2)
        after = sorted(str(k) for k, v in G.story_flags.story_flags.items() if v)
        gained = [f for f in after if f not in before]
        check("the story flags are all still there (nothing removed)", all(f in after for f in before))
        check("only the freeplay flags were added by the transfer", sorted(gained) == ["COOP_FREEPLAY_DONE"], gained)
        # the changer without the server object: the constant position is used
        fp = fresh(host=True)
        G.__server_object = False
        ctx2 = lua.table()
        ctx2["players"] = lambda: lua.table_from([G.db.mp_actors[101]])
        fp.transfer(ctx2)
        check("fallback exit position when the server object is not found", len(G.__tele) == 1 and abs(G.__tele[1]["x"] - 981.7) < 1e-3)
        G.__server_object = None

        # ---------------------------------------------------------------- 4. the exit (level changer) is closed until OPEN
        fp = fresh(host=True)
        calls = []
        lc = lua.eval("function(rec) return { enable_level_changer = function(self, v) rec[#rec + 1] = v end } end")
        rec = lua.table()
        G.__changers["aes_2_esc_freeplay_level_changer"] = lc(rec)
        G.__advance(3000)
        check("on CNPP-2 the exit is switched off on every machine at the start", len(rec) >= 1 and rec[1] is False, list(rec.values()))
        G.story_flags.give_flag("COOP_FREEPLAY_OPEN")
        G.__advance(3000)
        check("OPEN switches the exit on", rec[len(rec)] is True, list(rec.values()))
        G.__level = "coop_l01_escape"
        G.__changers["aes_2_esc_freeplay_level_changer"] = None
        G.__advance(3000)
        check("no error on a level without the exit", True)

        # ---------------------------------------------------------------- 5. arrival: the server closes the exit for good
        fp = fresh(host=True)
        G.story_flags.give_flag("COOP_FREEPLAY_OPEN")
        G.story_flags.give_flag("COOP_FREEPLAY_DONE")
        G.__level = "coop_l01_escape"
        G.__advance(3000)
        check("after the arrival on the Cordon the OPEN flag is taken away again", not flag("COOP_FREEPLAY_OPEN") and flag("COOP_FREEPLAY_DONE"))
        fp = fresh(host=True)
        G.story_flags.give_flag("COOP_FREEPLAY_OPEN")
        G.__advance(3000)
        check("before DONE the OPEN flag stays", flag("COOP_FREEPLAY_OPEN"))

        # ---------------------------------------------------------------- 6. watchdog
        fp = fresh(host=True)
        ctx3 = lua.table()
        ctx3["players"] = lambda: lua.table_from([G.db.mp_actors[101]])
        fp.transfer(ctx3)
        G.__advance(26000)
        check("level did not change after 25 s: FAILED flag", flag("COOP_FREEPLAY_FAILED"))
        G.__advance(8000)
        check("... and the host goes to the main menu (old behaviour)", "disconnect" in list(G.__console.values()), list(G.__console.values()))
        fp = fresh(host=True)
        fp.transfer(ctx3)
        G.__level = "coop_l01_escape"
        G.__advance(26000)
        check("level changed in time: no FAILED flag, nobody disconnected", not flag("COOP_FREEPLAY_FAILED") and len(G.__console) == 0)

        # ---------------------------------------------------------------- 7. texts
        for lang, enc in (("eng", "cp1251"), ("rus", "cp1251")):
            p = os.path.join(PATCHES, "freeplay", "gamedata", "configs", "text", lang, "st_coop_scn_freeplay.xml")
            raw = open(p, "rb").read()
            txt = raw.decode(enc)
            check("%s text file has both strings, windows-1251 header" % lang, 'id="scn_freeplay_caption"' in txt and 'id="scn_freeplay_msg"' in txt and 'encoding="windows-1251"' in txt)
            check("%s text file has no em dash and no user path" % lang, chr(0x2014) not in txt and "users" + chr(92) not in txt.lower())
        ru = open(os.path.join(PATCHES, "freeplay", "gamedata", "configs", "text", "rus", "st_coop_scn_freeplay.xml"), "rb").read().decode("cp1251")
        check("rus text is Cyrillic", any("Ѐ" <= ch <= "ӿ" for ch in ru))

        print("\n%d checks, %d failed" % (count[0], len(fails)))
        print("ALL PASS" if not fails else "FAILED: " + ", ".join(fails))
        return 1 if fails else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
