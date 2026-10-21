"""Generates the fetch jobs (kind = gen_fetch: bring an artifact / a mutant part) of the repeatable_quests patch from one table.

  python -I gen_fetch.py [<repeatable_quests dir>] [--check-items <config dir> ...]

The table JOBS below is the whole SoC set of artifact and mutant part orders (Steam SoC misc\\task_manager.ltx: tm_find_artefact_*, tm_monster_part_*,
barmen_find_artefact_*, barmen_monster_part_*, ecolog_find_artefact_*, ecolog_monster_part_*, freedom_monster_part_1) with the SoC giver, item, pay and
priority. Texts (title, giver line, PDA description, accept / hand-in lines) are the original SoC texts of tools/fetch_texts.json (soc_fetch_texts.py).
Rewrites, in place and idempotently, only the fetch parts of:
  gamedata/configs/misc/coop_repeat_quests.ltx   [list] entries + job sections (after the "fetch jobs" comment)
  gamedata/configs/misc/tm_coop_repeat.ltx       task sections (from [rq_sid_art1] to the end)
  gamedata/configs/gameplay/dialogs_coop_repeat_quests.xml   offer / accept phrases of the giver dialogs, the fetch hand-in dialogs, the Freedom dialog
  gamedata/configs/text/{eng,rus}/st_coop_repeat_quests.xml  strings (from rq_handin_fetch to the end)
  gamedata/scripts/coop_rq_dialogs.script        FETCH table, offer / hand-in functions
--check-items DIR...  config folders (base game, mod, patches) in which every item section and reward must exist.

SoC rules reproduced: a giver offers per kind (artifact / part) only the AVAILABLE order with the lowest priority; while one order of a kind is running no other
of that kind is offered; a finished order is offered again after the cooldown (the repeat script clears its flags). Orders with a story condition
(condlist in task_manager.ltx) use the mod's equivalent story flag (GATE_*)."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# SoC story infos and the flag of this mod that stands for the same story step
GATE_CASE = "AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO"   # agroprom_military_case_have (the military case was taken)
GATE_DARK = "BAR_SMART_TERRAIN_1_STALKER_BARMEN_1_HAS_DOCUMENTS_DARKVALLEY_STOP_DIALOG_INFO"   # bar_darklab_document_done (X18 documents handed to the Barman)
GATE_X16 = "X16_START_GET_OUT_OF_THE_LAB_TASK_INFO"   # yan_kill_brain_done (left laboratory X16 after the installation)

# giver: SoC task_manager parent, level, dialog ids, icon, names (the hand-in line "Hand it in to ...")
GIVERS = {
    "sid": dict(parent="trader", level="coop_l01_escape", dialog="rq_sid_dialog", handin="rq_sid_handin", icon="ui_rq_job_trader",
                en="Sidorovich", ru="Сидоровичу"),
    "bar": dict(parent="barman", level="coop_l05_bar", dialog="rq_bar_dialog", handin="rq_bar_handin", icon="ui_rq_job_barman",
                en="the Barman", ru="Бармену"),
    "sak": dict(parent="ecolog", level="coop_l08_yantar", dialog="rq_sak_dialog", handin="rq_sak_fetch_handin", icon="ui_rq_job_scientist",
                en="Sakharov", ru="Сахарову"),
    "fre": dict(parent="freedom", level="coop_l07_military", dialog="rq_fre_dialog", handin="rq_fre_handin", icon="ui_rq_task_find",
                en="Lukash", ru="Лукашу"),
}

# mod item sections: an artifact exists as af_x and (since soc_economy) as its SoC twin af_x_soc; both count. Parts are the sections mutant_loot drops.
def art(name, twin=True):
    return ["af_" + name, "af_" + name + "_soc"] if twin else ["af_" + name + "_soc"]


D = "ammo_12x76_dart"
MS = "medkit_scientic"
# id, giver, soc task, kind, prior (lower first), gate flags, accepted sections, money, reward items
JOBS = [
    dict(id="rq_sid_art1", giver="sid", soc="tm_find_artefact_1", kind="art", prior=1, gate=[], secs=art("medusa"), money=1500, items=["vodka"]),
    dict(id="rq_sid_art2", giver="sid", soc="tm_find_artefact_2", kind="art", prior=2, gate=[], secs=art("cristall_flower"), money=3000, items=["vodka"]),
    dict(id="rq_sid_art4", giver="sid", soc="tm_find_artefact_4", kind="art", prior=3, gate=[], secs=art("mincer_meat"), money=2500, items=["medkit_army"] * 3),
    dict(id="rq_sid_part1", giver="sid", soc="tm_monster_part_1", kind="part", prior=2, gate=[GATE_CASE], secs=["mutant_krovosos_part"], money=3000, items=[D] * 5),
    dict(id="rq_sid_part2", giver="sid", soc="tm_monster_part_2", kind="part", prior=1, gate=[], secs=["mutant_psevdodog_part"], money=1500, items=[D] * 5),
    dict(id="rq_bar_art1", giver="bar", soc="barmen_find_artefact_1", kind="art", prior=1, gate=[], secs=art("mincer_meat"), money=2500, items=[MS] * 2),
    dict(id="rq_bar_art2", giver="bar", soc="barmen_find_artefact_2", kind="art", prior=3, gate=[GATE_DARK], secs=art("rusty_kristall", False), money=2500, items=[MS, MS, "antirad", "antirad"]),
    dict(id="rq_bar_art3", giver="bar", soc="barmen_find_artefact_3", kind="art", prior=4, gate=[], secs=art("night_star"), money=0, items=["specops_outfit"] + ["grenade_f1"] * 3),
    dict(id="rq_bar_art4", giver="bar", soc="barmen_find_artefact_4", kind="art", prior=2, gate=[GATE_DARK], secs=art("electra_flash"), money=5000, items=[]),
    dict(id="rq_bar_art5", giver="bar", soc="barmen_find_artefact_5", kind="art", prior=5, gate=[GATE_X16], secs=art("gold_fish"), money=0,
         items=["wpn_lr300", "wpn_addon_grenade_launcher_m203", "wpn_addon_scope_susat", "wpn_addon_silencer"]),
    dict(id="rq_bar_part1", giver="bar", soc="barmen_monster_part_1", kind="part", prior=1, gate=[], secs=["mutant_flesh_part"], money=500, items=["conserva"] * 3),
    dict(id="rq_bar_part2", giver="bar", soc="barmen_monster_part_2", kind="part", prior=2, gate=[], secs=["mutant_boar_part"], money=1500, items=[]),
    dict(id="rq_sak_art1", giver="sak", soc="ecolog_find_artefact_1", kind="art", prior=3, gate=[], secs=art("fireball"), money=0, items=["af_dummy_pellicle_soc"]),
    dict(id="rq_sak_art2", giver="sak", soc="ecolog_find_artefact_2", kind="art", prior=1, gate=[], secs=art("gravi"), money=5000, items=[MS]),
    dict(id="rq_sak_art3", giver="sak", soc="ecolog_find_artefact_3", kind="art", prior=2, gate=[], secs=art("medusa"), money=2500, items=[MS]),
    dict(id="rq_sak_art4", giver="sak", soc="ecolog_find_artefact_4", kind="art", prior=4, gate=[], secs=art("electra_moonlight"), money=10000, items=[MS] * 3),
    dict(id="rq_sak_art5", giver="sak", soc="ecolog_find_artefact_5", kind="art", prior=5, gate=[], secs=art("rusty_sea-urchin", False), money=0, items=["scientific_outfit"]),
    dict(id="rq_sak_part1", giver="sak", soc="ecolog_monster_part_1", kind="part", prior=1, gate=[], secs=["mutant_snork_part"], money=2500, items=[MS]),
    dict(id="rq_sak_part2", giver="sak", soc="ecolog_monster_part_2", kind="part", prior=2, gate=[], secs=["mutant_flesh_part"], money=1000, items=["wpn_addon_scope_susat"]),
    dict(id="rq_sak_part3", giver="sak", soc="ecolog_monster_part_3", kind="part", prior=3, gate=[], secs=["mutant_boar_part"], money=2000, items=[D] * 3),
    dict(id="rq_sak_part4", giver="sak", soc="ecolog_monster_part_4", kind="part", prior=4, gate=[], secs=["mutant_psevdodog_part"], money=3000, items=[MS]),
    dict(id="rq_sak_part5", giver="sak", soc="ecolog_monster_part_5", kind="part", prior=5, gate=[], secs=["mutant_krovosos_part"], money=6000, items=[MS]),
    dict(id="rq_fre_part1", giver="fre", soc="freedom_monster_part_1", kind="part", prior=1, gate=[], secs=["mutant_boar_part"], money=1000, items=["vodka"]),
]
# SoC orders NOT offered: tm_find_artefact_3 (Night Star for Sidorovich: needs the info esc_darklab_documents_read, which only a Sidorovich dialog for the X18 documents
# sets; this mod has no such dialog, and its only reward outfit_stalker_m2 exists neither in SoC nor here).

# reward item names: section -> (EN one, EN many "%d", RU one, RU 2-4, RU 5+)
ITEM_NAMES = {
    "vodka": ("a bottle of vodka", "%d bottles of vodka", "бутылка водки", "бутылки водки", "бутылок водки"),
    "conserva": ("a can of food", "%d cans of food", "банка тушёнки", "банки тушёнки", "банок тушёнки"),
    "medkit_scientic": ("a science medkit", "%d science medkits", "научная аптечка", "научные аптечки", "научных аптечек"),
    "medkit_army": ("an army medkit", "%d army medkits", "армейская аптечка", "армейские аптечки", "армейских аптечек"),
    "antirad": ("an Antirad", "%d Antirads", "антирад", "антирада", "антирадов"),
    D: ("a box of 12x76 Dart shells", "%d boxes of 12x76 Dart shells", "коробка патронов 12x76 «Дротик»", "коробки патронов 12x76 «Дротик»", "коробок патронов 12x76 «Дротик»"),
    "grenade_f1": ("an F-1 grenade", "%d F-1 grenades", "граната Ф-1", "гранаты Ф-1", "гранат Ф-1"),
    "specops_outfit": ("a Berill-5M armored suit", None, "бронекостюм «Берилл-5М»", None, None),
    "scientific_outfit": ("a SEVA bodysuit", None, "комбинезон «СЕВА»", None, None),
    "wpn_lr300": ("an LR-300", None, "LR-300", None, None),
    "wpn_addon_grenade_launcher_m203": ("an M203 grenade launcher", None, "подствольник M203", None, None),
    "wpn_addon_scope_susat": ("a SUSAT scope", None, "прицел SUSAT", None, None),
    "wpn_addon_silencer": ("a silencer", None, "глушитель", None, None),
    "af_dummy_pellicle_soc": ("a \"Pellicle\" artifact", None, "артефакт «Плёнка»", None, None),
}


def rw_text(job, lang):
    parts = []
    if job["money"] > 0:
        parts.append("%d RU" % job["money"])
    seen = []
    for s in job["items"]:
        if s not in seen:
            seen.append(s)
    for s in seen:
        n = job["items"].count(s)
        nm = ITEM_NAMES[s]
        if lang == "eng":
            parts.append(nm[0] if n == 1 else nm[1] % n)
        else:
            if n == 1:
                parts.append(nm[2])
            else:
                parts.append("%d %s" % (n, nm[3] if n < 5 else nm[4]))
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + (" and " if lang == "eng" else " и ") + parts[-1]


def norm(s, lang):
    for a, b in ((0x2014, " - "), (0x2013, "-"), (0xa0, " "), (0x2019, "'"), (0x2018, "'"), (0x201c, '"'), (0x201d, '"'), (0x2026, "...")):
        s = s.replace(chr(a), b)
    if lang == "rus":
        s = re.sub(r'"([^"]*)"', "«\\1»", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def up(job):
    return job["id"].upper()


def flag(job, suf):
    return "RQG_%s_%s" % (up(job), suf)


def by_giver(g):
    return [j for j in JOBS if j["giver"] == g]


# ---------------------------------------------------------------------------------------------------------------- io
def rd(path, enc="cp1251"):
    return open(path, "rb").read().decode(enc).replace("\r\n", "\n")


def wr(path, text, enc="cp1251"):
    open(path, "wb").write(text.replace("\n", "\r\n").encode(enc))


def one_sub(pat, repl, text, flags=0, count=1):
    new, n = re.subn(pat, lambda m: repl, text, count=count, flags=flags)
    if n == 0:
        raise SystemExit("pattern not found: " + pat)
    return new


# ---------------------------------------------------------------------------------------------------------------- ltx files
def gen_cfg(G):
    p = os.path.join(G, "configs", "misc", "coop_repeat_quests.ltx")
    t = rd(p)
    # list: drop the old fetch ids, append the new ones after the last list entry
    m = re.search(r"\[list\]\n(.*?)\n\n", t, re.S)
    lst = [l for l in m.group(1).split("\n") if l.strip() and not re.fullmatch(r"rq_(sid|bar|sak|fre)_(art|part)\d+", l.strip())]
    lst += [j["id"] for j in JOBS]
    t = t[:m.start(1)] + "\n".join(lst) + t[m.end(1):]
    i = t.index("; ---- fetch jobs")
    head = t[:i].rstrip("\n") + "\n\n"
    out = [
        "; ---- fetch jobs (bring an artifact / a mutant part): the whole SoC set of orders, generated by tools/gen_fetch.py (do not edit by hand).",
        "; kind = gen_fetch: nothing is spawned, no map spot; the hand-in dialog of the giver takes item + count from the player who talks and pays money and items",
        "; to that player (scripts/coop_rq_dialogs.script). soc = the SoC task_manager.ltx section, prior = SoC priority (lower first, one order per kind and giver is",
        "; offered), gate = story flags that must be set (SoC condlist). pay_* / item / prior / gate mirror the table in coop_rq_dialogs.script for tools/check_rq.py.",
        "; cooldown and timeout are the defaults.",
        "",
    ]
    for j in JOBS:
        g = GIVERS[j["giver"]]
        out += ["[%s]" % j["id"], "level = %s" % g["level"], "kind = gen_fetch", "soc = %s" % j["soc"],
                "accept = %s" % flag(j, "ACC"), "done = %s" % flag(j, "DONE"), "fail = %s" % flag(j, "FAIL"),
                "item = %s" % ",".join(j["secs"]), "count = 1", "prior = %d" % j["prior"], "gate = %s" % (",".join(j["gate"]) or "none"),
                "pay_money = %d" % j["money"], "pay_items = %s" % (",".join(j["items"]) or "none"), ""]
    wr(p, head + "\n".join(out))


def gen_tm(G):
    p = os.path.join(G, "configs", "misc", "tm_coop_repeat.ltx")
    t = rd(p)
    i = t.index("[rq_sid_art1]")
    out = []
    for j in JOBS:
        g = GIVERS[j["giver"]]
        out += ["[%s]" % j["id"], "icon = %s" % g["icon"], "prior = 100", "storyline = false", "title = %s_name" % j["id"], "descr = %s_descr" % j["id"],
                "target = nil", "condlist_0 = {+%s} complete" % flag(j, "DONE"), "condlist_1 = {+%s} fail" % flag(j, "FAIL"), ""]
    wr(p, t[:i] + "\n".join(out))


# ---------------------------------------------------------------------------------------------------------------- strings
def gen_text(G, T):
    for lang in ("eng", "rus"):
        p = os.path.join(G, "configs", "text", lang, "st_coop_repeat_quests.xml")
        t = rd(p)
        i = t.index('\t<string id="rq_handin_fetch">')
        S = T[lang]
        out = []

        def add(i_, text):
            out.append('\t<string id="%s">\n\t\t<text>%s</text>\n\t</string>' % (i_, norm(text, lang)))

        add("rq_handin_fetch", S["tm_reward_job"])
        for gk, g in GIVERS.items():
            add("rq_handin_%s_ask" % gk, S["tm_%s_job_ask" % g["parent"]])
        for j in JOBS:
            g = GIVERS[j["giver"]]
            title, said, descr = S[j["soc"]], S[j["soc"] + "_text"], S[j["soc"] + "_descr"]
            descr = descr.rstrip()
            if descr[-1] not in ".!?":
                descr += "."
            if lang == "eng":
                tail = " Hand it in to %s. Reward: %s." % (g["en"], rw_text(j, lang))
            else:
                tail = " Сдать %s. Награда: %s." % (g["ru"], rw_text(j, lang))
            add(j["id"] + "_name", title)
            add(j["id"] + "_descr", descr + tail)
            add(j["id"] + "_offer", title)
            add(j["id"] + "_npc", said)
            add(j["id"] + "_accept", S["tm_seek_job_yes"])
            add("rq_handin_" + j["id"], title)
            add(j["id"] + "_done", S["tm_%s_job_complete" % g["parent"]])
        wr(p, t[:i] + "\n".join(out) + "\n</string_table>\n")


# ---------------------------------------------------------------------------------------------------------------- dialogs
def offer_block(g):
    """offer / npc / accept phrases of the fetch jobs of giver g; returns (phrases text, offer ids)"""
    lines, ids = [], []
    for k, j in enumerate(by_giver(g)):
        o, n, a = 100 + k, 200 + k, 300 + k
        ids.append(o)
        acc = flag(j, "ACC")
        lines.append('      <phrase id="%d"><text>%s_offer</text><precondition>coop_rq_dialogs.offer_%s</precondition><dont_has_flag>%s</dont_has_flag><next>%d</next></phrase>'
                     % (o, j["id"], j["id"], acc, n))
        lines.append('      <phrase id="%d"><text>%s_npc</text><next>%d</next><next>99</next></phrase>' % (n, j["id"], a))
        lines.append('      <phrase id="%d"><text>%s_accept</text><dont_has_flag>%s</dont_has_flag><give_flag>%s</give_flag></phrase>' % (a, j["id"], acc, acc))
    return "\n".join(lines), ids


def handin_dialog(g):
    gv = GIVERS[g]
    js = by_giver(g)
    L = ['  <dialog id="%s">' % gv["handin"], "    <precondition>coop_rq_dialogs.fetch_open_%s</precondition>" % g, "    <phrase_list>",
         '      <phrase id="0"><text>rq_handin_fetch</text><next>1</next></phrase>',
         '      <phrase id="1"><text>rq_handin_%s_ask</text>%s<next>99</next></phrase>' % (g, "".join("<next>%d</next>" % (10 + k) for k in range(len(js))))]
    for k, j in enumerate(js):
        L.append('      <phrase id="%d"><text>rq_handin_%s</text><precondition>coop_rq_dialogs.has_%s</precondition><has_flag>%s</has_flag><dont_has_flag>%s</dont_has_flag>'
                 '<dont_has_flag>%s</dont_has_flag><action>coop_rq_dialogs.pay_%s</action><give_flag>%s</give_flag><next>%d</next></phrase>'
                 % (10 + k, j["id"], j["id"], flag(j, "ACC"), flag(j, "DONE"), flag(j, "FAIL"), j["id"], flag(j, "DONE"), 30 + k))
        L.append('      <phrase id="%d"><text>%s_done</text></phrase>' % (30 + k, j["id"]))
    L += ['      <phrase id="99"><text>rq_not_now</text><action>dialogs.break_dialog</action></phrase>', "    </phrase_list>", "  </dialog>"]
    return "\n".join(L)


def gen_dialogs(G):
    p = os.path.join(G, "configs", "gameplay", "dialogs_coop_repeat_quests.xml")
    t = rd(p)
    # 1. drop the old hand-in dialogs of the fetch jobs
    for d in ("rq_sid_handin", "rq_bar_handin", "rq_sak_fetch_handin", "rq_fre_handin", "rq_fre_dialog"):
        t = re.sub(r'  <dialog id="%s">.*?</dialog>\n' % d, "", t, flags=re.S)
    # 2. giver dialogs: remove the fetch phrases, add the new ones before the "not now" phrase
    for g in ("sid", "bar", "sak"):
        gv = GIVERS[g]
        m = re.search(r'(  <dialog id="%s">\n)(.*?)(  </dialog>\n)' % gv["dialog"], t, re.S)
        body = m.group(2)
        gone = set()
        keep = []
        for ln in body.split("\n"):
            mm = re.match(r'\s*<phrase id="(\d+)"><text>rq_%s_(art|part)\d+_(offer|npc|accept)</text>' % g, ln)
            if mm:
                if mm.group(3) == "offer":
                    gone.add(mm.group(1))
                continue
            keep.append(ln)
        body = "\n".join(keep)
        # the "what needs doing" phrase lists the offers
        def fix_next(mm):
            nexts = [x for x in re.findall(r"<next>(\d+)</next>", mm.group(2)) if x not in gone and x != "99"]
            return mm.group(1) + "".join("<next>%s</next>" % x for x in nexts) + "@@NEW@@<next>99</next></phrase>"
        body = re.sub(r'(<phrase id="1"><text>rq_npc_work</text>)((?:<next>\d+</next>)+)</phrase>', fix_next, body)
        block, ids = offer_block(g)
        body = body.replace("@@NEW@@", "".join("<next>%d</next>" % i for i in ids))
        body = body.replace('      <phrase id="99">', block + '\n      <phrase id="99">', 1)
        t = t[:m.start(2)] + body + t[m.end(2):]
    # 3. hand-in dialogs + the Freedom dialog at the end
    extra = [handin_dialog(g) for g in ("sid", "bar", "sak")]
    block, ids = offer_block("fre")
    extra.append('  <dialog id="rq_fre_dialog">\n    <phrase_list>\n      <phrase id="0"><text>rq_ask_work</text><next>1</next></phrase>\n'
                 '      <phrase id="1"><text>rq_npc_work</text>%s<next>99</next></phrase>\n%s\n'
                 '      <phrase id="99"><text>rq_not_now</text><action>dialogs.break_dialog</action></phrase>\n    </phrase_list>\n  </dialog>'
                 % ("".join("<next>%d</next>" % i for i in ids), block))
    extra.append(handin_dialog("fre"))
    t = t.replace("</game_dialogs>", "\n".join(extra) + "\n</game_dialogs>")
    wr(p, t)


# ---------------------------------------------------------------------------------------------------------------- lua
FETCH_OFFER = '''-- BEGIN fetch_offer (generated by tools/gen_fetch.py)
-- SoC task_manager rules: a giver offers per kind (art / part) only the available order with the lowest priority (prior); while an order of the kind runs
-- no other of that kind is offered; an order whose story condition (gate flags = SoC condlist) is not met, or that waits for its cooldown (accept flag
-- set, done / fail set: the repeat script clears them when it is due), is not available.
local function fetch_gate_ok(f)
	for _, g in ipairs(f.gate) do
		if not story_flags.has_flag(g) then return false end
	end
	return true
end

-- "free" = can be offered (not accepted), "active" = accepted and running, "wait" = finished, waiting for the cooldown
local function fetch_state(id)
	if not story_flags.has_flag(rq_flag(id, "ACC")) then return "free" end
	if story_flags.has_flag(rq_flag(id, "DONE")) or story_flags.has_flag(rq_flag(id, "FAIL")) then return "wait" end
	return "active"
end

function fetch_offer(id)
	local f = FETCH[id]
	if f == nil or not fetch_gate_ok(f) or fetch_state(id) ~= "free" then return false end
	for id2, f2 in pairs(FETCH) do
		if id2 ~= id and f2.giver == f.giver and f2.kind == f.kind then
			local st = fetch_state(id2)
			if st == "active" then return false end
			if st == "free" and f2.prior < f.prior and fetch_gate_ok(f2) then return false end
		end
	end
	return true
end
-- END fetch_offer
'''


def lua_table():
    L = ["-- fetch jobs (bring an artifact / a mutant part): the whole SoC set, generated by tools/gen_fetch.py (see NOTES.md). The talking player hands in and is paid.",
         "-- giver / kind / prior / gate = who offers it, art or part, SoC priority, story flags required. secs = accepted sections (an artifact exists as af_x and as its",
         "-- SoC twin af_x_soc), count = pieces, money / items = pay to that player.",
         "local FETCH = {"]

    def q(lst):
        return "{" + ", ".join('"%s"' % x for x in lst) + "}"
    for j in JOBS:
        L.append('\t%s = {giver = "%s", kind = "%s", prior = %d, gate = %s, secs = %s, count = 1, money = %d, items = %s},'
                 % (j["id"], j["giver"], j["kind"], j["prior"], q(j["gate"]), q(j["secs"]), j["money"], q(j["items"])))
    L.append("}")
    return "\n".join(L) + "\n"


def lua_funcs():
    L = []
    for g in GIVERS:
        L.append('function fetch_open_%s(first_speaker, second_speaker) return fetch_open("%s", first_speaker, second_speaker) end' % (g, g))
    L.append("")
    for j in JOBS:
        i = j["id"]
        L.append('function offer_%s(first_speaker, second_speaker) return fetch_offer("%s") end' % (i, i))
        L.append('function has_%s(first_speaker, second_speaker) return fetch_has("%s", first_speaker, second_speaker) end' % (i, i))
        L.append('function pay_%s(first_speaker, second_speaker) fetch_pay("%s", first_speaker, second_speaker) end' % (i, i))
    return "\n".join(L) + "\n"


def gen_lua(G):
    p = os.path.join(G, "scripts", "coop_rq_dialogs.script")
    t = rd(p)
    # table
    a = t.index("-- fetch jobs (bring an artifact / a mutant part)")
    b = t.index("\n}\n", a) + 3
    t = t[:a] + lua_table() + t[b:]
    # offer helper (needs rq_flag and FETCH: after the table's helpers, before the "old find jobs" block)
    t = re.sub(r"-- BEGIN fetch_offer.*?-- END fetch_offer\n\n?", "", t, flags=re.S)
    k = t.index('-- old "find" jobs')
    t = t[:k] + FETCH_OFFER + "\n" + t[k:]
    # wrappers
    t = "\n".join(l for l in t.split("\n") if not re.match(r"function (has|pay|offer)_rq_(sid|bar|sak|fre)_(art|part)\d+\(", l)
                  and not re.match(r"function fetch_open_\w+\(", l))
    t = re.sub(r"\n{3,}", "\n\n", t)
    k = t.index("function find_open_wolf")
    t = t[:k] + lua_funcs() + "\n" + t[k:]
    wr(p, t)


# ---------------------------------------------------------------------------------------------------------------- item check
def sections(dirs):
    names = set()
    for d in dirs:
        for dp, dn, fn in os.walk(d):
            if os.sep + "wip" in dp or os.sep + "tests" in dp:
                continue
            for f in fn:
                if f.endswith(".ltx"):
                    t = open(os.path.join(dp, f), "rb").read().decode("cp1251", "replace")
                    names.update(re.findall(r"^\[([\w\-]+)\]", t, re.M))
    return names


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = []
    if "--check-items" in sys.argv:
        i = sys.argv.index("--check-items") + 1
        while i < len(sys.argv) and not sys.argv[i].startswith("--"):
            check.append(sys.argv[i])
            i += 1
        args = [a for a in args if a not in check]
    patch = args[0] if args else os.path.dirname(HERE)
    G = os.path.join(patch, "gamedata")
    if check:
        have = sections(check)
        bad = 0
        for j in JOBS:
            for s in j["secs"] + j["items"]:
                if s not in have:
                    print("MISSING section %s (job %s)" % (s, j["id"]))
                    bad += 1
        print("item check: %d missing" % bad)
        if bad:
            sys.exit(1)
        return
    T = json.load(open(os.path.join(HERE, "fetch_texts.json"), encoding="ascii"))
    for lang in ("eng", "rus"):
        for j in JOBS:
            for s in ("", "_text", "_descr"):
                if j["soc"] + s not in T[lang]:
                    raise SystemExit("no SoC text %s%s (%s)" % (j["soc"], s, lang))
    gen_cfg(G)
    gen_tm(G)
    gen_text(G, T)
    gen_dialogs(G)
    gen_lua(G)
    per = {}
    for j in JOBS:
        per[j["giver"]] = per.get(j["giver"], 0) + 1
    print("%d fetch jobs: %s" % (len(JOBS), ", ".join("%s %d" % kv for kv in sorted(per.items()))))


if __name__ == "__main__":
    main()
