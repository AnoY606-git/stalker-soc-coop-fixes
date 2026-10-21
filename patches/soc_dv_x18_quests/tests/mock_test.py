"""Offline check (no game) of coop_soc_dv.script (the chain tick) and coop_soc_bar.script (Barkeep dialog states, rewards, voice).
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL scripts in a Lua 5.1 VM with a small engine mock (story flags, players with position and inventory, level tick, task hand-out)."""
import os
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
fails = 0


def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + ((" : " + str(info)) if info != "" else ""))
    if not ok:
        fails += 1


PRELUDE = r'''
local dv_path, bar_path, patch_root = ...
local E = { string = string, table = table, math = math, io = io, os = os, pairs = pairs, ipairs = ipairs, pcall = pcall, tonumber = tonumber,
	tostring = tostring, type = type, setmetatable = setmetatable, getmetatable = getmetatable, error = error, select = select, unpack = unpack,
	next = next, assert = assert, rawget = rawget, rawset = rawset, print = print, loadstring = loadstring, setfenv = setfenv }
E._G = E
E.__log = {}
E.__time = 0
E.__given = {}                 -- "task|player" -> count
E.__calls = {}
E.__client = false
E.__played = {}
E.__voice_lang = "eng"
function E.printf_msg(fmt, ...) E.__log[#E.__log + 1] = string.format(fmt, ...) end
function E.time_global() return E.__time end
function E.OnServer() return not E.__client end
function E.OnClient() return E.__client end
function E.IsActorNetReady(id) return true end
function E.GiveTaskToClient(task, pid) local k = task .. "|" .. pid; E.__given[k] = (E.__given[k] or 0) + 1 end
local V = {}
V.__index = V
function V:set(x, y, z) self.x, self.y, self.z = x, y, z; return self end
function E.vector() return setmetatable({ x = 0, y = 0, z = 0 }, V) end
local flags = {}
E.story_flags = { has_flag = function(n) return flags[string.upper(n)] == true end,
	give_flag = function(n) flags[string.upper(n)] = true end,
	disable_flag = function(n) flags[string.upper(n)] = nil end }
function E.__reset_flags() for k in pairs(flags) do flags[k] = nil end end
E.__level = "coop_l04_darkvalley"
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end }
E.db = { mp_actors = {} }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z), __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec) return self.__items[sec] end
	E.db.mp_actors[id] = o
	return o
end
-- voice mock
E.coop_soc_opening = { voice_lang = function() return E.__voice_lang end }
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
E.dialogs = { who_is_npc = function(a, b) if a == nil then return nil, b end return b, a end }
E.__money = 0
E.dialogs_money = { give_money_to_actor_5000 = function() E.__money = E.__money + 5000 end,
	give_money_to_actor_10000 = function() E.__money = E.__money + 10000 end }
E.__transfers = {}
E.dialogs_coop_l05_bar = {}
for _, n in ipairs({ "transfer_agr_safe_container_1", "transfer_dev_flash_agru", "transfer_dev_document_1_x18", "transfer_dev_document_2_x18", "transfer_dev_document_3_x18" }) do
	E.dialogs_coop_l05_bar[n] = function() E.__transfers[#E.__transfers + 1] = n end
end
local function mk_sound(path)
	local s = { path = path }
	function s:playing() return false end
	function s:stop() end
	function s:play(o, d, f) E.__played[#E.__played + 1] = path end
	return s
end
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(t, path) return mk_sound(path) end })
E.__me = nil
function E.getLocalActor() return E.__me end
E.getFS = function() return { exist = function(self, root, name)
	for _, r in ipairs({ patch_root, patch_root .. "/../bar_soc_quests", patch_root .. "/../soc_ru_voices" }) do
		local f = io.open(r .. "/gamedata/sounds/" .. string.gsub(name, "\\", "/"), "rb")
		if f then f:close() return true end
	end
	return false end } end
E.game = { translate_string = function(s) return "Windowed" end }

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
E.coop_soc_dv = load(dv_path, "coop_soc_dv")
E.coop_soc_bar = load(bar_path, "coop_soc_bar")
return E
'''

BASE = (36.0, -70.0)


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    E = lua.execute(PRELUDE, os.path.join(PATCH, "gamedata", "scripts", "coop_soc_dv.script"),
                    os.path.join(PATCH, "gamedata", "scripts", "coop_soc_bar.script"), PATCH.replace("\\", "/"))
    dv, bar = E["coop_soc_dv"], E["coop_soc_bar"]

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(n):
        E["story_flags"]["give_flag"](n)

    def reset():
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__level"] = "coop_l04_darkvalley"
        dv["reset_given"]()

    def player(pid, x=0.0, z=-300.0):
        return E["__player"](pid, "p%d" % pid, x, 0.0, z)

    def move(p, x, z):
        p["__pos"] = E["vector"]()
        p["__pos"]["x"], p["__pos"]["y"], p["__pos"]["z"] = x, 0.0, z

    def step():
        return dv["step"]()

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def all_tasks():
        return sorted(k for k in E["__given"].keys())

    # ---------------------------------------------------------------- chain
    reset()
    p1, p2 = player(1), player(2)
    step()
    check("nothing is given before the job", len(all_tasks()) == 0, all_tasks())

    give("ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO")
    step()
    check("the Sidorovich job alone gives no Dark Valley task", len(all_tasks()) == 0, all_tasks())

    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO")
    step()
    check("job accepted: 'sneak into the base' to BOTH players", given("val_soc_darklab_1_task", 1) == 1 and given("val_soc_darklab_1_task", 2) == 1)
    check("job accepted: the old autosave flag of the Borov logic is set", flag("BAR_START_SNEAK_INTO_THE_X_18_LAB_QUEST_TASK_INFO"))
    step(); step()
    check("tasks are given once per player", given("val_soc_darklab_1_task", 1) == 1 and len(all_tasks()) == 2, all_tasks())
    check("no later objective yet", given("val_soc_darklab_2_task", 1) == 0)

    move(p1, BASE[0] + 10, BASE[1] + 5)
    step()
    check("a player in the bandit base: VAL_ACTOR_ON_BANDITS_BASE", flag("VAL_ACTOR_ON_BANDITS_BASE"))
    check("'take Borov's key' to both players", given("val_soc_darklab_2_task", 1) == 1 and given("val_soc_darklab_2_task", 2) == 1)

    # Borov is killed by somebody (NPC or player): the key step ends without any item check
    give("VAL_SMART_TERRAIN_12_BANDIT_1_SQUAD_DEAD")
    step()
    check("Borov dead: key flag set (no soft-lock)", flag("VAL_ACTOR_HAS_BOROV_KEY"))
    check("'get out of the bandit base' given to both", given("val_soc_darklab_3_task", 1) == 1 and given("val_soc_darklab_3_task", 2) == 1)
    check("not left yet while p1 is inside", not flag("VAL_ACTOR_LEAVE_BANDITS_BASE"))
    move(p1, BASE[0] + 120, BASE[1])
    step()
    check("every player farther than 75 m: VAL_ACTOR_LEAVE_BANDITS_BASE", flag("VAL_ACTOR_LEAVE_BANDITS_BASE"))
    check("'find the entrance to the lab' given to both", given("val_soc_darklab_4_task", 1) == 1 and given("val_soc_darklab_4_task", 2) == 1)

    # late joiner: gets every task that is open right now, and only those
    p3 = player(3, BASE[0] + 120, BASE[1])
    step()
    check("late joiner gets the open objective", given("val_soc_darklab_4_task", 3) == 1)
    check("late joiner does not get finished objectives", given("val_soc_darklab_1_task", 3) == 0 and given("val_soc_darklab_2_task", 3) == 0
          and given("val_soc_darklab_3_task", 3) == 0)

    # entering the lab: SoC bar_darklab_documents2 starts, bar_darklab_documents is done
    give("VAL_START_SNEAK_INTO_THE_X_18_LAB_1_QUEST_TASK_INFO")
    step()
    check("lab entered: VAL_X18_DOOR_OPEN and DAR_RUN_QUEST", flag("VAL_X18_DOOR_OPEN") and flag("DAR_RUN_QUEST"))
    check("'Find the documents' (bar_darklab_documents2) to all three", all(given("val_start_sneak_into_the_x_18_lab_1_quest_task", i) == 1 for i in (1, 2, 3)))
    p4 = player(4)
    step()
    check("late joiner in the lab gets 'Find the documents' only", given("val_start_sneak_into_the_x_18_lab_1_quest_task", 4) == 1
          and given("val_soc_darklab_4_task", 4) == 0)

    # code doors
    give("DAR_DOOR1_CLOSED")
    step()
    check("door 1 used: 'discover the code' to everybody", all(given("x18_soc_codedoor_1_code_task", i) == 1 for i in (1, 2, 3, 4)))
    check("door 1: 'open the door' not yet", given("x18_soc_codedoor_1_open_task", 1) == 0)
    p2["__items"]["dev_document_1_x18"] = True
    step()
    check("document 1 found: flag X18_START_GO_TO_X18_DOC_1_TASK_INFO", flag("X18_START_GO_TO_X18_DOC_1_TASK_INFO"))
    check("door 1: 'open the door using the code' to everybody", all(given("x18_soc_codedoor_1_open_task", i) == 1 for i in (1, 2, 3, 4)))
    give("X18_CODEDOOR_1_OPEN_INFO")
    give("DAR_DOOR2_CLOSED")
    give("X18_START_GO_TO_X18_DOC_2_TASK_INFO")
    step()
    check("door 2 with the code already known goes straight to 'open the door'", given("x18_soc_codedoor_2_open_task", 1) == 1 and given("x18_soc_codedoor_2_code_task", 1) == 0)

    # documents: the party holds all three (spread over players), the Barkeep is the target
    p1["__items"]["dev_document_2_x18"] = True
    p3["__items"]["dev_document_3_x18"] = True
    step()
    check("all three documents (two players): BAR_DARKLAB_DOCUMENT_GAIN", flag("BAR_DARKLAB_DOCUMENT_GAIN"))
    check("'Bring the documents to the Barkeep' to every player", all(given("val_start_take_the_documents_to_the_barmen_quest_task", i) == 1 for i in (1, 2, 3, 4)))
    give("VAL_RAID_START")
    step()
    check("raid: 'Get out of the Dark Valley' (val_come_to_trader) to every player", all(given("val_start_get_out_via_south_gate_quest_task", i) == 1 for i in (1, 2, 3, 4)))
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO")
    step()
    check("documents handed to the Barkeep: the Yantar line is NOT given here (it starts when the X16 job is accepted, patch bar_soc_quests)",
          all(given("bar_start_go_to_yantar_quest_task", i) == 0 for i in (1, 2, 3, 4)))

    # --- skipping: a fresh game that goes straight to the lab
    reset()
    player(1)
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO")
    give("VAL_START_SNEAK_INTO_THE_X_18_LAB_1_QUEST_TASK_INFO")
    step()
    check("lab first: every earlier flag is set, no stale Barkeep-job task", flag("VAL_ACTOR_ON_BANDITS_BASE") and flag("VAL_ACTOR_HAS_BOROV_KEY")
          and flag("VAL_ACTOR_LEAVE_BANDITS_BASE") and given("val_soc_darklab_1_task", 1) == 0 and given("val_soc_darklab_4_task", 1) == 0, all_tasks())
    check("lab first: 'Find the documents' is given", given("val_start_sneak_into_the_x_18_lab_1_quest_task", 1) == 1)

    # --- documents already handed in: no X18 task is offered any more
    reset()
    player(1)
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO")
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO")
    give("VAL_RAID_START")
    step()
    t = all_tasks()
    check("done at the Barkeep: no task is given, val_come_to_trader is not given (SoC: it fails)", t == [], t)

    # --- Bullet / captive / Serega
    reset()
    player(1)
    player(2)
    give("VAL_ESCORT_TASK_START")
    step()
    check("Bullet asks: 'Free the Dutyer' (follow Bullet) to both", given("val_start_follow_the_bullet_quest_task", 1) == 1 and given("val_start_follow_the_bullet_quest_task", 2) == 1)
    give("VAL_SMART_TERRAIN_19_SPAWN_SQUAD_SPACE_RESTRICTOR_INFO")
    step()
    check("ambush reached: second objective to both", given("val_start_save_the_prisoner_quest_task", 1) == 1 and given("val_start_save_the_prisoner_quest_task", 2) == 1)
    check("no prisoner task before the captors are dead", given("val_soc_prisoner_task", 1) == 0)
    give("VAL_SMART_TERRAIN_19_BANDIT_1_SQUAD_DEAD")
    step()
    check("captors dead: 'Free the Dutyer from prison' (Serega) to both", given("val_soc_prisoner_task", 1) == 1 and given("val_soc_prisoner_task", 2) == 1)
    reset()
    player(1)
    give("VAL_ESCORT_TASK_START")
    give("VAL_SMART_TERRAIN_18_DUTY_BULLET_SQUAD_DEAD")
    step()
    check("Bullet dead before the task: nothing is given and nothing waits", len(all_tasks()) == 0, all_tasks())
    reset()
    player(1)
    give("VAL_SMART_TERRAIN_19_BANDIT_1_SQUAD_DEAD")
    give("VAL_SMART_TERRAIN_20_DUTY_1_SQUAD_DEAD")
    step()
    check("Serega dead: no prisoner task", given("val_soc_prisoner_task", 1) == 0)

    # --- dead / not ready players are skipped, a respawned one gets the open tasks
    reset()
    a, b = player(1), player(2)
    b["__alive"] = False
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO")
    step()
    check("a dead player is skipped", given("val_soc_darklab_1_task", 1) == 1 and given("val_soc_darklab_1_task", 2) == 0)
    b["__alive"] = True
    step()
    check("... and gets the task after the respawn", given("val_soc_darklab_1_task", 2) == 1)

    # the level tick registered itself
    dv["install"]()
    check("install registers one level call", len(list(E["__calls"].values())) >= 1)

    # ---------------------------------------------------------------- Barkeep dialog
    reset()
    st = lambda: bar["state"]()
    check("Barkeep: default greeting at the start", st() == "default")
    give("ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_GO_TO_FOX_STOP_DIALOG_INFO")
    check("Barkeep: asks for the Agroprom documents after Sidorovich's job", st() == "agroprom")
    give("BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO")
    check("Barkeep: offers the X18 job after the hand-in", st() == "offer")
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_GO_TO_DARKVALLEY_STOP_DIALOG_INFO")
    check("Barkeep: waits for the documents", st() == "wait")
    give("BAR_DARKLAB_DOCUMENT_GAIN")
    check("Barkeep: asks for the X18 documents", st() == "docs")
    give("BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO")
    check("Barkeep: offers the X16 job afterwards (SoC 19)", st() == "x16offer")
    reset()
    give("BAR_SMART_TERRAIN_1_TRADER_BARMEN_HAS_DOCUMENTS_AGROPROM_STOP_DIALOG_INFO")
    states = ["st_agroprom", "st_offer", "st_wait", "st_docs", "st_default", "st_x16offer", "st_x16docs", "st_radaroffer", "st_radar"]
    one = sum(1 for s in states if bar[s](None, None))
    check("exactly one state precondition is true", one == 1, one)

    me = E["__player"](9, "talker", 0.0, 0.0, 0.0)
    me["__items"]["agr_safe_container_1"] = True
    check("has_agroprom_docs: true with the container", bar["has_agroprom_docs"](None, me))
    me["__items"]["agr_safe_container_1"] = None
    check("has_agroprom_docs: false without it", not bar["has_agroprom_docs"](None, me))
    bar["take_agroprom_docs"](None, me)
    bar["reward_agroprom"](None, me)
    bar["take_x18_docs"](None, me)
    bar["reward_x18"](None, me)
    tr = sorted(str(x) for x in E["__transfers"].values())
    check("hand-ins use the stock transfers (container, flash drive, three documents)", len(tr) == 5, tr)
    check("rewards: 5000 (Agroprom) + 10000 (X18)", int(E["__money"]) == 15000, E["__money"])

    # voice: English recording only (the Russian SoC has none); per-player language
    voiced = list(bar["VOICE_IDS"].values())
    check("10 phrases have a recording (7 here, 3 in patch bar_soc_quests)", len(voiced) == 10, voiced)
    roots = [PATCH, os.path.join(os.path.dirname(PATCH), "bar_soc_quests"), os.path.join(os.path.dirname(PATCH), "soc_ru_voices")]
    for lang in ("eng", "rus"):
        E["__voice_lang"] = lang
        for pid in voiced:
            p = bar["voice_path"](pid)
            if lang == "eng":
                ok = p is not None and any(os.path.isfile(os.path.join(r, "gamedata", "sounds", p.replace("\\", os.sep) + ".ogg")) for r in roots)
                check("voice %s eng: file exists" % pid, ok, p)
            else:
                ok = p == "characters_voice\\dialogs\\bar_bar_barmen_start_" + pid and any(os.path.isfile(os.path.join(r, "gamedata", "sounds", p.replace("\\", os.sep) + ".ogg")) for r in roots)
                check("voice %s rus: Russian file (soc_ru_voices)" % pid, ok, p)
    E["__voice_lang"] = "eng"
    check("a line without a recording is silent", bar["voice_path"]("211") is None)

    # say(): plays on the talking client only, archive line for everybody
    E["__client"] = True
    E["__me"] = me
    npc = E["__player"](10, "barman", 0.0, 0.0, 0.0)
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    bar["say_221"](npc, me)
    played = list(E["__played"].values())
    check("say_221 on the talker's machine plays the English recording", played == ["characters_voice\\dialogs\\eng\\bar_bar_barmen_start_221"], played)
    other = E["__player"](11, "other", 0.0, 0.0, 0.0)
    E["__me"] = other
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    bar["say_221"](npc, me)
    check("say_221 on another player's machine is silent", len(list(E["__played"].values())) == 0)
    E["__me"] = me
    E["__voice_lang"] = "rus"
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    bar["say_221"](npc, me)
    played = list(E["__played"].values())
    check("say_221 with voice_language rus plays the Russian recording", played == ["characters_voice\\dialogs\\bar_bar_barmen_start_221"], played)
    E["__client"] = False
    log = [str(x) for x in E["__log"].values()]
    check("the PDA archive line is emitted", any(x == "EMIT coop_soc_barman_221" for x in log))

    print("\n%d FAIL" % fails if fails else "\nALL PASS")
    sys.exit(1 if fails else 0)


main()
