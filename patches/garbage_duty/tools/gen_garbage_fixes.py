"""Generates the Garbage config edits of the patches garbage_gray (bandits), campfires (Bes, Gray), garbage_duty (Duty checkpoint).

  python gen_garbage_fixes.py [<mod gamedata.db0 folder>]

Reads the mod sources (read only) or the already patched copies, and writes the files into the patch folders. Every edit asserts that the text it
changes is there exactly once, running it twice changes nothing. Files keep their bytes (windows-1251 text is handled as latin-1), CRLF kept.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(r"~\Downloads\Shadow of COOP 8.0\source\gamedata.db0")
CFG = os.path.join(SRC, "configs")
NL = "\r\n"


def rd(p):
    return open(p, "rb").read().decode("latin-1")


def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(s.encode("latin-1"))


def patch_path(patch, rel):
    return os.path.join(PATCHES, patch, "gamedata", rel)


def base_text(patch, rel):
    """the patched copy when it exists (idempotent), else the mod file"""
    p = patch_path(patch, rel)
    if os.path.exists(p):
        return rd(p)
    return rd(os.path.join(SRC, rel))


def sub1(s, pat, repl, flags=0, count=1):
    n = len(re.findall(pat, s, flags))
    assert n == count, "pattern %r matched %d times (want %d)" % (pat, n, count)
    return re.sub(pat, lambda m: repl if not callable(repl) else repl(m), s, flags=flags)


def crlf(s):
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


# ------------------------------------------------------------------------------------------------ Bes (campfires copy)
def bes():
    rel = r"configs\scripts\coop_l02_garbage\gar_smart_terrain_2_walker_devil.ltx"
    s = rd(patch_path("campfires", rel))
    if "walker_devil_done" in s:
        return
    # 1. the post-battle talk (bandits dead, reward not yet paid): his start line is the short "Ну и бойня..." (existing dialog), not the request
    s = sub1(s, r"(\[meet@gar_smart_terrain_2_walker_devil\]\r\n(?:[^\[]*?)trade_enable[^\r\n]*\r\n)",
             lambda m: m.group(1) + "meet_dialog = gar_smart_terrain_4_stalker_devil_2_start_dialog" + NL)
    # 2. after the reward he stays talkable with the same short line (was: no_meet, and the greeting came back)
    s = sub1(s, r"(\[kamp@gar_smart_terrain_2_animpoint_1_no_meet\]\r\n(?:[^\[]*?)meet[ \t]*=[ \t]*)no_meet",
             lambda m: m.group(1) + "meet@gar_smart_terrain_2_walker_devil_done")
    s = s.rstrip("\r\n") + NL + NL + crlf("""[meet@gar_smart_terrain_2_walker_devil_done]
close_snd_hello = nil
close_snd_bye = nil
close_anim = nil
close_victim = nil
far_anim = nil
far_victim = nil
close_distance = 0
far_distance = 0
close_snd_distance = 5
abuse = false
use = {=actor_enemy} false, true
allow_break = true
meet_on_talking = false
trade_enable = false
meet_dialog = gar_smart_terrain_4_stalker_devil_2_start_dialog
""")
    wr(patch_path("campfires", rel), s)


# ------------------------------------------------------------------------------------------------ Gray attack start (campfires copy)
def gray():
    """The fight is started by the server tick of coop_scn_garbage_duty.script (the SoC zones gar_seryi_factory / igrok_durak / shuher, any player), not by the task signal:
    an earlier draft gave the info with the task and Gray's stalkers could die unseen. Reverts that draft when it is in the copy."""
    rel = r"configs\scripts\coop_l02_garbage\gar_smart_terrain_7_walker_gray.ltx"
    s = rd(patch_path("campfires", rel))
    s = s.replace(" +GAR_THE_ORDER_TO_KILL_GRAY_INFO%", "%")
    wr(patch_path("campfires", rel), s)


# ------------------------------------------------------------------------------------------------ 6 bandits (garbage_gray)
# idle spot / look point, attack walk point (all paths of gar_smart_terrain_6: a job can only use the paths of its own smart terrain)
BANDITS = [
    # k, idle walk, idle look, standing state, attack walk, attack look
    (1, "walker_3_look", "walker_2_look", "hide_na", "walker_2_look", "walker_5_look"),
    (2, "walker_2_walk", "walker_2_look", "hide_fire", "walker_2_look", "walker_5_look"),
    (3, "walker_3_walk", "walker_3_look", "hide", "walker_5_look", "walker_2_look"),
    (4, "walker_4_walk", "walker_4_look", "hide", "walker_2_look", "walker_5_look"),
    (5, "walker_5_walk", "walker_5_look", "hide_fire", "walker_5_look", "walker_2_look"),
    (6, "walker_4_look", "walker_5_look", "hide", "walker_5_look", "walker_2_look"),
]


def bandits():
    out = []
    for k, w, l, st, aw, al in BANDITS:
        n = "gar_smart_terrain_6_walker_bandit_%d" % k
        out.append("""[logic@%(n)s]
suitable = {=check_npc_name(sim_default_bandit_1)} true
active = walker@%(n)s_idle
prior = 300

[walker@%(n)s_idle]
path_walk = %(w)s
path_look = %(l)s
def_state_standing = %(st)s
def_state_moving = assault
invulnerable = true
meet = no_meet
combat_ignore_cond = true
combat_ignore_keep_when_attacked = true
on_info = {+GAR_THE_ORDER_TO_KILL_GRAY_INFO} walker@%(n)s_attack

[walker@%(n)s_attack]
path_walk = %(aw)s
path_look = %(al)s
def_state_moving = assault
meet = no_meet

;================================================
""" % dict(n=n, w=w, l=l, st=st, aw=aw, al=al))
    wr(patch_path("garbage_gray", r"configs\scripts\coop_l02_garbage\gar_smart_terrain_6_walker_bandit.ltx"), crlf("\n".join(out)))

    rel = r"configs\scripts\coop_l02_garbage\smart\gar_smart_terrain_6.ltx"
    s = base_text("garbage_gray", rel)
    if "walker_bandit_6" not in s:
        s = sub1(s, r"(gar_smart_terrain_6_walker_bandit_5[ \t]*=[ \t]*coop_l02_garbage\\gar_smart_terrain_6_walker_bandit\.ltx)",
                 lambda m: m.group(1) + NL + "gar_smart_terrain_6_walker_bandit_6\t\t= coop_l02_garbage\\gar_smart_terrain_6_walker_bandit.ltx")
    wr(patch_path("garbage_gray", rel), s)


# ------------------------------------------------------------------------------------------------ squads (garbage_gray owns the file)
def squads():
    rel = r"configs\misc\squad_descr_coop_l02_garbage.ltx"
    s = base_text("garbage_gray", rel)
    # 6th bandit (SoC gar_seryi_bandits: six)
    s = re.sub(r"(\[gar_smart_terrain_6_bandit_2_squad\][^\[]*?npc = sim_default_bandit_1, sim_default_bandit_1)(\r\n)",
               lambda m: m.group(1) + ", sim_default_bandit_1" + m.group(2), s, count=1) if "bandit_2_squad]:online_offline_group\r\nfaction = bandit\r\nnpc = sim_default_bandit_1, sim_default_bandit_1, sim_default_bandit_1" not in s else s
    assert re.search(r"\[gar_smart_terrain_6_bandit_2_squad\][^\[]*?npc = sim_default_bandit_1, sim_default_bandit_1, sim_default_bandit_1\r\n", s)
    # Duty checkpoint: the SoC checkpoint characters (class gar_dolg_blokpost) instead of the generic Duty
    for sq in ("gar_smart_terrain_9_duty_1_squad", "gar_smart_terrain_9_duty_2_squad", "gar_smart_terrain_9_duty_3_squad"):
        s = re.sub(r"(\[%s\][^\[]*?npc = )sim_default_duty_2, sim_default_duty_2, sim_default_duty_2" % sq,
                   lambda m: m.group(1) + "gar_dolg_blokpost, gar_dolg_blokpost, gar_dolg_blokpost", s, count=1)
        assert re.search(r"\[%s\][^\[]*?npc = gar_dolg_blokpost, gar_dolg_blokpost, gar_dolg_blokpost" % sq, s), sq
    s = re.sub(r"(\[gar_smart_terrain_9_duty_prapor_squad\][^\[]*?npc = gar_smart_terrain_8_duty_prapor, )sim_default_duty_3, sim_default_duty_3",
               lambda m: m.group(1) + "gar_dolg_blokpost, gar_dolg_blokpost", s, count=1)
    assert re.search(r"\[gar_smart_terrain_9_duty_prapor_squad\][^\[]*?npc = gar_smart_terrain_8_duty_prapor, gar_dolg_blokpost, gar_dolg_blokpost", s)
    wr(patch_path("garbage_gray", rel), s)

    # player_scaling copy of the same squad (generated file, kept in step)
    p = patch_path("player_scaling", r"configs\misc\squad_descr_pscale.ltx")
    t = rd(p)
    if not re.search(r"\[gar_smart_terrain_6_bandit_2_squad_ps\][^\[]*?npc = sim_default_bandit_1, sim_default_bandit_1, sim_default_bandit_1\r?\n", t):
        t = sub1(t, r"(\[gar_smart_terrain_6_bandit_2_squad_ps\][^\[]*?npc = sim_default_bandit_1, sim_default_bandit_1)(\r?\n)",
                 lambda m: m.group(1) + ", sim_default_bandit_1" + m.group(2))
    wr(p, t)


# ------------------------------------------------------------------------------------------------ Duty (garbage_duty + campfires + freedom_duty)
def duty_jobs():
    # jobs take the SoC checkpoint characters
    rel = r"configs\scripts\coop_l02_garbage\gar_smart_terrain_9_walker_duty.ltx"
    s = base_text("garbage_duty", rel)
    s = re.sub(r"check_npc_name\(sim_default_duty_[23]\)", "check_npc_name(gar_dolg_blokpost)", s)
    assert "sim_default_duty" not in s
    wr(patch_path("garbage_duty", rel), s)

    rel = r"configs\scripts\coop_l02_garbage\gar_smart_terrain_9_animpoint_duty.ltx"
    s = rd(patch_path("campfires", rel))
    s = re.sub(r"check_npc_name\(sim_default_duty_[23]\)", "check_npc_name(gar_dolg_blokpost)", s)
    assert "sim_default_duty" not in s
    wr(patch_path("campfires", rel), s)

    # boars: every boar reports a kill by a player (SoC [mob_death@gar_boars_rush] / killed_by_actor, one flag per boar)
    rel = r"configs\scripts\coop_l02_garbage\gar_smart_terrain_8_m_boar_squad.ltx"
    s = base_text("garbage_duty", rel)
    if "mob_death@" not in s:
        for n in range(1, 9):
            s = sub1(s, r"(\[logic@gar_smart_terrain_8_m_boar_squad_%d\]\r\n(?:[^\[]*?)prior[ \t]*=[ \t]*300\r\n)" % n,
                     lambda m, n=n: m.group(1) + "on_death = mob_death@gar_smart_terrain_8_m_boar_squad_%d_death" % n + NL)
        s = s.rstrip("\r\n") + NL + NL
        for n in range(1, 9):
            s += "[mob_death@gar_smart_terrain_8_m_boar_squad_%d_death]" % n + NL
            s += "on_info = {=killed_by_actor} %%+GAR_DUTY_BOAR_KILLED_%d%%" % n + NL + NL
    wr(patch_path("garbage_duty", rel), s)

    # profile of the checkpoint class (freedom_duty owns npc_profile_addon.xml)
    p = patch_path("freedom_duty", r"configs\gameplay\npc_profile_addon.xml")
    t = rd(p)
    if 'id="gar_dolg_blokpost"' not in t:
        nl = "\r\n" if "\r\n" in t else "\n"
        t = sub1(t, r'(<character id="gar_smart_terrain_8_duty_prapor">\s*<class>gar_smart_terrain_8_duty_prapor</class>\s*</character>)',
                 lambda m: m.group(1) + nl + '\t<character id="gar_dolg_blokpost">' + nl + "\t\t<class>gar_dolg_blokpost</class>" + nl + "\t</character>")
    wr(p, t)

    # spawn section of the class
    rel = r"configs\creatures\spawn_sections_coop_l02_garbage.ltx"
    s = base_text("garbage_duty", rel)
    if "[gar_dolg_blokpost]" not in s:
        s = s.rstrip("\r\n") + NL + NL + crlf("""[gar_dolg_blokpost]:stalker
$spawn = "respawn\\gar_dolg_blokpost"
character_profile = gar_dolg_blokpost
spec_rank = experienced
community = dolg
""")
    wr(patch_path("garbage_duty", rel), s)


def character_desc():
    rel = r"configs\gameplay\character_desc_coop_l02_garbage.xml"
    s = base_text("garbage_duty", rel)
    if "gar_dolg_blokpost_balon_8" in s:
        return
    # commander = SoC gar_dolg_blokpost_commander (visual stalker_do_balon_4), his talk is the SoC checkpoint dialog
    blk = re.search(r'<specific_character id="gar_smart_terrain_8_duty_prapor".*?</specific_character>', s, re.S)
    b = blk.group(0)
    b2 = b.replace(r"<visual>actors\stalker_dolg\stalker_dolg_4</visual>", r"<visual>actors\dolg\stalker_do_balon_4</visual>")
    b2 = b2.replace("<start_dialog>gar_smart_terrain_8_duty_prapor_start_dialog</start_dialog>", "<start_dialog>gar_duty_pass_start_dialog</start_dialog>")
    assert b2 != b and "gar_duty_pass_start_dialog" in b2 and "stalker_do_balon_4" in b2
    s = s.replace(b, b2)

    def spec(sid, icon, visual, rank, rep, weapon, ammo):
        return crlf("""
<specific_character id="%(sid)s" team_default = "1">
	<name>GENERATE_NAME_sergeant</name>
	<icon>%(icon)s</icon>
	<map_icon x="1" y="0"></map_icon>
	<bio>gar_dolg_blokpost_bio</bio>

	<class>gar_dolg_blokpost</class>
	<community>dolg</community>
	<snd_config>characters_voice\\human_02\\dolg\\</snd_config>

	<rank>%(rank)d</rank>
	<reputation>%(rep)d</reputation>
	<money min="600" max="2000" infinitive="0"/>

	<visual>%(visual)s</visual>
	<crouch_type>0</crouch_type>
	<supplies>
		[spawn] \\n
		wpn_pm = 1 \\n
		ammo_9x18_fmj = 1 \\n
		%(weapon)s = 1 \\n
		%(ammo)s = 1 \\n
#include "gameplay\\character_items_2.xml"
#include "gameplay\\character_food.xml"
#include "gameplay\\character_drugs_2.xml"
	</supplies>
#include "gameplay\\character_criticals_4.xml"
#include "gameplay\\character_dialogs.xml"
</specific_character>
""" % dict(sid=sid, icon=icon, visual=visual, rank=rank, rep=rep, weapon=weapon, ammo=ammo))

    add = NL + crlf("<!-- Duty checkpoint on the road to the Bar: SoC gar_dolg_blokpost (class), skins of the SoC instances gar_dolg_blokpost_1..8 -->")
    add += spec("gar_dolg_blokpost_balon_8", "ui_portret_dolg_2", r"actors\dolg\stalker_do_balon_8", 520, 86, "wpn_ak74u", "ammo_5.45x39_ap")
    add += spec("gar_dolg_blokpost_antigas", "ui_portret_dolg_2", r"actors\dolg\stalker_do_antigas", 499, 120, "wpn_ak74u", "ammo_5.45x39_fmj")
    add += spec("gar_dolg_blokpost_balon_80", "ui_portret_dolg_2", r"actors\dolg\stalker_do_balon_80", 471, 124, "wpn_ak74u", "ammo_5.45x39_ap")
    # insert before the closing tag of the root (the file ends with an xml wrapper in the mod: find the last specific_character)
    i = s.rindex("</specific_character>") + len("</specific_character>")
    s = s[:i] + add + s[i:]
    wr(patch_path("garbage_duty", rel), s)


# ------------------------------------------------------------------------------------------------ dialog + strings (garbage_duty)
RU = {
    "gar_duty_pass_i_see": "Понятно.",
    "gar_duty_pass_rules": "Таковы наши правила.",
    "gar_duty_pass_pay": "Нет, я лучше заплачу за проход (2000 руб.). Вот, держи.",
    "gar_duty_pass_paid": "Отлично, теперь проходи, и лучше чтобы у тебя действительно было важное дело к бармену. Будь осторожнее, дальше по дороге много аномалий.",
    "gar_duty_pass_no_money": "У меня нет денег.",
    "gar_duty_pass_no_pass": "Тогда в бар тебе прохода нет.",
    "gar_duty_pass_say_hi": "Будешь у бармена, передай привет от меня. Да, не забудь, в проходе много аномалий, будь осторожен.",
    "gar_dolg_blokpost_bio": "Сталкер группировки \"Долг\". Детальная информация отсутствует.",
    "gar_duty_rush_win": "Отлично Меченый, ты действительно нам сильно помог. Будем считать, что ты оплатил свой пропуск. Можешь идти на Бар.",
    "gar_duty_rush_lose": "Ну и слабак ты, Меченый, пользы от тебя ноль. Так что и благодарности от нас ты не дождешься. Не за что тебя благодарить.",
    "st_gar_duty_lang_probe": "Язык",
}
EN = {
    "gar_duty_pass_i_see": "I see.",
    "gar_duty_pass_rules": "Those are the rules.",
    "gar_duty_pass_pay": "I'd rather pay (2000 RU). Here.",
    "gar_duty_pass_paid": "Good! You can go, but you better have some really important business with the Barkeep, you hear? And be careful - there's lots of anomalies ahead.",
    "gar_duty_pass_no_money": "I don't have the money.",
    "gar_duty_pass_no_pass": "Well, you can't go through to the bar then.",
    "gar_duty_pass_say_hi": "Say \"hi\" for the Barkeep from me when you see him. Oh, and don't forget - there are lots of anomalies on the way, so be careful.",
    "gar_dolg_blokpost_bio": "Duty stalker. No detailed information.",
    "gar_duty_rush_win": "Excellent, Marked One, you really helped us out there. I say that's payment enough for your pass. Go on to the Bar.",
    "gar_duty_rush_lose": "You're rubbish, Marked One. Totally useless! Don't expect gratitude - there's nothing to thank you for!",
    "st_gar_duty_lang_probe": "Language",
}


def strings():
    for lang, tbl, enc in (("eng", EN, "utf-8"), ("rus", RU, "cp1251")):
        hdr = '<?xml version="1.0" encoding="%s" ?>' % ("windows-1251" if enc == "cp1251" else "UTF-8")
        body = hdr + "\r\n<string_table>\r\n"
        for k, v in tbl.items():
            body += '\t<string id="%s">\r\n\t\t<text>%s</text>\r\n\t</string>\r\n' % (k, v.replace("&", "&amp;").replace("<", "&lt;"))
        body += "</string_table>\r\n"
        p = patch_path("garbage_duty", r"configs\text\%s\st_garbage_duty.xml" % lang)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(body.encode(enc))


def ph(pid, text, nxt=(), pre=None, act=None, say=None):
    s = '            <phrase id="%s">\r\n' % pid
    if say:
        s += "                <action>coop_pda_phrases.say__%s</action>\r\n" % say
    if pre:
        for p in pre:
            s += "                <precondition>coop_scn_garbage_duty.%s</precondition>\r\n" % p
    if act:
        s += "                <action>coop_scn_garbage_duty.%s</action>\r\n" % act
    s += ("                <text>%s</text>\r\n" % text) if text else "                <text />\r\n"
    for n in nxt:
        s += "                <next>%s</next>\r\n" % n
    s += "            </phrase>\r\n"
    return s


def dialog():
    rel = r"configs\gameplay\dialogs_coop_l02_garbage.xml"
    s = base_text("garbage_duty", rel)
    if "gar_duty_pass_start_dialog" in s:
        return
    P = "gar_smart_terrain_8_duty_prapor_"
    d = '    <!-- Duty checkpoint commander, the SoC dialog gar_dolg_blokpost: closed until the pass (case / money / boars), phrase ids are the SoC ones -->\r\n'
    d += '    <dialog id="gar_duty_pass_start_dialog">\r\n        <phrase_list>\r\n'
    d += ph("0", None, ["1", "3"])
    d += ph("1", None, ["11"], pre=["pass_closed"])
    d += ph("11", P + "start_dialog_0", ["111"], say=P + "start_dialog_0")
    d += ph("111", P + "the_destination_is_a_bar_0", ["1111"], say=P + "the_destination_is_a_bar_0")
    d += ph("1111", P + "the_destination_is_a_bar_1", ["11111", "11112", "1111211", "111122"], say=P + "the_destination_is_a_bar_1")
    d += ph("11111", "gar_duty_pass_i_see", ["111111"], pre=["case_missing"])
    d += ph("111111", "gar_duty_pass_rules")
    d += ph("11112", P + "the_destination_is_a_bar_2", ["111121"], pre=["case_have"], say=P + "the_destination_is_a_bar_2")
    d += ph("111121", P + "the_destination_is_a_bar_3", ["123"], act="give_pass_case", say=P + "the_destination_is_a_bar_3")
    d += ph("123", P + "the_destination_is_a_bar_4", ["33"], say=P + "the_destination_is_a_bar_4")
    d += ph("1111211", "gar_duty_pass_pay", ["11112111"], pre=["can_pay"], act="give_pass_money")
    d += ph("11112111", "gar_duty_pass_paid")
    d += ph("111122", "gar_duty_pass_no_money", ["111123"], pre=["cannot_pay"])
    d += ph("111123", "gar_duty_pass_no_pass")
    d += ph("3", None, ["33"], pre=["pass_open"])
    d += ph("33", "gar_duty_pass_say_hi")
    d += "        </phrase_list>\r\n    </dialog>\r\n"
    i = s.rindex("</game_dialogs>")
    s = s[:i] + d + s[i:]
    wr(patch_path("garbage_duty", rel), s)


if __name__ == "__main__":
    bes()
    gray()
    bandits()
    squads()
    duty_jobs()
    character_desc()
    strings()
    dialog()
    print("done")
