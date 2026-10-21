"""Writes the three XML files of patch soc_doctor_chain (windows-1251 header, ASCII content, CRLF). Idempotent.
  gamedata\configs\gameplay\dialogs_coop_soc_doctor.xml          the Guide topic and the Doctor's greeting / talk (SoC esc_provodnik_start, cit_doctor_hello_dialog, cit_doctor_main_dialog)
  gamedata\configs\gameplay\npc_profile_soc_doctor.xml           the profile (character id soc_cit_doctor)
  gamedata\configs\gameplay\character_desc_coop_soc_doctor.xml   the specific character (the SoC Doctor: model actors\stalker_mp\stalker_doctor, the same skin the SoC Doctor has)
"""
import os

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), 'gamedata', 'configs', 'gameplay')


def phrase(pid, text, action=None, nexts=(), pre=None, flags=()):
    s = ['            <phrase id="%s">' % pid]
    if action:
        s.append('                <action>%s</action>' % action)
    s.append('                <text%s' % (' />' if text is None else '>%s</text>' % text))
    if pre:
        s.append('                <precondition>%s</precondition>' % pre)
    for f in flags:
        if f == 'BREAK':
            s.append('                <action>dialogs.break_dialog</action>')
        else:
            s.append('                <give_flag>%s</give_flag>' % f)
    for n in nexts:
        s.append('                <next>%s</next>' % n)
    s.append('            </phrase>')
    return '\n'.join(s)


D = ['<?xml version="1.0" encoding="windows-1251" ?>', '<game_dialogs>']

# ---- the Guide (Cordon): SoC esc_provodnik_start branch 12 to 16 (the Guide's greeting 11 is the mod's own start dialog)
D.append('    <!-- SoC esc_provodnik_start, branch 12 to 16: the topic is offered once Ghost\'s documents are taken and until the Guide has spoken -->')
D.append('    <dialog id="soc_doc_guide_dialog">')
D.append('        <precondition>coop_soc_doctor.st_g_open</precondition>')
D.append('        <phrase_list>')
D.append(phrase('0', 'coop_soc_doc_g_0', 'coop_soc_doctor.say_g0', ['1']))
D.append(phrase('1', 'coop_soc_doc_g_1', 'coop_soc_doctor.say_g1', ['2']))
D.append(phrase('2', 'coop_soc_doc_g_2', 'coop_soc_doctor.say_g2', ['3']))
D.append(phrase('3', 'coop_soc_doc_g_3', 'coop_soc_doctor.say_g3', ['4'], flags=['ESC_FIND_DOCTOR_START']))
D.append(phrase('4', 'coop_soc_doc_g_4', 'coop_soc_doctor.say_g4', flags=['BREAK']))
D.append('        </phrase_list>')
D.append('    </dialog>')

# ---- the Doctor: greeting (NPC first), SoC cit_doctor_hello_dialog
D.append('    <!-- SoC cit_doctor_hello_dialog: first meeting / after the talk -->')
D.append('    <dialog id="soc_doc_hello_dialog">')
D.append('        <phrase_list>')
D.append(phrase('0', None, nexts=['1', '2']))
D.append(phrase('1', None, nexts=['11'], pre='coop_soc_doctor.st_h_first'))
D.append(phrase('11', 'coop_soc_doc_d_h11', 'coop_soc_doctor.say_dh11'))
D.append(phrase('2', None, nexts=['21'], pre='coop_soc_doctor.st_h_after'))
D.append(phrase('21', 'coop_soc_doc_d_h21', 'coop_soc_doctor.say_dh21'))
D.append('        </phrase_list>')
D.append('    </dialog>')

# ---- the Doctor: the talk, SoC cit_doctor_main_dialog (phrases 0 to 4; 41 and 5 say "we are in the Dead City, the Merc camp" and are not used)
D.append('    <!-- SoC cit_doctor_main_dialog 0 to 4 (41 and 5 answer "where are we": the Dead City jail, which the mod does not have). Gives the stash task and the diary text -->')
D.append('    <dialog id="soc_doc_main_dialog">')
D.append('        <precondition>coop_soc_doctor.st_d_open</precondition>')
D.append('        <phrase_list>')
for pid, nxt, flags in (('0', '1', ()), ('1', '11', ()), ('11', '2', ()), ('2', '21', ()), ('21', '3', ()), ('3', '31', ()), ('31', '4', ()),
                        ('4', None, ('CIT_JAIL_DOCTOR_PRYP_TASK', 'CIT_DOCTOR_MEET_CONCLUSION_INFO'))):
    D.append(phrase(pid, 'coop_soc_doc_d_' + pid, 'coop_soc_doctor.say_d' + pid, [nxt] if nxt else [], flags=flags))
D.append('        </phrase_list>')
D.append('    </dialog>')
D.append('</game_dialogs>')

P = ['<?xml version=\'1.0\' encoding="windows-1251"?>', '<xml>',
     '\t<!-- soc_doctor_chain: the Doctor of the original SoC (profile id used by the spawn section soc_cit_doctor) -->',
     '\t<character id="soc_cit_doctor">', '\t\t<class>soc_cit_doctor</class>', '\t</character>', '</xml>']

C = ['<?xml version=\'1.0\' encoding="windows-1251"?>', '<xml>',
     '<!-- soc_doctor_chain: SoC cit_doctor (Strelok\'s friend). Same model as the SoC Doctor (the mod has it as actors\stalker_mp\stalker_doctor). -->',
     '<specific_character id="soc_cit_doctor" team_default = "1">',
     '    <name>coop_soc_doc_name</name>',
     '    <icon>ui_inGame2_neutral_0_3</icon>',
     '    <map_icon x="0" y="0"></map_icon>',
     '    <bio>coop_soc_doc_bio</bio>',
     '    <class>soc_cit_doctor</class>',
     '    <community>stalker</community> <terrain_sect>stalker_terrain</terrain_sect>',
     '    <money min="1000" max="2000" infinitive="0"></money>',
     '    <rank>859</rank>',
     '    <reputation>145</reputation>',
     '    <visual>actors\stalker_mp\stalker_doctor</visual>',
     '    <snd_config>characters_voice\human_02\stalker\</snd_config>',
     '    <crouch_type>-1</crouch_type>',
     '    <supplies>',
     '        [spawn] \n',
     '    </supplies>',
     '#include "gameplay\character_criticals_4.xml"',
     '    <start_dialog>soc_doc_hello_dialog</start_dialog>',
     '    <actor_dialog>soc_doc_main_dialog</actor_dialog>',
     '    <actor_dialog>actor_break_dialog</actor_dialog>',
     '</specific_character>', '</xml>']

for name, lines in (('dialogs_coop_soc_doctor.xml', D), ('npc_profile_soc_doctor.xml', P), ('character_desc_coop_soc_doctor.xml', C)):
    txt = '\r\n'.join(lines) + '\r\n'
    assert all(ord(c) < 128 for c in txt), name
    with open(os.path.join(out, name), 'wb') as f:
        f.write(txt.encode('ascii'))
    print('wrote', name)
