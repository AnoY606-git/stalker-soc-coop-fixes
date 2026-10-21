"""Offline consistency check of the repeatable quests (no game needed).
python check_rq.py [<patch dir (repeatable_quests)>] [--mod <Shadow of COOP source dir>]
Every job in coop_repeat_quests.ltx [list] must have: a section with level/kind/flags, a task section in tm_coop_repeat.ltx (title, descr, icon, both
condlists), eng + rus strings (title, descr, offer, npc, accept, hand-in lines) with identical id sets, an offer + accept phrase in a dialog that is attached
to an NPC, and a way to finish: gen_find / gen_fetch need a hand-in phrase that sets the DONE flag and a hand-in dialog attached to an NPC, with a Lua
precondition / action that exists in coop_rq_dialogs.script. Icons must exist in a textures_descr (this patch's or the mod's). Hidden tasks must exist.
gen_fetch jobs also: an offer phrase with a Lua precondition (SoC priority rule), prior / gate / items of the ltx equal the FETCH table of the script, gate flags
exist in the mod's story_flags_table (--mod), every dialog is a valid phrase graph (unique ids, every <next> target exists), and the longest possible
menu of every giver is reported (a giver offers at most one artifact and one part order at a time).
NPCs are searched in this patch's character_desc files and in those of the sibling patches (the Freedom leader lives in freedom_duty).
Exit code 1 when anything is wrong."""
import os, re, sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
here = os.path.dirname(os.path.abspath(__file__))
patch = args[0] if args else os.path.dirname(here)
mod = None
if "--mod" in sys.argv:
    mod = sys.argv[sys.argv.index("--mod") + 1]
G = os.path.join(patch, "gamedata")
bad = []


def rd(rel):
    return open(os.path.join(G, rel), "rb").read().decode("cp1251").replace("\r\n", "\n")


def sections(text):
    out = {}
    for m in re.finditer(r"^\[(\w+)\]\n(.*?)(?=\n\[|\Z)", text, re.M | re.S):
        d = {}
        for ln in m.group(2).split("\n"):
            if "=" in ln and not ln.lstrip().startswith(";"):
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip()
        out[m.group(1)] = d
    return out


def err(msg):
    bad.append(msg)
    print("FAIL", msg)


ltx = rd("configs/misc/coop_repeat_quests.ltx")
S = sections(ltx)
jobs = [l.strip() for l in S_list.split("\n")] if False else [l.strip() for l in re.search(r"\[list\]\n(.*?)\n\n", ltx, re.S).group(1).split("\n") if l.strip()]
tm = sections(rd("configs/misc/tm_coop_repeat.ltx"))
strings = {}
for lang in ("eng", "rus"):
    t = rd("configs/text/%s/st_coop_repeat_quests.xml" % lang)
    strings[lang] = dict(re.findall(r'<string id="([^"]+)">\s*<text>(.*?)</text>', t, re.S))
if set(strings["eng"]) != set(strings["rus"]):
    err("eng / rus string ids differ: %s" % sorted(set(strings["eng"]) ^ set(strings["rus"]))[:10])
for lang, d in strings.items():
    for i, v in d.items():
        if chr(0x2014) in v or chr(0x2013) in v:
            err("%s: dash in %s" % (lang, i))
        if lang == "rus" and not re.search("[Ѐ-ӿ]", v) and not re.fullmatch(r"[\d\W]*", v) and len(v) > 12:
            err("rus string without Cyrillic: %s" % i)
dlg = rd("configs/gameplay/dialogs_coop_repeat_quests.xml")
dialogs = {m.group(1): m.group(2) for m in re.finditer(r'<dialog id="(\w+)">(.*?)</dialog>', dlg, re.S)}
attached = set()
for f in os.listdir(os.path.join(G, "configs", "gameplay")):
    if f.startswith("character_desc"):
        attached |= set(re.findall(r"(?<!<!--)<actor_dialog>(rq_\w+)</actor_dialog>", rd("configs/gameplay/" + f)))
import glob
for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(patch)), "*", "gamedata", "configs", "gameplay", "character_desc*.xml")):
    if os.path.abspath(os.path.dirname(f)) == os.path.abspath(os.path.join(G, "configs", "gameplay")):
        continue
    txt = re.sub(r"<!--.*?-->", "", open(f, "rb").read().decode("cp1251", "replace"), flags=re.S)
    attached |= set(re.findall(r"<actor_dialog>(rq_\w+)</actor_dialog>", txt))
lua = rd("scripts/coop_rq_dialogs.script")
lua_funcs = set(re.findall(r"^function (\w+)\(", lua, re.M))
tex = rd("configs/ui/textures_descr/ui_rq_task_icons.xml")
icons = set(re.findall(r'<texture id="(\w+)"', tex))
if mod:
    nm = open(os.path.join(mod, "gamedata.db0", "configs", "ui", "textures_descr", "ui_actor_newsmanager_icons.xml"), "rb").read().decode("cp1251", "replace")
    icons |= set(re.findall(r'<texture id="(\w+)"', nm))
used_strings = set(re.findall(r"<text>(\w+)</text>", dlg))
for i in used_strings:
    for lang in ("eng", "rus"):
        if i not in strings[lang]:
            err("dialog text %s missing in %s" % (i, lang))
n_fetch = n_find = 0
fetch_meta = {}
mod_flags = None
if mod:
    sf = os.path.join(mod, "gamedata.db1", "scripts", "story_flags_table.script")
    if os.path.exists(sf):
        mod_flags = set(re.findall(r'"([A-Z0-9_]+)"', open(sf, "rb").read().decode("cp1251", "replace")))
for j in jobs:
    s = S.get(j)
    if s is None:
        err("%s: no section" % j)
        continue
    for k in ("level", "kind", "accept", "done", "fail"):
        if k not in s:
            err("%s: no %s" % (j, k))
    kind = s.get("kind")
    flag = j.upper()
    if s.get("accept") != "RQG_%s_ACC" % flag or s.get("done") != "RQG_%s_DONE" % flag or s.get("fail") != "RQG_%s_FAIL" % flag:
        err("%s: flag names do not follow RQG_<ID>_ACC/DONE/FAIL" % j)
    t = tm.get(j)
    if t is None:
        err("%s: no task section in tm_coop_repeat.ltx" % j)
    else:
        for k in ("icon", "title", "descr", "condlist_0", "condlist_1"):
            if k not in t:
                err("%s: task has no %s" % (j, k))
        if t.get("icon") not in icons:
            err("%s: icon %s is in no textures_descr" % (j, t.get("icon")))
        if "RQG_%s_DONE" % flag not in t.get("condlist_0", "") or "RQG_%s_FAIL" % flag not in t.get("condlist_1", ""):
            err("%s: task condlists do not use the done / fail flags" % j)
        for k in ("title", "descr"):
            for lang in ("eng", "rus"):
                if t.get(k) not in strings[lang]:
                    err("%s: %s string %s missing in %s" % (j, k, t.get(k), lang))
    for suf in ("offer", "npc", "accept"):
        for lang in ("eng", "rus"):
            if "%s_%s" % (j, suf) not in strings[lang]:
                err("%s: string %s_%s missing in %s" % (j, j, suf, lang))
    if kind in ("gen_find", "gen_fetch"):
        for lang in ("eng", "rus"):
            if "rq_handin_" + j not in strings[lang]:
                err("%s: hand-in string missing in %s" % (j, lang))
    # offer + accept phrase in a dialog that an NPC carries
    off = [d for d, b in dialogs.items() if "<text>%s_offer</text>" % j in b]
    acc = [d for d, b in dialogs.items() if re.search(r"<give_flag>RQG_%s_ACC</give_flag>" % flag, b)]
    if not off or not acc:
        err("%s: no offer / accept phrase in the dialogs" % j)
    elif not (set(off) & attached):
        err("%s: offer dialog %s is attached to no NPC" % (j, off))
    if kind in ("gen_find", "gen_fetch"):
        hand = [d for d, b in dialogs.items() if re.search(r"<give_flag>RQG_%s_DONE</give_flag>" % flag, b) or "RQG_%s_DONE</give_flag>" % flag in b]
        if not hand:
            err("%s: no hand-in phrase sets the done flag" % j)
        elif not (set(hand) & attached):
            err("%s: hand-in dialog %s is attached to no NPC" % (j, hand))
        else:
            for d in hand:
                body = dialogs[d]
                if "<precondition>coop_rq_dialogs." not in body.split("<phrase_list>")[0]:
                    err("%s: hand-in dialog %s has no dialog-level precondition (it would show without a job)" % (j, d))
                for fn in re.findall(r"<(?:precondition|action)>coop_rq_dialogs\.(\w+)<", body):
                    if fn not in lua_funcs:
                        err("%s: %s is not defined in coop_rq_dialogs.script" % (j, fn))
    if kind == "gen_fetch":
        n_fetch += 1
        for fn in ("has_" + j, "pay_" + j):
            if fn not in lua_funcs:
                err("%s: %s missing" % (j, fn))
        if not re.search(r"\b%s = \{giver" % j, lua):
            err("%s: not in the FETCH table of coop_rq_dialogs.script" % j)
        if s.get("pay_items") is None or s.get("item") is None:
            err("%s: item / pay_items missing" % j)
        if int(s.get("pay_money", "0")) <= 0 and s.get("pay_items", "none") == "none":
            err("%s: neither money nor items are paid" % j)
        m_f = re.search(r"\b%s = \{giver = \"(\w+)\", kind = \"(\w+)\", prior = (\d+), gate = \{(.*?)\}, secs = \{(.*?)\}, count = (\d+), money = (\d+), items = \{(.*?)\}\}" % j, lua)
        if m_f is None:
            err("%s: FETCH table line has an unexpected shape" % j)
        else:
            q = lambda x: [a for a in re.findall(r'"([^"]+)"', x)]
            if s.get("prior") != m_f.group(3):
                err("%s: prior ltx %s != lua %s" % (j, s.get("prior"), m_f.group(3)))
            if q(m_f.group(4)) != ([] if s.get("gate", "none") == "none" else s["gate"].split(",")):
                err("%s: gate differs between ltx and lua" % j)
            if q(m_f.group(5)) != s.get("item", "").split(","):
                err("%s: item differs between ltx and lua" % j)
            if int(m_f.group(7)) != int(s.get("pay_money", "0")):
                err("%s: pay_money differs between ltx and lua" % j)
            if q(m_f.group(8)) != ([] if s.get("pay_items", "none") == "none" else s["pay_items"].split(",")):
                err("%s: pay_items differ between ltx and lua" % j)
            fetch_meta[j] = (m_f.group(1), m_f.group(2), q(m_f.group(4)))
        for fn in ("offer_" + j,):
            if fn not in lua_funcs:
                err("%s: %s missing" % (j, fn))
        if not re.search(r"<text>%s_offer</text><precondition>coop_rq_dialogs\.offer_%s</precondition>" % (j, j), dlg):
            err("%s: the offer phrase has no offer_%s precondition (the SoC priority rule would not apply)" % (j, j))
        for g in s.get("gate", "none").split(","):
            if g != "none" and mod_flags is not None and g not in mod_flags:
                err("%s: gate flag %s is not a story flag of the mod" % (j, g))
        if "reward_items" in s:
            err("%s: reward_items would pay every player; use pay_items" % j)
    if kind == "gen_find":
        n_find += 1
# every dialog is a valid phrase graph; longest possible menu per giver
menu = {}
for d, body in dialogs.items():
    ids = re.findall(r'<phrase id="(\d+)">', body)
    if len(ids) != len(set(ids)):
        err("dialog %s: duplicate phrase ids %s" % (d, sorted(i for i in set(ids) if ids.count(i) > 1)))
    for tgt in set(re.findall(r"<next>(\d+)</next>", body)):
        if tgt not in ids:
            err("dialog %s: <next>%s</next> points to no phrase" % (d, tgt))
    m1 = re.search(r'<phrase id="1"><text>rq_npc_work</text>((?:<next>\d+</next>)+)</phrase>', body)
    if m1:
        offers = [x for x in re.findall(r"<next>(\d+)</next>", m1.group(1)) if x != "99"]
        for o in re.findall(r'<phrase id="(\d+)"><text>rq_\w+_offer</text>', body):
            if o not in offers:
                err("dialog %s: offer phrase %s is not listed after rq_npc_work (never shown)" % (d, o))
        plain = fetch_ids = 0
        for o in offers:
            mo = re.search(r'<phrase id="%s"><text>(rq_\w+)_offer</text>' % o, body)
            if mo and mo.group(1) in fetch_meta:
                fetch_ids += 1
            else:
                plain += 1
        kinds = len(set(fetch_meta[mo2][1] for mo2 in fetch_meta if re.search(r'<text>%s_offer</text>' % mo2, body)))
        menu[d] = (plain, fetch_ids, plain + kinds)
for d, (plain, nf, mx) in sorted(menu.items()):
    if nf:
        print("menu %s: %d fixed offers + %d fetch orders of which at most %d at a time = at most %d entries (+ Not now)" % (d, plain, nf, mx - plain, mx))
        if mx > 9:
            err("dialog %s: the menu can get longer than 9 entries" % d)
# every dialog id used by an NPC exists, no NPC carries a dialog of a removed giver
for a in attached:
    if a not in dialogs:
        err("character_desc attaches %s but it is not defined" % a)
for d in dialogs:
    if d not in attached:
        err("dialog %s is defined but attached to no NPC" % d)
# the mod's generic task menu must be gone from every NPC
for f in os.listdir(os.path.join(G, "configs", "gameplay")):
    if f.startswith("character_desc"):
        t = re.sub(r"<!--.*?-->", "", rd("configs/gameplay/" + f), flags=re.S)
        for m in re.findall(r"<actor_dialog>(\w+_secondary_quests_dialog)</actor_dialog>", t):
            err("%s still offers the generic task menu %s" % (f, m))
# hidden tasks exist
hid = [l.strip() for l in re.search(r"\[list\]\n(.*)", rd("configs/misc/coop_hidden_tasks.ltx"), re.S).group(1).split("\n") if l.strip() and not l.strip().startswith(";")]
if mod:
    alltm = ""
    mm = os.path.join(mod, "gamedata.db0", "configs", "misc")
    for f in os.listdir(mm):
        if f.startswith("tm_coop_l"):
            alltm += open(os.path.join(mm, f), "rb").read().decode("cp1251", "replace")
    # tasks added by sibling patches (for example darkvalley_restore) count as tasks of the mod too
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(patch)), "*", "gamedata", "configs", "misc", "tm_coop_l*.ltx")):
        alltm += open(f, "rb").read().decode("cp1251", "replace")
    for h in hid:
        if "[%s]" % h not in alltm:
            err("hidden task %s is not a task of the mod" % h)
print("%d jobs (%d fetch, %d find), %d strings per language, %d hidden tasks, %d problems" % (len(jobs), n_fetch, n_find, len(strings["eng"]), len(hid), len(bad)))
sys.exit(1 if bad else 0)
