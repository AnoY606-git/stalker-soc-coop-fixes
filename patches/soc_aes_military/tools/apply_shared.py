"""Changes to files that other patches / the installer ship (this patch adds only its own files). Idempotent: a second run changes nothing.

  python -I patches\\soc_aes_military\\tools\\apply_shared.py <repo root>

Run it AFTER the release zip is built (the coordinator does that); the patch works without it, only the change list and two NOTES would then still say
"Operation Monolith is not in the mod".
  1. installer\\changes_1.4*.en.txt / changes_1.4*.ru.txt (every change list that has the soc_aes_quests line: changes_1.4 and changes_1.4.1 today;
     a list without that line is left alone): the soc_aes_quests entry loses its last sentence ("Not in the mod: Operation Monolith ..."), and a new
     entry @soc_aes_military follows it (dropped by release.py when soc_aes_military is in --skip)
  2. patches\\soc_aes_quests\\NOTES.md: the three places that say the task was not added
Files are edited as bytes (BOM, line endings and everything else stay as they are). Exit 1 when an expected text is missing and not already changed.
"""
import os
import sys

root = sys.argv[1] if len(sys.argv) > 1 else '.'

EN_OLD = ' Not in the mod: "Operation Monolith" (there are no assault army squads).'
RU_OLD = ' Нет в моде: "Операция Монолит" (нет военных отрядов штурма).'

EN_NEW = ('- @soc_aes_military: "Operation Monolith" from the original on the power plant level (CNPP-1). The military action plan (the "Situation" article) is found '
          'where the wounded soldier lay in the original, at the entrance. After that every player gets the task "Operation Monolith" with the original steps (the gate, '
          'the two Monolith fortifications, break through to the sarcophagus) and map markers on the gate, the fortifications, the sarcophagus and the army groups Sapsan, '
          'Korshun, Yastreb, Pustelga, Sokol, Grif, Sova and Lun (the army squads the mod already has on that level). The original radio reports of the battle play along '
          'the road (the original voice lines, in English or Russian like the voice language of the player, played for each player when he reaches the place). '
          'The task is done at the sarcophagus and never blocks the way')
RU_NEW = ('- @soc_aes_military: "Операция Монолит" из оригинала на уровне ЧАЭС (ЧАЭС-1). План действий военных (запись "Обстановка") находится там, где в оригинале лежал '
          'раненый солдат у входа. После этого каждый игрок получает задание "Операция Монолит" с шагами оригинала (ворота, два укрепления Монолита, прорваться к саркофагу) '
          'и метками на воротах, укреплениях, саркофаге и группах "Сапсан", "Коршун", "Ястреб", "Пустельга", "Сокол", "Гриф", "Сова" и "Лунь" (отряды армии, которые '
          'уже есть в моде на этом уровне). По дороге звучат оригинальные радиопереговоры боя (оригинальные реплики на английском или русском, как в настройке голоса '
          'игрока, каждому игроку, когда он доходит до места). '
          'Задание выполняется у саркофага и никогда не мешает пройти')

problems = []


def edit(rel, fn):
    p = os.path.join(root, *rel.split('/'))
    if not os.path.isfile(p):
        problems.append('missing file ' + rel)
        return
    raw = open(p, 'rb').read()
    new = fn(raw)
    if new is None:
        problems.append('expected text not found in ' + rel)
    elif new != raw:
        open(p, 'wb').write(new)
        print('changed', rel)
    else:
        print('already done', rel)


def changes(old, entry):
    def fn(raw):
        text = raw.decode('utf-8')
        nl = '\r\n' if '\r\n' in text else '\n'
        lines = text.split(nl)
        idx = [i for i, l in enumerate(lines) if l.startswith('- @soc_aes_quests,')]
        if len(idx) != 1:
            return None
        i = idx[0]
        if old in lines[i]:
            lines[i] = lines[i].replace(old, '')
        has_mine = any(l.startswith('- @soc_aes_military:') for l in lines)
        if has_mine:
            lines = [entry if l.startswith('- @soc_aes_military:') else l for l in lines]
        else:
            lines.insert(i + 1, entry)
        return nl.join(lines).encode('utf-8')
    return fn


def has_aes_line(rel):
    p = os.path.join(root, *rel.split('/'))
    return os.path.isfile(p) and any(l.startswith('- @soc_aes_quests,') for l in open(p, 'rb').read().decode('utf-8').splitlines())


lists = 0
for lang, entry_old, entry_new in (('en', EN_OLD, EN_NEW), ('ru', RU_OLD, RU_NEW)):
    d = os.path.join(root, 'installer')
    names = sorted(f for f in os.listdir(d) if f.startswith('changes_1.4') and f.endswith('.' + lang + '.txt')) if os.path.isdir(d) else []
    for f in names:
        rel = 'installer/' + f
        if has_aes_line(rel):
            edit(rel, changes(entry_old, entry_new))
            lists += 1
        else:
            print('skipped (no soc_aes_quests line)', rel)
if lists == 0:
    problems.append('no installer/changes_1.4*.txt with a soc_aes_quests line found')

# ---- soc_aes_quests NOTES.md
N_ROW_OLD = '| 8 | no "Operation Monolith" | NOT added: the mod\'s CNPP levels have no military squads (only dead soldiers and loot boxes), the task has 12 objectives about their groups |'
N_ROW_NEW = ('| 8 | no "Operation Monolith" | added by patch `soc_aes_military` (the mod DOES have 12 army squads on CNPP-1, created by its spawn restrictors; that patch adds the plan, the task, '
             'the markers on the groups and the SoC radio) |')
N_LIM_OLD = '- "Operation Monolith" (`aes_military_task`): no military squads exist on the mod\'s CNPP levels.'
N_LIM_NEW = '- "Operation Monolith" (`aes_military_task`): patch `soc_aes_military` (the army squads exist on CNPP-1).'
N_RU_OLD = ' Не сделано: "Операция Монолит" (в моде нет военных отрядов штурма).'
N_RU_NEW = ' "Операция Монолит" сделана в патче `soc_aes_military` (отряды армии на ЧАЭС-1 в моде есть).'


def notes(raw):
    text = raw.decode('utf-8')
    done = 0
    for old, new in ((N_ROW_OLD, N_ROW_NEW), (N_LIM_OLD, N_LIM_NEW), (N_RU_OLD, N_RU_NEW)):
        if old in text:
            text = text.replace(old, new)
            done += 1
        elif new in text:
            done += 1
    if done != 3:
        return None
    return text.encode('utf-8')


edit('patches/soc_aes_quests/NOTES.md', notes)

if problems:
    for p in problems:
        print('PROBLEM', p)
    sys.exit(1)
