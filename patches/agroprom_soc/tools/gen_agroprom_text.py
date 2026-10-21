"""Makes the text files of patch agroprom_soc (cp1251 xml, eng + rus).

  python gen_agroprom_text.py <mod gamedata.db0 folder> <patch gamedata folder>

SoC wording: tools\\soc_agr_strings.json = the Steam SoC 1.0006 English string tables and the SoC Russian string table (st_soc_strings.xml of the
SoC add-on), ids as in SoC. Written files:
  configs\\text\\<lang>\\st_agroprom_soc_chain.xml        new ids of the tasks SoC has and the mod had not (help the stalkers, Ghost, the flash drive step)
  configs\\text\\<lang>\\st_dialogs_coop_l03_agroprom.xml  the mod's file, only the six Mole lines changed to the SoC dialog "agr_factory_krot_start"
                                                          (same string ids: the dialog and the PDA archive functions stay as they are)
"""
import json
import os
import re
import sys

mod, out = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, 'soc_agr_strings.json'), encoding='utf-8'))
# "found our" is a typo of the original English string
S['agr_find_ghost_descr']['eng'] = S['agr_find_ghost_descr']['eng'].replace('found our that', 'found out that')
ENC = {'eng': 'cp1251', 'rus': 'cp1251'}


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def wr(lang, name, text):
    p = os.path.join(out, 'configs', 'text', lang, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(text.encode(ENC[lang]))
    print('wrote', lang, name, len(text))


def L(lang, k):
    return S[k][lang]


for lang in ('eng', 'rus'):
    # new task strings: "objective text\n\nbriefing" like the phase 1 texts (patch soc_task_texts)
    rows = [
        ('coop_soc_agr_help_stalkers_name', L(lang, 'agr_help_stalkers')),
        ('coop_soc_agr_help_stalkers_descr', L(lang, 'agr_help_stalkers_0') + '\\n\\n' + L(lang, 'article_agr_krot_sos')),
        ('coop_soc_agr_ghost_name', L(lang, 'agr_find_ghost')),
        ('coop_soc_agr_ghost_descr', L(lang, 'agr_find_ghost') + '\\n\\n' + L(lang, 'agr_find_ghost_descr')),
        ('coop_soc_agru_flash_descr', L(lang, 'agroprom_find_gunslinger_cache_2')),
    ]
    x = '<?xml version="1.0" encoding="windows-1251" ?>\r\n<string_table>\r\n'
    for k, v in rows:
        x += '\t<string id="%s">\r\n\t\t<text>%s</text>\r\n\t</string>\r\n' % (k, esc(v))
    x += '</string_table>\r\n'
    wr(lang, 'st_agroprom_soc_chain.xml', x)

    # the Mole dialog: SoC agr_factory_krot_start, the "Seriy sent me" branch (the only branch the mod has: the group comes from Seriy)
    base = open(os.path.join(mod, 'configs', 'text', lang, 'st_dialogs_coop_l03_agroprom.xml'), 'rb').read().decode(ENC[lang])
    repl = {
        'agr_smart_terrain_7_stalker_mole_start_dialog_0': 'agr_factory_krot_start_0',                      # Mole: thanks
        'agr_smart_terrain_7_stalker_mole_talk_to_the_stalker_mole_0': 'agr_factory_krot_start_2',          # actor: looking for info on Strelok, Seriy sent me
        'agr_smart_terrain_7_stalker_mole_talk_to_the_stalker_mole_1': 'agr_krot_actor_met_seriy_100',      # Mole: the stash is below, I give you the info
        'agr_smart_terrain_7_stalker_mole_talk_to_the_stalker_mole_2': 'agr_factory_krot_start_10002',      # actor: how do I get into the basement
        'agr_smart_terrain_7_stalker_mole_talk_to_the_stalker_mole_3': 'agr_factory_krot_start_1502',       # Mole: one of the many entrances
        'agr_smart_terrain_7_stalker_mole_talk_to_the_stalker_mole_4': 'agr_factory_krot_start_15002',      # actor: thanks for the information
    }
    for mid, sid in repl.items():
        pat = re.compile(r'(<string id="' + re.escape(mid) + r'">\s*<text>)(.*?)(</text>)', re.S)
        assert pat.search(base), mid
        base = pat.sub(lambda m: m.group(1) + esc(L(lang, sid)) + m.group(3), base, count=1)
    wr(lang, 'st_dialogs_coop_l03_agroprom.xml', base)
