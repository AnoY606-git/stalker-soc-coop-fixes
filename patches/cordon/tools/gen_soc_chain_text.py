"""Make configs\\text\\eng|rus\\st_cordon_soc_chain.xml (windows-1251) from the ORIGINAL Shadow of Chernobyl strings.

  python gen_soc_chain_text.py <steam soc extract dir> <port rus st_soc_strings.xml> <out gamedata\\configs\\text>

<steam soc extract dir>  = xdb_soc.py extraction of config\\text\\eng\\*.xml of the Steam install (English SoC, windows-1251)
<port rus st_soc_strings.xml> = Russian SoC strings (soc_ai_port\\extracted\\src\\...\\configs\\text\\rus\\st_soc_strings.xml)
Every id of the new chain is a SoC id (escape_trader_jobs_*, esc_bridge_soldiers_start_*, task strings) under a coop_soc_* name.
Lines marked COMPOSED are built from SoC lines (no single SoC string exists); they are written here in both languages.
"""
import os
import re
import sys

steam, rus_file, out = sys.argv[1], sys.argv[2], sys.argv[3]


def load(path, enc):
    raw = open(path, 'rb').read()
    try:
        t = raw.decode('utf-8') if enc == 'utf8' else raw.decode('cp1251')
    except UnicodeDecodeError:
        t = raw.decode('cp1251', errors='replace')
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'<string id="([^"]*)">\s*<text>(.*?)</text>', t, re.S)}


ENG = {}
for dp, dn, fn in os.walk(os.path.join(steam, 'config', 'text', 'eng')):
    for f in fn:
        if f.endswith('.xml'):
            ENG.update(load(os.path.join(dp, f), 'cp1251'))
RUS = load(rus_file, 'utf8')

# new id -> SoC id
MAP = {
    # Sidorovich, SoC escape_trader_jobs: 0 (actor), 6, 61 ... 611111111 (the military case: Agroprom documents)
    'coop_soc_job_0': 'escape_trader_jobs_0',
    'coop_soc_job_1': 'escape_trader_jobs_6',
    'coop_soc_job_2': 'escape_trader_jobs_61',
    'coop_soc_job_3': 'escape_trader_jobs_611',
    'coop_soc_job_4': 'escape_trader_jobs_6111',
    'coop_soc_job_5': 'escape_trader_jobs_61111',
    'coop_soc_job_6': 'escape_trader_jobs_611111',
    'coop_soc_job_7': 'escape_trader_jobs_6111111',
    'coop_soc_job_8': 'escape_trader_jobs_61111111',
    'coop_soc_job_9': 'escape_trader_jobs_611111111',
    # bridge soldiers, SoC esc_bridge_soldiers_start
    'coop_soc_bridge_11': 'esc_bridge_soldiers_start_11',
    'coop_soc_bridge_12': 'esc_bridge_soldiers_start_12',
    'coop_soc_bridge_13': 'esc_bridge_soldiers_start_13',
    'coop_soc_bridge_14': 'esc_bridge_soldiers_start_14',
    'coop_soc_bridge_15': 'esc_bridge_soldiers_start_15',
    'coop_soc_bridge_21': 'esc_bridge_soldiers_start_21',
    'coop_soc_bridge_24': 'esc_bridge_soldiers_start_24',
    'coop_soc_bridge_25': 'esc_bridge_soldiers_start_25',
    # SoC task strings
    'coop_soc_task_trader_job_name': 'esc_trader_job',
    'coop_soc_task_trader_job_descr': 'esc_trader_job_text',
    'coop_soc_task_railroad_name': 'find_railroad_passage',
    'coop_soc_task_railroad_descr': 'find_railroad_passage_text',
    'coop_soc_task_documents_name': 'agroprom_get_military_documents',
}

# COMPOSED: the SoC task has three one-line stages (_0 institute, _1 steal the documents, _2 take them to the Barkeep): one description
COMPOSED = {
    'coop_soc_task_documents_descr': {
        'eng': "Agroprom Research Institute: steal the militaries' documents, then take them to the Barkeep.",
        'rus': "НИИ Агропром: выкрасть военные документы, затем отнести документы бармену.",
    },
    # the pass is paid with money, not vodka (original SoC bridge dialog: 500). The task is hidden (SoC has no task for it), see NOTES.md
    'coop_soc_task_pass_name': {
        'eng': 'Pass the army outpost',
        'rus': "Пройти блокпост",
    },
    'coop_soc_task_pass_descr': {
        'eng': "To get past the army outpost at the railway bridge we have to give Major Kuznetsov 500 rubles.",
        'rus': "Чтобы пройти через блокпост у железнодорожного моста, нужно отдать майору Кузнецову 500 рублей.",
    },
}

for lang, src in (('eng', ENG), ('rus', RUS)):
    lines = ['<?xml version="1.0" encoding="windows-1251"?>', '<string_table>']
    for new, old in MAP.items():
        if old not in src:
            sys.exit('missing SoC string %s (%s)' % (old, lang))
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, src[old]))
    for new, d in COMPOSED.items():
        lines.append('\t<string id="%s"><text>%s</text></string>' % (new, d[lang]))
    lines.append('</string_table>')
    txt = '\r\n'.join(lines) + '\r\n'
    assert '—' not in txt, 'em dash'
    d = os.path.join(out, lang)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'st_cordon_soc_chain.xml'), 'wb') as f:
        f.write(txt.encode('cp1251'))
    print(lang, len(MAP) + len(COMPOSED), 'strings')
