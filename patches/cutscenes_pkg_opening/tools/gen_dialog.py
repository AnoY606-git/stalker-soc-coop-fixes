"""Apply the SoC opening dialog to dialogs_coop_l01_escape.xml.
usage: gen_dialog.py <in.xml> <out.xml>
Replaces the Sidorovich start dialog (NPC greeting) by the original SoC escape_trader_start_dialog structure:
  new game (flag COOP_SOC_OPENING_TALKED missing): SoC phrase 3, only the experienced answer 32, then 321 / 3211 / 32111 / 321111.
  afterwards: the mod's usual greeting.
"""
import sys, re

src, dst = sys.argv[1], sys.argv[2]
t = open(src, "rb").read().decode("cp1251")

old_start = re.search(r'    <dialog id="esc_smart_terrain_1_trader_sidorovich_start_dialog">.*?</dialog>\r?\n', t, re.S)
assert old_start, "start dialog not found"

NL = "\r\n"
new_start = NL.join([
    '    <dialog id="esc_smart_terrain_1_trader_sidorovich_start_dialog">',
    '        <phrase_list>',
    '            <phrase id="0">',
    '                <text />',
    '                <next>10</next>',
    '                <next>20</next>',
    '            </phrase>',
    '            <!-- original SoC escape_trader_start_dialog: phrase 3 (the choice), only the experienced branch 32 -->',
    '            <phrase id="10">',
    '                <text />',
    '                <dont_has_flag>COOP_SOC_OPENING_TALKED</dont_has_flag>',
    '                <next>3</next>',
    '            </phrase>',
    '            <phrase id="3">',
    '                <action>coop_soc_opening.say_3</action>',
    '                <text>coop_soc_open_3</text>',
    '                <next>32</next>',
    '            </phrase>',
    '            <phrase id="32">',
    '                <action>coop_soc_opening.say_32</action>',
    '                <text>coop_soc_open_32</text>',
    '                <next>321</next>',
    '            </phrase>',
    '            <phrase id="321">',
    '                <action>coop_soc_opening.say_321</action>',
    '                <text>coop_soc_open_321</text>',
    '                <give_flag>COOP_SOC_OPENING_TALKED</give_flag>',
    '                <give_flag>ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO</give_flag>',
    '                <give_flag>ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_TALK_TO_THE_WOLF_STOP_DIALOG_INFO</give_flag>',
    '                <next>3211</next>',
    '            </phrase>',
    '            <phrase id="3211">',
    '                <action>coop_soc_opening.say_3211</action>',
    '                <text>coop_soc_open_3211</text>',
    '                <next>32111</next>',
    '            </phrase>',
    '            <phrase id="32111">',
    '                <action>coop_soc_opening.say_32111</action>',
    '                <text>coop_soc_open_32111</text>',
    '                <next>321111</next>',
    '            </phrase>',
    '            <phrase id="321111">',
    '                <action>coop_soc_opening.say_321111</action>',
    '                <text>coop_soc_open_321111</text>',
    '                <action>dialogs.break_dialog</action>',
    '            </phrase>',
    '            <!-- after the opening: the mod\'s usual greeting -->',
    '            <phrase id="20">',
    '                <text />',
    '                <has_flag>COOP_SOC_OPENING_TALKED</has_flag>',
    '                <next>21</next>',
    '            </phrase>',
    '            <phrase id="21">',
    '                <action>coop_pda_phrases.say__esc_smart_terrain_1_trader_sidorovich_start_dialog_0</action>',
    '                <text>esc_smart_terrain_1_trader_sidorovich_start_dialog_0</text>',
    '            </phrase>',
    '        </phrase_list>',
    '    </dialog>',
    ''])
t = t[:old_start.start()] + new_start + t[old_start.end():]
open(dst, "wb").write(t.encode("cp1251"))
print("wrote", dst, len(t))
