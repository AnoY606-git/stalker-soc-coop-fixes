"""Offline check of the fetch jobs' dialog logic (no game, a second):  python rq_dialogs_mock_test.py   (needs `pip install lupa`)
Runs the REAL gamedata/scripts/coop_rq_dialogs.script in a Lua 5.1 VM with a mock engine (story flags, an actor with an inventory, the dialogs.relocate_*
helpers) and compares it with an independent Python model of the SoC task_manager rules, for the jobs read from the shipped coop_repeat_quests.ltx:
  * offer_<job> (the precondition of the offer phrase): per giver and kind only the available order with the lowest priority, none while an order of the
    kind runs, gate flags, cooldown (accept + done / fail flags). Hand-made scenarios plus 3000 random flag states.
  * fetch_open_<giver> / has_<job>: the hand-in dialog only with a running job AND the item (either twin section).
  * pay_<job>: ONE piece is taken (twins one after the other), money and every reward item arrive at the talking player, nothing else changes;
    with the flag RQ_NO_ITEM_REWARDS the money still arrives and the items do not; zero money is not paid at all."""
import os
import random
import re
import sys

import lupa.lua51 as lupa51

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.abspath(os.path.join(HERE, ".."))
G = os.path.join(PATCH, "gamedata")

LUA = r'''
local script_path = ...
local E = {}
for _, k in ipairs({ "string", "table", "math", "pcall", "ipairs", "pairs", "tonumber", "tostring", "type", "next", "select", "unpack", "error", "assert", "setmetatable" }) do E[k] = _G[k] end
E._G = E
local flags = {}
E.story_flags = {
	has_flag = function(f) return flags[f] == true end,
	give_flag = function(f) flags[f] = true end,
	disable_flag = function(f) flags[f] = nil end,
}
local actor = { is_actor = true, id_ = 1, inv = {}, money = 0 }
local npc = { is_actor = false, id_ = 2, inv = {} }
local function wrap(o)
	o.id = function(self) return self.id_ end
	o.iterate_inventory = function(self, fn, arg) for _, s in ipairs(self.inv) do fn(arg, { section = function() return s end }) end end
	o.object = function(self, sec) for _, s in ipairs(self.inv) do if s == sec then return s end end return nil end
	return o
end
wrap(actor); wrap(npc)
E.db = { mp_actors = { [1] = actor } }
E.LocalActor = function() return 1 end
local function who(first, second)
	if first.is_actor then return second, first end
	return first, second
end
local function take(first, second, sec)
	local _, a = who(first, second)
	for i, s in ipairs(a.inv) do if s == sec then table.remove(a.inv, i) return end end
	error("actor has no " .. sec)
end
E.dialogs = {
	who_is_npc = who,
	relocate_item_section_from_actor = function(first, second, sec) take(first, second, sec) end,
	relocate_money_to_actor = function(first, second, n) local _, a = who(first, second) a.money = a.money + n end,
	relocate_item_section_to_actor = function(first, second, sec, n) local _, a = who(first, second) for _ = 1, (n or 1) do table.insert(a.inv, sec) end end,
}
local chunk = assert(loadfile(script_path))
setfenv(chunk, E)
chunk()
local T = {}
T.flags = flags
T.actor = actor
T.npc = npc
T.reset = function() for k in pairs(flags) do flags[k] = nil end actor.inv = {} actor.money = 0 end
T.call = function(name, ...) local f = E[name] if f == nil then error("no function " .. name) end return f(...) end
T.has_fn = function(name) return E[name] ~= nil end
T.set_inv = function(list) actor.inv = {} for _, s in ipairs(list) do table.insert(actor.inv, s) end end
T.inv = function() local r = {} for _, s in ipairs(actor.inv) do table.insert(r, s) end return r end
return T
'''


def parse_jobs():
    t = open(os.path.join(G, "configs", "misc", "coop_repeat_quests.ltx"), "rb").read().decode("cp1251").replace("\r\n", "\n")
    jobs = {}
    for m in re.finditer(r"^\[(rq_\w+)\]\n(.*?)(?=\n\[|\Z)", t, re.M | re.S):
        d = {}
        for ln in m.group(2).split("\n"):
            if "=" in ln and not ln.lstrip().startswith(";"):
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip()
        if d.get("kind") == "gen_fetch":
            giver = m.group(1).split("_")[1]
            jobs[m.group(1)] = dict(
                id=m.group(1), giver=giver, kind="art" if "_art" in m.group(1) else "part", prior=int(d["prior"]),
                gate=[] if d["gate"] == "none" else d["gate"].split(","), secs=d["item"].split(","), money=int(d["pay_money"]),
                items=[] if d["pay_items"] == "none" else d["pay_items"].split(","))
    return jobs


def fl(job, suf):
    return "RQG_%s_%s" % (job["id"].upper(), suf)


def model_offers(jobs, flags):
    """independent model of the SoC rule: per giver and kind the available (gate ok, not accepted) order with the lowest priority; nothing while one runs"""
    def st(j):
        if not flags.get(fl(j, "ACC")):
            return "free"
        return "wait" if flags.get(fl(j, "DONE")) or flags.get(fl(j, "FAIL")) else "active"
    out = set()
    for g in set(j["giver"] for j in jobs.values()):
        for k in ("art", "part"):
            grp = [j for j in jobs.values() if j["giver"] == g and j["kind"] == k]
            if any(st(j) == "active" for j in grp):
                continue
            avail = [j for j in grp if st(j) == "free" and all(flags.get(x) for x in j["gate"])]
            if avail:
                out.add(min(avail, key=lambda j: j["prior"])["id"])
    return out


def main():
    jobs = parse_jobs()
    lua = lupa51.LuaRuntime(unpack_returned_tuples=True)
    T = lua.execute(LUA, os.path.join(G, "scripts", "coop_rq_dialogs.script"))
    fails = []
    n = [0]

    def check(name, ok, info=""):
        n[0] += 1
        if not ok:
            fails.append("%s %s" % (name, info))
            print("FAIL", name, info)

    check("jobs found", len(jobs) >= 20, str(len(jobs)))
    allflags = set()
    for j in jobs.values():
        allflags.update(j["gate"])
        allflags.update(fl(j, s) for s in ("ACC", "DONE", "FAIL"))
    for j in jobs.values():
        for fn in ("offer_", "has_", "pay_"):
            check("function " + fn + j["id"], bool(T.has_fn(fn + j["id"])))
    for g in set(j["giver"] for j in jobs.values()):
        check("function fetch_open_" + g, bool(T.has_fn("fetch_open_" + g)))

    def set_flags(d):
        T.reset()
        for k, v in d.items():
            if v:
                T.flags[k] = True

    def lua_offers(d):
        set_flags(d)
        return set(i for i, j in jobs.items() if T.call("offer_" + i, T.actor, T.npc))

    # hand-made scenarios
    def sc(name, d, expect):
        got = lua_offers(d)
        check("scenario " + name, got == expect, "got %s want %s" % (sorted(got), sorted(expect)))
        check("model agrees " + name, model_offers(jobs, d) == expect, str(sorted(model_offers(jobs, d))))

    sc("fresh: lowest priority of each kind", {}, {"rq_sid_art1", "rq_sid_part2", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("sid art1 running: no other Sidorovich artifact, parts stay",
       {"RQG_RQ_SID_ART1_ACC": 1}, {"rq_sid_part2", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("sid art1 on cooldown: art2 next",
       {"RQG_RQ_SID_ART1_ACC": 1, "RQG_RQ_SID_ART1_DONE": 1}, {"rq_sid_art2", "rq_sid_part2", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("sid art1, art2 on cooldown: art4 next (no art3 order)",
       {"RQG_RQ_SID_ART1_ACC": 1, "RQG_RQ_SID_ART1_FAIL": 1, "RQG_RQ_SID_ART2_ACC": 1, "RQG_RQ_SID_ART2_DONE": 1},
       {"rq_sid_art4", "rq_sid_part2", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("sid part2 on cooldown: the gated bloodsucker part needs the military case",
       {"RQG_RQ_SID_PART2_ACC": 1, "RQG_RQ_SID_PART2_DONE": 1}, {"rq_sid_art1", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("sid part2 on cooldown + case: bloodsucker part",
       {"RQG_RQ_SID_PART2_ACC": 1, "RQG_RQ_SID_PART2_DONE": 1, "AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO": 1},
       {"rq_sid_art1", "rq_sid_part1", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("barman art1 on cooldown, X18 documents not handed in: art3 (priority 4) is next",
       {"RQG_RQ_BAR_ART1_ACC": 1, "RQG_RQ_BAR_ART1_DONE": 1}, {"rq_bar_art3", "rq_sid_art1", "rq_sid_part2", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("barman art1 on cooldown + documents: Flash (priority 2)",
       {"RQG_RQ_BAR_ART1_ACC": 1, "RQG_RQ_BAR_ART1_DONE": 1, "BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO": 1},
       {"rq_bar_art4", "rq_sid_art1", "rq_sid_part2", "rq_bar_part1", "rq_sak_art2", "rq_sak_part1", "rq_fre_part1"})
    sc("sakharov: all five parts finished once -> none offered, artifacts unaffected",
       {"RQG_RQ_SAK_PART%d_%s" % (i, s): 1 for i in range(1, 6) for s in ("ACC", "DONE")},
       {"rq_sid_art1", "rq_sid_part2", "rq_bar_art1", "rq_bar_part1", "rq_sak_art2", "rq_fre_part1"})

    # random flag states against the model
    rnd = random.Random(20261021)
    flist = sorted(allflags)
    bad = 0
    for i in range(3000):
        d = {f: (rnd.random() < 0.25) for f in flist}
        got = lua_offers(d)
        want = model_offers(jobs, d)
        if got != want:
            bad += 1
            if bad <= 3:
                print("FAIL random state", i, "got", sorted(got), "want", sorted(want))
    check("3000 random flag states agree with the model", bad == 0, "%d differ" % bad)

    # hand-in
    for jid, j in sorted(jobs.items()):
        g = j["giver"]
        for tag, flags in (("no job", {}), ("job running", {fl(j, "ACC"): 1}), ("job done", {fl(j, "ACC"): 1, fl(j, "DONE"): 1}), ("job failed", {fl(j, "ACC"): 1, fl(j, "FAIL"): 1})):
            for item in (None, j["secs"][0], j["secs"][-1]):
                set_flags(flags)
                T.set_inv(lua.table_from([item] if item else []))
                shown = bool(T.call("fetch_open_" + g, T.actor, T.npc))
                has = bool(T.call("has_" + jid, T.actor, T.npc))
                want_open = tag == "job running" and item is not None
                # another running job of the same giver with the same item would also open the dialog; none is set here
                check("hand-in %s %s item=%s: open" % (jid, tag, item), shown == want_open, "shown %s" % shown)
                check("hand-in %s %s item=%s: has" % (jid, tag, item), has == (item is not None), "has %s" % has)
        # wrong item
        set_flags({fl(j, "ACC"): 1})
        T.set_inv(lua.table_from(["wpn_pm"]))
        check("hand-in %s: unrelated item does not open it" % jid, not bool(T.call("fetch_open_" + g, T.actor, T.npc)))
        # pay: one piece, money, items
        for no_items in (False, True):
            set_flags({fl(j, "ACC"): 1, "RQ_NO_ITEM_REWARDS": 1 if no_items else 0})
            twin = j["secs"][-1]
            T.set_inv(lua.table_from(list(j["secs"]) + ["wpn_pm"]))   # one of each twin + something else
            before = list(T.inv().values())
            T.call("pay_" + jid, T.actor, T.npc)
            after = list(T.inv().values())
            want_after = list(before)
            want_after.remove(j["secs"][0])
            if not no_items:
                want_after += j["items"]
            check("pay %s%s: one piece taken, rewards added, nothing else changes" % (jid, " (item rewards off)" if no_items else ""),
                  sorted(after) == sorted(want_after), "after %s want %s" % (sorted(after), sorted(want_after)))
            check("pay %s%s: money" % (jid, " (item rewards off)" if no_items else ""), int(T.actor.money) == j["money"], str(T.actor.money))
        # without the item nothing is paid
        set_flags({fl(j, "ACC"): 1})
        T.set_inv(lua.table_from(["wpn_pm"]))
        T.call("pay_" + jid, T.actor, T.npc)
        check("pay %s without the item pays nothing" % jid, int(T.actor.money) == 0 and list(T.inv().values()) == ["wpn_pm"], "%s %s" % (T.actor.money, list(T.inv().values())))

    print("%d checks, %d failed" % (n[0], len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
