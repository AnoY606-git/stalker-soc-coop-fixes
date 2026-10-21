"""Task sections of patch soc_aes_quests (idempotent, deterministic).

  python apply_tm.py <mod source configs\\misc dir>

Makes gamedata\\configs\\misc\\tm_coop_l10_pripyat.ltx and tm_coop_l11_control_monolith.ltx from the mod's own files (nobody else ships them) and edits
the copy of tm_coop_l11_sarcofag.ltx that patch sarcophagus_count owns (one patch per file) in place. Files are read and written as bytes
(utf-8 comments, CRLF). A second run changes nothing.

What changes (see NOTES.md):
  pripyat   : the stash task of SoC (cit_doctor_task, three steps) is new; the meeting / following steps also close when the party is on CNPP-1.
  control   : ONE "Solve the Monolith's secret" task done when all six generators are down (the other five steps are hidden), the talk with
              C-Consciousness no longer hands out the mod-only "kill all representatives" task.
  sarcofag  : "Sneak in to the sarcophagus", "Find the Wish Granter", the secret lab steps (bunker, hidden door, behind the door) are new; the door step
              is done by the decoder use, the Preacher steps are no longer chained (they stay in the file, hidden).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GD = os.path.join(os.path.dirname(HERE), "gamedata", "configs", "misc")
REPO_PATCHES = os.path.dirname(os.path.dirname(HERE))
SARC = os.path.join(REPO_PATCHES, "sarcophagus_count", "gamedata", "configs", "misc", "tm_coop_l11_sarcofag.ltx")
MARK = b"; soc_aes_quests"
CRLF = chr(13) + chr(10)
TABS = chr(9) * 8


def sect(name, icon, prior, title, descr, target, conds):
    lines = ["[%s]" % name,
             "icon \t\t\t\t\t\t\t\t\t= " + icon,
             "prior \t\t\t\t\t\t\t\t\t= " + str(prior),
             "storyline \t\t\t\t\t\t\t\t= true",
             "title \t\t\t\t\t\t\t\t\t= " + title,
             "descr \t\t\t\t\t\t\t\t\t= " + descr,
             "target \t\t\t\t\t\t\t\t\t= " + target]
    for i, c in enumerate(conds):
        lines.append("condlist_%d \t\t\t\t\t\t\t\t= %s" % (i, c))
    return "\r\n".join(lines) + "\r\n"


def set_conds(text, section, conds):
    """replace the condlist_N lines of one section (text is str with CRLF); the lines go after the last key of the section, before the comment
    block that introduces the next section."""
    m = re.search(r"(?m)^\[%s\]\r\n(.*?)(?=^\[|\Z)" % re.escape(section), text, re.S)
    if not m:
        raise SystemExit("section %s not found" % section)
    lines = m.group(1).split(CRLF)
    lines = [l for l in lines if not re.match(r"\s*condlist_\d+", l)]
    last = -1
    for i, l in enumerate(lines):
        if l.strip() and not l.lstrip().startswith(";"):
            last = i
    add = ["condlist_%d" % i + TABS + "= " + c for i, c in enumerate(conds)]
    lines[last + 1:last + 1] = add
    return text[:m.start(1)] + CRLF.join(lines) + text[m.end(1):]


def build_pripyat(src):
    t = open(src, "rb").read().decode("utf-8")
    t = set_conds(t, "pri_start_go_to_cnpp_quest_task",
                  ["{+PRI_START_GO_TO_CNPP_QUEST_TASK_INFO} complete %=give_task(aes_1_start_go_to_sarcofag_quest_task)%",
                   "{+AES_1_START_GO_TO_SARCOFAG_QUEST_TASK_INFO} complete", "{+SOC_AES_SAR_ARRIVED} complete"])
    t = set_conds(t, "pri_start_meet_a_group_of_stalkers_quest_task",
                  ["{+PRI_SMART_TERRAIN_1_WALKER_LEADER_IDLE_INFO} complete",
                   "{+PRI_START_GO_TO_CNPP_QUEST_TASK_INFO} complete", "{+SOC_AES_CNPP_ARRIVED} complete"])
    t = set_conds(t, "pri_start_help_the_stalkers_get_to_the_underground_parking_quest_task",
                  ["{+PRI_SMART_TERRAIN_19_ORDINARY_MONOLITH_1_SQUAD_DEAD +PRI_SMART_TERRAIN_19_ORDINARY_MONOLITH_2_SQUAD_DEAD} complete",
                   "{+PRI_START_GO_TO_CNPP_QUEST_TASK_INFO} complete", "{+SOC_AES_CNPP_ARRIVED} complete"])
    icon = "ui_inGame2_pri_start_go_to_cnpp_quest_task"
    new = ["", "; soc_aes_quests: SoC cit_doctor_task \"Secret stash at Pripyat\" (tasks_deadcity.xml): hotel, the room, the stash with the decoder.",
           "; Given by coop_soc_aes.script when the party is on Pripyat; fails when the party has left for CNPP-1 without the decoder (the Sarcophagus then has its own copy).", ""]
    stash = lambda n, descr, conds: sect("pri_soc_stash_%d_task" % n, icon, 150, "st_pri_soc_stash_name", descr, "nil", conds)
    fail = "{+PRI_START_GO_TO_CNPP_QUEST_TASK_INFO} fail"
    fail2 = "{+SOC_AES_CNPP_ARRIVED} fail"
    new.append(stash(1, "st_pri_soc_stash_1_descr", ["{+PRI_ACTOR_IN_HOTEL} complete", "{+PRI_ACTOR_IN_HIDING_PLACE} complete", "{+PRI_MONOLITH_DECODER_GOT} complete", fail, fail2]))
    new.append("")
    new.append(stash(2, "st_pri_soc_stash_2_descr", ["{+PRI_ACTOR_IN_HIDING_PLACE} complete", "{+PRI_MONOLITH_DECODER_GOT} complete", fail, fail2]))
    new.append("")
    new.append(stash(3, "st_pri_soc_stash_3_descr", ["{+PRI_MONOLITH_DECODER_GOT} complete", fail, fail2]))
    t = t.rstrip("\r\n") + "\r\n" + "\r\n".join(new) + "\r\n"
    return t.encode("utf-8")


def build_control(src):
    t = open(src, "rb").read().decode("utf-8")
    t = set_conds(t, "con_start_destroy_the_monolith_installation_1_quest_task",
                  ["{+CON_MONOLITH_GENERATOR_1_INFO +CON_MONOLITH_GENERATOR_2_INFO +CON_MONOLITH_GENERATOR_3_INFO +CON_MONOLITH_GENERATOR_4_INFO "
                   "+CON_MONOLITH_GENERATOR_5_INFO +CON_MONOLITH_GENERATOR_6_INFO} complete"])
    t = set_conds(t, "con_start_talk_to_the_representative_awareness_quest_task",
                  ["{+CON_SMART_TERRAIN_13_ECOLOG_REPRESENTATIVE_AWARENESS_6_DIALOG_STOP_INFO} complete"])
    t = t.rstrip("\r\n") + "\r\n\r\n; soc_aes_quests: the five other generator steps and the kill-all-representatives step are hidden (configs\\misc\\coop_hidden_tasks.ltx);\r\n" \
        "; SoC has ONE objective \"Solve the Monolith's secret\" (done when all six generators are down) and only TALKS to C-Consciousness.\r\n"
    return t.encode("utf-8")


def edit_sarcofag():
    raw = open(SARC, "rb").read()
    if MARK in raw:
        return None
    t = raw.decode("utf-8")
    t = set_conds(t, "sar_start_get_to_the_monolith_quest_task",
                  ["{+SAR_MONOLITH_WISH_SPACE_RESTRICTOR_INFO} complete", "{+SAR_ENTER_COMMAND_CENTER} complete"])
    t = set_conds(t, "sar_start_open_the_door_to_monolith_management_quest_task",
                  ["{+LOCKED_START_OPEN_INFO} complete", "{+SAR_ENTER_COMMAND_CENTER} complete"])
    icon_w = "ui_inGame2_sar_start_get_to_the_monolith_quest_task"
    icon_l = "ui_inGame2_sar_start_open_the_door_to_monolith_management_quest_task"
    new = ["", MARK.decode() + ": SoC sar_monolith (tasks_sarcofag.xml): objective 0 is sar_start_get_to_the_monolith_quest_task above (open until the Wish Granter is reached),",
           "; objectives 1 and 2 follow. The Preacher steps and the decoder search step above are hidden (the decoder comes from the Pripyat hotel stash, coop_soc_aes.script).", ""]
    new.append(sect("sar_soc_sneak_in_task", icon_w, 200, "st_sar_soc_wish_name", "st_sar_soc_sneak_in_descr", "nil",
                    ["{+SAR_MONOLITH_FIND} complete", "{+SAR_MONOLITH_WISH_SPACE_RESTRICTOR_INFO} complete", "{+SAR_ENTER_COMMAND_CENTER} complete"]))
    new.append("")
    new.append(sect("sar_soc_find_wish_task", icon_w, 200, "st_sar_soc_wish_name", "st_sar_soc_find_wish_descr", "sar_monolith",
                    ["{+SAR_MONOLITH_WISH_SPACE_RESTRICTOR_INFO} complete", "{+SAR_ENTER_COMMAND_CENTER} complete"]))
    new.append("")
    new.append("; SoC sar_secret_lab: 1 enter the secret bunker (+ the Doctor's briefing), 2 find the hidden door, 3 open it using the decoder (sar_start_open_the_door... above),")
    new.append("; 4 find out what is behind the door (until the party is on the Control Monolith level)")
    new.append(sect("sar_soc_lab_1_task", icon_l, 200, "st_sar_soc_lab_name", "st_sar_soc_lab_1_descr", "nil",
                    ["{+SAR_SOC_BUNKER} complete", "{+SAR_SECRET_DOOR_FIND} complete", "{+LOCKED_START_OPEN_INFO} complete", "{+SAR_ENTER_COMMAND_CENTER} complete"]))
    new.append("")
    new.append(sect("sar_soc_lab_2_task", icon_l, 200, "st_sar_soc_lab_name", "st_sar_soc_lab_2_descr", "sar_codedoor_left_decoder",
                    ["{+SAR_SECRET_DOOR_FIND} complete", "{+LOCKED_START_OPEN_INFO} complete", "{+SAR_ENTER_COMMAND_CENTER} complete"]))
    new.append("")
    new.append(sect("sar_soc_lab_4_task", icon_l, 200, "st_sar_soc_lab_name", "st_sar_soc_lab_4_descr", "sar_codedoor_left_decoder",
                    ["{+SAR_ENTER_COMMAND_CENTER} complete"]))
    t = t.rstrip("\r\n") + "\r\n" + "\r\n".join(new) + "\r\n"
    return t.encode("utf-8")


def write(path, data):
    if os.path.isfile(path) and open(path, "rb").read() == data:
        print("unchanged " + os.path.relpath(path, REPO_PATCHES))
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print("written   " + os.path.relpath(path, REPO_PATCHES))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    write(os.path.join(GD, "tm_coop_l10_pripyat.ltx"), build_pripyat(os.path.join(src, "tm_coop_l10_pripyat.ltx")))
    write(os.path.join(GD, "tm_coop_l11_control_monolith.ltx"), build_control(os.path.join(src, "tm_coop_l11_control_monolith.ltx")))
    data = edit_sarcofag()
    if data is None:
        print("unchanged " + os.path.relpath(SARC, REPO_PATCHES) + " (already edited)")
    else:
        write(SARC, data)


if __name__ == "__main__":
    main()
