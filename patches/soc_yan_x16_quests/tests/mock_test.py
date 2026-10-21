"""Offline check (no game) of coop_soc_yan.script: the Yantar / X16 chain tick, the Sakharov / Kruglov dialog states, the items the server hands out,
the measurement zones, the voice lines.
usage: python mock_test.py        (needs `pip install lupa`)
Runs the REAL script in a Lua 5.1 VM with a small engine mock (story flags, players with position and inventory, alife().create, task hand-out)."""
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
local path, patch_root = ...
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
E.__created = {}               -- list of "section|player or world"
E.__fail_create = false
E.__story = {}                 -- story id -> server entity id
E.__guide_pos = nil
E.__vas_online = nil
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
E.__level = "coop_l08_yantar"
local nextid = 100
E.level = { name = function() return E.__level end, add_call = function(f, g) E.__calls[#E.__calls + 1] = f end,
	vertex_id = function(pos) return 77 end,
	object_by_id = function(id)
		if id == 500 and E.__guide_online then return { position = function() return E.__guide_pos end } end
		if E.__vas_online and E.__vas_online.id == id then return E.__vas_online end
		return nil end }
E.get_story_object_id = function(s) return E.__story[s] end
E.alife = function() return {
	create = function(self, section, pos, lv, gv, parent)
		if E.__fail_create and (section == "yan_vasilyev") then error("create failed") end
		nextid = nextid + 1
		local se = { id = nextid, section = section, kill = function() end }
		if parent ~= nil then
			E.__created[#E.__created + 1] = section .. "|" .. parent
			local p = E.db.mp_actors[parent]
			if p then p.__items[section] = true end
		else
			E.__created[#E.__created + 1] = section .. "|world"
			if section == "yan_vasilyev" then E.__story["yan_vasilyev"] = se.id end
		end
		return se
	end,
	object = function(self, id) if id == 500 and E.__guide_pos then return { position = E.__guide_pos } end return nil end } end
E.db = { mp_actors = {} }
function E.__player(id, name, x, y, z)
	local o = { __id = id, __name = name, __alive = true, __pos = E.vector():set(x, y, z), __items = {} }
	function o:id() return self.__id end
	function o:name() return self.__name end
	function o:alive() return self.__alive end
	function o:position() return self.__pos end
	function o:object(sec) if self.__items[sec] then return true end return nil end
	function o:level_vertex_id() return 1 end
	function o:game_vertex_id() return 2 end
	E.db.mp_actors[id] = o
	return o
end
E.coop_soc_opening = { voice_lang = function() return E.__voice_lang end }
E.coop_pda_phrases = { phrase_speaker = {} }
E.coop_pda_archive_sync = { emit_phrase = function(a, b, tid) E.__log[#E.__log + 1] = "EMIT " .. tid end }
local function mk_sound(p)
	local s = { path = p }
	function s:playing() return false end
	function s:stop() end
	function s:play(o, d, f) E.__played[#E.__played + 1] = p end
	return s
end
E.sound_object = setmetatable({ s2d = 1 }, { __call = function(t, p) return mk_sound(p) end })
E.__me = nil
function E.getLocalActor() return E.__me end
E.getFS = function() return { exist = function(self, root, name)
	for _, r in ipairs({ patch_root, patch_root .. "/../soc_ru_voices" }) do
		local f = io.open(r .. "/gamedata/sounds/" .. string.gsub(name, "\\", "/"), "rb")
		if f then f:close() return true end
	end
	return false end } end
E.game = { translate_string = function(s) return "Windowed" end }

local f = io.open(path, "r")
local src = f:read("*a")
f:close()
local env = setmetatable({}, { __index = E })
local fn = assert(loadstring(src, "coop_soc_yan"))
setfenv(fn, env)
fn()
E.coop_soc_yan = env
return E
'''

F_OFFERED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO"
F_PREP = "YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO"
F_REPORTED = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_MEASUREMENTS_STOP_DIALOG_INFO"
F_HELMET = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_GIVE_PSI_PROTECTION_HELMET_STOP_DIALOG_INFO"
F_DONE = "YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_INSTALLATION_IS_DISABLED_STOP_DIALOG_INFO"
MEAS = ["YAN_START_TAKE_MEASUREMENTS_%d_QUEST_TASK_INFO" % i for i in (1, 2, 3)]
SW = ["X16_LAB_PRIMARY_SWITCHER_%d_DEACTIVATE_INFO" % i for i in (1, 2, 3, 4)]
SITES = [(108.5, -8.9, -209.3), (144.2, -8.9, -121.8), (177.9, -4.6, -99.5)]
YAN, X16, CORDON = "coop_l08_yantar", "coop_l08_x16", "coop_l01_escape"


def main():
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    E = lua.execute(PRELUDE, os.path.join(PATCH, "gamedata", "scripts", "coop_soc_yan.script"), PATCH.replace("\\", "/"))
    Y = E["coop_soc_yan"]

    def flag(n):
        return E["story_flags"]["has_flag"](n)

    def give(n):
        E["story_flags"]["give_flag"](n)

    def reset(level=YAN):
        E["__reset_flags"]()
        E["db"]["mp_actors"] = lua.table_from({})
        E["__given"] = lua.table_from({})
        E["__created"] = lua.table_from({})
        E["__story"] = lua.table_from({})
        E["__fail_create"] = False
        E["__level"] = level
        E["__time"] = 0
        E["__guide_pos"] = None
        E["__guide_online"] = False
        Y["reset_given"]()

    def player(pid, x=0.0, y=0.0, z=0.0):
        return E["__player"](pid, "p%d" % pid, x, y, z)

    def move(p, x, y, z):
        p["__pos"] = E["vector"]()
        p["__pos"]["x"], p["__pos"]["y"], p["__pos"]["z"] = x, y, z

    def step(dt=1000):
        E["__time"] = E["__time"] + dt
        return Y["step"](E["__time"])

    def given(task, pid):
        v = E["__given"][task + "|" + str(pid)]
        return int(v) if v else 0

    def all_tasks():
        return sorted(k for k in E["__given"].keys())

    def created():
        return sorted(str(v) for v in E["__created"].values())

    def n_created(prefix):
        return sum(1 for c in created() if c.startswith(prefix))

    # ---------------------------------------------------------------- the chain
    reset()
    p1, p2 = player(1, 0, 0, -270), player(2, 3, 0, -270)
    step()
    check("on Yantar: 'Help for the scientists' to BOTH players", given("yan_soc_job_task", 1) == 1 and given("yan_soc_job_task", 2) == 1, all_tasks())
    check("on Yantar: the ARRIVED flag of the Rostok tasks is set", flag("ROS_START_GO_TO_YANTAR_QUEST_TASK_INFO"))
    check("nothing else yet", all_tasks() == ["yan_soc_job_task|1", "yan_soc_job_task|2"], all_tasks())
    step(); step()
    check("tasks are given once per player", given("yan_soc_job_task", 1) == 1 and len(all_tasks()) == 2, all_tasks())
    check("the old carrier / per-step tasks are never given", given("yan_start_go_to_yantar_quest_task", 1) == 0 and given("yan_start_take_measurements_1_quest_task", 1) == 0)

    # Sakharov: offer (dialog sets the flag)
    check("Sakharov: the offer is the first state", Y["sak_state"]() == "offer")
    give(F_OFFERED)
    step()
    check("help offered: ONE measurement task to both", given("yan_start_talk_to_the_kruglov_quest_task", 1) == 1 and given("yan_start_talk_to_the_kruglov_quest_task", 2) == 1)
    check("Sakharov waits", Y["sak_state"]() == "wait")
    check("Kruglov: talk state", Y["kru_state"]() == "talk")
    give(F_PREP)
    check("Kruglov: busy after the agreement", Y["kru_state"]() == "busy")
    step()
    check("no device in the party: the server gives one to the first living player", n_created("yan_psi_detector|") == 1, created())
    step(5000)
    check("... but only one (the item is in his inventory now)", n_created("yan_psi_detector|") == 1, created())
    carrier = p1

    # measurements: a player with the device in the sphere for 10 s, any order, resets when he leaves
    move(p2, *SITES[0])
    step(); step(3000)
    check("a player without the device in a site measures nothing", not flag(MEAS[0]))
    move(carrier, SITES[1][0] + 2, SITES[1][1], SITES[1][2])
    step(1000); step(5000)
    check("5 s in site 2: not done", not flag(MEAS[1]))
    move(carrier, 0, 0, -270)
    step(1000)
    move(carrier, *SITES[1])
    step(1000); step(8000)
    check("left and came back: the 10 s start again", not flag(MEAS[1]))
    step(3000)
    check("site 2 measured after 10 s", flag(MEAS[1]) and flag("YAN_START_WAIT_FOR_THE_MEASUREMENTS_TO_FINISH_2_QUEST_TASK_INFO"))
    check("sites 1 and 3 untouched", not flag(MEAS[0]) and not flag(MEAS[2]))
    move(carrier, *SITES[2])
    step(1000); step(11000)
    move(carrier, *SITES[0])
    step(1000); step(11000)
    check("all three measured (any order)", all(flag(m) for m in MEAS))
    check("Sakharov: results state", Y["sak_state"]() == "results")
    check("the measurement task is still open until Sakharov (no new task yet)", given("yan_start_infiltrate_the_x16_lab_quest_task", 1) == 0)

    # the dialog: phrase 31 sets REPORTED + HELMET + REWARD together
    give(F_REPORTED)
    give(F_HELMET)
    give("YAN_SOC_REWARD_GIVEN")
    step()
    check("results delivered: an artifact for EVERY player", n_created("af_cristall_flower|") == 2, created())
    step(1000)
    check("... once", n_created("af_cristall_flower|") == 2, created())
    check("the helmet for every player (no helmet in anybody's bag)", n_created("dev_psi_protection_helmet|1") == 1 and n_created("dev_psi_protection_helmet|2") == 1, created())
    step(30000)
    check("... not again while they have it", n_created("dev_psi_protection_helmet|") == 2, created())
    p3 = player(3, 0, 0, -270)
    step()
    check("a late joiner gets a helmet too", n_created("dev_psi_protection_helmet|3") == 1, created())
    check("late joiner gets the open task (lab job) and not the finished measurement task", given("yan_start_infiltrate_the_x16_lab_quest_task", 3) == 1
          and given("yan_start_talk_to_the_kruglov_quest_task", 3) == 0 and given("yan_soc_job_task", 3) == 0)
    check("the lab job: Vasiliev's corpse and PDA are made once", n_created("yan_vasilyev|world") == 1 and n_created("yan_vasilyev_pda|world") == 1, created())
    step(1000); step(1000)
    check("... never twice", n_created("yan_vasilyev|world") == 1, created())
    check("to every player once", all(given("yan_start_infiltrate_the_x16_lab_quest_task", i) == 1 for i in (1, 2, 3)))
    check("Sakharov: lab state", Y["sak_state"]() == "lab")

    # Vasiliev's PDA
    check("PDA not yet read", not flag("YAN_SOC_VASILYEV_FOUND"))
    p2["__items"]["yan_vasilyev_pda"] = True
    step()
    check("a player holds the PDA: VASILYEV_FOUND and the tip flag", flag("YAN_SOC_VASILYEV_FOUND") and flag("YAN_SOC_VAS_PDA"))

    # the lab level
    E["__level"] = X16
    Y["reset_given"]()
    E["__given"] = lua.table_from({})
    step()
    check("lab level: LAB flag", flag("YAN_YAN_START_INFILTRATE_THE_X16_LAB_QUEST_TASK_INFO"))
    check("lab: Ghost's documents task and the switches task to all three", all(given("yan_soc_ghost_task", i) == 1 and given("x16_start_find_the_installation_quest_task", i) == 1 for i in (1, 2, 3)), all_tasks())
    check("lab: the Yantar-only tasks are not given here", given("yan_soc_job_task", 1) == 0 and given("yan_start_infiltrate_the_x16_lab_quest_task", 1) == 0)
    check("the exit task waits for the levers", given("x16_start_get_out_of_the_lab_task", 1) == 0)
    check("the helmet is kept for everybody in the lab", n_created("dev_psi_protection_helmet|") == 3, created())

    # documents
    check("documents not taken", not flag("X16_GHOST_DOCS_TAKEN"))
    p3["__items"]["lab_x16_documents"] = True
    step()
    check("a player holds Ghost's documents: X16_GHOST_DOCS_TAKEN and YAN_X16_DOCUMENTS_GAIN (the Barkeep task)", flag("X16_GHOST_DOCS_TAKEN") and flag("YAN_X16_DOCUMENTS_GAIN"))
    check("'Meet the Guide' to every player", all(given("yan_soc_guide_task", i) == 1 for i in (1, 2, 3)))

    # levers
    give(SW[0]); give(SW[1])
    step()
    check("a lever pressed: INSTALL flag (the task text goes to the modules)", flag("X16_START_FIND_THE_INSTALLATION_QUEST_TASK_INFO"))
    check("two levers: no exit task yet", given("x16_start_get_out_of_the_lab_task", 1) == 0)
    give(SW[2]); give(SW[3])
    step()
    check("all four levers: 'Get out of the lab' to every player", all(given("x16_start_get_out_of_the_lab_task", i) == 1 for i in (1, 2, 3)), all_tasks())

    # back on Yantar: tunnel exit (restrictor flag), Sakharov
    E["__level"] = YAN
    Y["reset_given"]()
    E["__given"] = lua.table_from({})
    give("X16_START_GET_OUT_OF_THE_LAB_TASK_INFO")
    step()
    check("Sakharov: thanks state", Y["sak_state"]() == "exit")
    check("the exit task is re-offered after the level change (the engine ignores a task a player has)", given("x16_start_get_out_of_the_lab_task", 1) == 1)
    give(F_DONE)
    step()
    check("Sakharov: the mod's greeting afterwards", Y["sak_state"]() == "done")
    reset()
    player(1)
    give(F_DONE)
    step()
    check("after the job: no lab / Yantar task is offered", [t for t in all_tasks() if not t.startswith("yan_soc_guide")] == [], all_tasks())

    # ---------------------------------------------------------------- no soft-lock
    # lab first (a debug jump or a save): every earlier flag is set, no rewards are made up
    reset(X16)
    player(1)
    step()
    check("lab entered without the Sakharov talks: earlier flags set", all(flag(f) for f in (F_OFFERED, F_PREP, F_REPORTED, F_HELMET, "YAN_SOC_VASILYEV_FOUND")))
    check("... no artifact / suit reward is made up", n_created("af_cristall_flower|") == 0 and n_created("ecolog_outfit|") == 0, created())
    check("... the helmet is handed out (nobody can be locked out of the lab)", n_created("dev_psi_protection_helmet|") == 1, created())

    # Vasiliev cannot be created
    reset()
    player(1)
    give(F_HELMET)
    E["__fail_create"] = True
    step(); step(); step(); step()
    check("Vasiliev cannot be created 3 times: the step is skipped (VASILYEV_FOUND)", flag("YAN_SOC_VASILYEV_FOUND"))
    check("... and the lab task is offered", given("yan_start_infiltrate_the_x16_lab_quest_task", 1) == 1)

    # the online object of the corpse comes up alive: it is killed once (like the Ghost's body of patch yantar_restore)
    reset()
    player(1)
    give(F_HELMET)
    step()
    vid = int(E["__story"]["yan_vasilyev"])
    E["__vas_online"] = lua.eval("function(id) local o = { id = id, __alive = true, __kills = 0 } function o:alive() return self.__alive end "
                                 "function o:kill(w) self.__alive = false self.__kills = self.__kills + 1 end return o end")(vid)
    step(); step()
    check("Vasiliev online and alive: killed exactly once", E["__vas_online"]["__alive"] is False and int(E["__vas_online"]["__kills"]) == 1)
    E["__vas_online"] = None

    # Vasiliev already exists (a save): not created again
    reset()
    player(1)
    E["__story"]["yan_vasilyev"] = 321
    give(F_HELMET)
    step()
    check("Vasiliev exists (story object): nothing is created", n_created("yan_vasilyev") == 0, created())

    # all levers without the documents (corpse lost)
    reset(X16)
    player(1)
    for s in SW:
        give(s)
    step()
    check("all levers: the documents step is closed (no soft-lock)", flag("X16_GHOST_DOCS_TAKEN") and given("yan_soc_ghost_task", 1) == 0)

    # left the lab by the entrance instead of the tunnel
    reset(YAN)
    player(1)
    for s in SW:
        give(s)
    step()
    check("all levers and back on Yantar: the exit flag is set (no tunnel needed)", flag("X16_START_GET_OUT_OF_THE_LAB_TASK_INFO"))

    # the Barkeep took the documents: everything before is closed
    reset(YAN)
    player(1)
    give("BAR_X16_DOCUMENTS_DONE")
    step()
    check("documents at the Barkeep: Sakharov is done, no Yantar task is offered", flag(F_DONE) and all(not t.startswith(("yan_soc_job", "yan_start", "x16_start")) for t in all_tasks()), all_tasks())

    # the Guide on Cordon
    reset(CORDON)
    player(1, 0, 0, 0)
    give("X16_GHOST_DOCS_TAKEN")
    E["__story"]["esc_smart_terrain_1_stalker_guide"] = 500
    gp = E["vector"]()
    gp["x"], gp["y"], gp["z"] = 100.0, 0.0, 100.0
    E["__guide_pos"] = gp
    step()
    check("Guide far away: not met", not flag("YAN_SOC_GUIDE_MET"))
    check("... the task is given on any level", given("yan_soc_guide_task", 1) == 1)
    move(E["db"]["mp_actors"][1], 102.0, 0.0, 100.0)
    step()
    check("a player next to the Guide (offline entity position): GUIDE_MET", flag("YAN_SOC_GUIDE_MET"))
    reset(CORDON)
    player(1, 0, 0, 0)
    give("X16_GHOST_DOCS_TAKEN")
    step(); step(31000)
    check("no Guide object known: met after 30 s on Cordon", flag("YAN_SOC_GUIDE_MET"))
    reset(CORDON)
    player(1, 0, 0, 0)
    give("X16_GHOST_DOCS_TAKEN")
    E["__story"]["esc_smart_terrain_1_stalker_guide"] = 500
    gp = E["vector"]()
    gp["x"], gp["y"], gp["z"] = 3.0, 0.0, 0.0
    E["__guide_pos"] = gp
    E["__guide_online"] = True
    step()
    check("online Guide object: met", flag("YAN_SOC_GUIDE_MET"))

    # suit (Sakharov branch 10)
    reset()
    player(1); player(2)
    give("YAN_SOC_OUTFIT_GIVEN")
    step(); step()
    check("the suit flag: one suit per player, once", n_created("ecolog_outfit|") == 2, created())

    # dead / respawned players
    reset()
    a, b = player(1), player(2)
    b["__alive"] = False
    step()
    check("a dead player is skipped", given("yan_soc_job_task", 1) == 1 and given("yan_soc_job_task", 2) == 0)
    b["__alive"] = True
    step()
    check("... and gets the task after the respawn", given("yan_soc_job_task", 2) == 1)

    # the level tick registered itself
    Y["install"]()
    check("install registers one level call", len(list(E["__calls"].values())) >= 1)

    # ---------------------------------------------------------------- dialog states: exactly one precondition is true
    sak = ["st_s_done", "st_s_exit", "st_s_lab", "st_s_results", "st_s_wait", "st_s_offer_r", "st_s_offer"]
    kru = ["st_k_after", "st_k_busy", "st_k_talk", "st_k_meet_r", "st_k_meet"]
    seq = [[], ["ROS_SMART_TERRAIN_3_KRUGLOV_HELP_SPACE_RESTRICTOR_INFO"], [F_OFFERED], [F_OFFERED, F_PREP], [F_OFFERED, F_PREP] + MEAS,
           [F_OFFERED, F_PREP, F_REPORTED, F_HELMET] + MEAS, [F_HELMET, "X16_START_GET_OUT_OF_THE_LAB_TASK_INFO"], [F_DONE]]
    exp_s = ["offer", "offer_r", "wait", "wait", "results", "lab", "exit", "done"]
    exp_k = ["meet", "meet_r", "talk", "busy", "busy", "after", "after", "after"]
    for fl, es, ek in zip(seq, exp_s, exp_k):
        reset()
        for f in fl:
            give(f)
        step()                                                   # the tick makes the chain monotonic (a later flag also sets the earlier ones)
        n_s = sum(1 for s in sak if Y[s](None, None))
        n_k = sum(1 for s in kru if Y[s](None, None))
        check("Sakharov state with %s -> %s (exactly one true)" % (",".join(x[:12] for x in fl) or "nothing", es), Y["sak_state"]() == es and n_s == 1, (Y["sak_state"](), n_s))
        check("Kruglov state -> %s (exactly one true)" % ek, Y["kru_state"]() == ek and n_k == 1, (Y["kru_state"](), n_k))

    # ---------------------------------------------------------------- voice: English recordings only, per-player language
    vs, vk = list(Y["VOICE_S"].values()), list(Y["VOICE_K"].values())
    check("8 Sakharov phrases and 2 Kruglov phrases have a recording", len(vs) == 8 and len(vk) == 2, (vs, vk))
    for lang in ("eng", "rus"):
        E["__voice_lang"] = lang
        for kind, ids, base in (("s", vs, "yantar_general_ucheniy_talk_start_"), ("k", vk, "yantar_help_scientist_")):
            for i in ids:
                p = Y["voice_path"](kind, i)
                if lang == "eng":
                    ok = p is not None and os.path.isfile(os.path.join(PATCH, "gamedata", "sounds", p.replace("\\", os.sep) + ".ogg")) and p.endswith(base + i)
                    check("voice %s%s eng: file exists" % (kind, i), ok, p)
                else:
                    ok = p is not None and p.endswith(base + i) and "\\eng\\" not in p and os.path.isfile(os.path.join(os.path.dirname(PATCH), "soc_ru_voices", "gamedata", "sounds", p.replace("\\", os.sep) + ".ogg"))
                    check("voice %s%s rus: Russian file ships in soc_ru_voices" % (kind, i), ok, p)
    E["__voice_lang"] = "eng"
    check("a line without a recording is silent", Y["voice_path"]("s", "2111") is None)
    me = E["__player"](9, "talker", 0.0, 0.0, 0.0)
    npc = E["__player"](10, "sakharov", 0.0, 0.0, 0.0)
    E["__client"] = True
    E["__me"] = me
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    Y["say_s31"](npc, me)
    played = list(E["__played"].values())
    check("say_s31 on the talker's machine plays the English recording", played == ["characters_voice\\dialogs\\eng\\yantar_general_ucheniy_talk_start_31"], played)
    other = E["__player"](11, "other", 0.0, 0.0, 0.0)
    E["__me"] = other
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    Y["say_s31"](npc, me)
    check("say_s31 on another player's machine is silent", len(list(E["__played"].values())) == 0)
    E["__me"] = me
    E["__voice_lang"] = "rus"
    E["__played"] = lua.table_from({})
    E["__time"] = E["__time"] + 5000
    Y["say_s31"](npc, me)
    played = list(E["__played"].values())
    check("say_s31 with voice_language rus plays the Russian recording", played == ["characters_voice\\dialogs\\yantar_general_ucheniy_talk_start_31"], played)
    E["__client"] = False
    log = [str(x) for x in E["__log"].values()]
    check("the PDA archive line is emitted (Sakharov)", any(x == "EMIT coop_soc_yan_s_31" for x in log))
    check("the archive knows the speaker: NPC line", E["coop_pda_phrases"]["phrase_speaker"]["coop_soc_yan_s_31"] == "npc")
    check("the archive knows the speaker: player line", (Y["say_s311"](npc, me) or True) and E["coop_pda_phrases"]["phrase_speaker"]["coop_soc_yan_s_311"] == "actor")

    print("\n%d FAIL" % fails if fails else "\nALL PASS")
    sys.exit(1 if fails else 0)


main()
