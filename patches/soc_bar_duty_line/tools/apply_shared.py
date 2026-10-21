"""Changes of patch soc_bar_duty_line to files that OTHER patches ship (idempotent; bytes are edited, nothing else is touched).
  python apply_shared.py [--repo DIR]        DIR = a tree with patches\\... and installer\\... (default: this repo). The coordinator runs it AFTER the zip.

  1. patches\\repeatable_quests\\gamedata\\configs\\system.ltx       registers dialogs_coop_soc_duty, character_desc_coop_soc_duty, npc_profile_coop_soc_duty
  2. patches\\repeatable_quests\\gamedata\\configs\\misc\\task_manager.ltx   #include "tm_coop_soc_duty.ltx"
  3. patches\\repeatable_quests\\gamedata\\configs\\gameplay\\character_desc_coop_l05_bar.xml   Voronin / Petrenko start with the SoC dialogs, Voronin and
     the Barkeep get the actor dialogs of the Duty line (the mod's own Voronin / Petrenko start dialogs stay in the dialog file, unused)
  4. installer\\changes_1.4.en.txt / .ru.txt     the change line of this patch; the sentence of the bar_soc_quests line that says the Duty / Freedom
     quests are not in the mod is shortened
  5. patches\\bar_soc_quests\\NOTES.md            a pointer under "The Duty / Freedom line"
"""
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import duty_model as M

repo = os.path.dirname(os.path.dirname(os.path.dirname(here)))
if '--repo' in sys.argv:
    repo = os.path.abspath(sys.argv[sys.argv.index('--repo') + 1])
P = lambda *a: os.path.join(repo, *a)
changed = []


def rw(path, fn):
    data = open(path, 'rb').read()
    new = fn(data)
    if new != data:
        open(path, 'wb').write(new)
        changed.append(os.path.relpath(path, repo))


# ---- 1. system.ltx: append names to three list lines
def add_to_list(data, key_regex, name):
    """append `, name` to the first line matching key_regex (bytes) unless the name is already in it"""
    m = re.search(key_regex, data, re.M)
    if m is None:
        sys.exit('system.ltx: line not found: ' + key_regex.decode())
    line = m.group(0)
    if re.search(rb'(^|[=,\s])' + re.escape(name.encode()) + rb'(\s*,|\s*$|\s*\r?$)', line.rstrip(b'\r\n')):
        return data
    stripped = line.rstrip(b'\r\n')
    tail = line[len(stripped):]
    return data[:m.start()] + stripped.rstrip() + b', ' + name.encode() + tail + data[m.end():]


def system(data):
    data = add_to_list(data, rb'^files\s*=\s*dialogs,[^\r\n]*', 'dialogs_coop_soc_duty')
    data = add_to_list(data, rb'^specific_characters_files\s*=[^\r\n]*', 'character_desc_coop_soc_duty')
    data = add_to_list(data, rb'^files\s*=\s*npc_profile,[^\r\n]*', 'npc_profile_coop_soc_duty')
    return data


rw(P('patches', 'repeatable_quests', 'gamedata', 'configs', 'system.ltx'), system)


# ---- 2. task_manager.ltx
def taskman(data):
    inc = b'#include "tm_coop_soc_duty.ltx"'
    if inc in data:
        return data
    nl = b'\r\n' if b'\r\n' in data else b'\n'
    anchor = b'#include "tm_coop_repeat.ltx"'
    i = data.find(anchor)
    if i < 0:
        anchor = b'#include "tm_coop_l11_stancia_1.ltx"'
        i = data.find(anchor)
    if i < 0:
        sys.exit('task_manager.ltx: anchor not found')
    j = i + len(anchor)
    return data[:j] + nl + inc + data[j:]


rw(P('patches', 'repeatable_quests', 'gamedata', 'configs', 'misc', 'task_manager.ltx'), taskman)

# ---- 3. character_desc_coop_l05_bar.xml


def chars(data):
    for cid, (start, acts) in M.SHARED_CHARACTERS.items():
        m = re.search(rb'<specific_character id="' + cid.encode() + rb'".*?</specific_character>', data, re.S)
        if m is None:
            sys.exit('character %s not found' % cid)
        blk = m.group(0)
        nl = b'\r\n' if b'\r\n' in blk else b'\n'
        if start is not None:
            blk = re.sub(rb'<start_dialog>[^<]*</start_dialog>', b'<start_dialog>' + start.encode() + b'</start_dialog>', blk, count=1)
        for a in acts:
            tag = b'<actor_dialog>' + a.encode() + b'</actor_dialog>'
            if tag in blk:
                continue
            br = re.search(rb'([ \t]*)<actor_dialog>actor_break_dialog</actor_dialog>', blk)
            if br is None:
                sys.exit('character %s: no actor_break_dialog line' % cid)
            blk = blk[:br.start()] + br.group(1) + tag + nl + blk[br.start():]
        data = data[:m.start()] + blk + data[m.end():]
    return data


rw(P('patches', 'repeatable_quests', 'gamedata', 'configs', 'gameplay', 'character_desc_coop_l05_bar.xml'), chars)

# ---- 4. changes lines
EN = ("- @soc_bar_duty_line: The Duty / Freedom line of the Bar follows the original SoC. Duty's gate commander (Sergeant Plichko) and Captain Ivantsov stand where "
      "they stood in SoC; the commander sells the pass for 1000, Voronin, Petrenko and the commander speak the original lines. Join Duty: Ivantsov's test (win the "
      "pseudodog fight on the Arena), Voronin's Bulldog 6 job (the RG-6 lies in the Freedom village stash of the Army Warehouses), the oath and the Duty suit. The "
      "Barkeep's jobs \"Kill the mad veterans\" (Lucky and two veterans camp on the Wild Territory) and \"Eliminate the Mercs\" (Tyran with his men at the construction "
      "site, snipers on the way) end with their PDAs; after the Mercs Voronin sends you to kill the leader of Freedom (Lukash). Every task goes to every player, late "
      "joiners included; a dead NPC or a lost item does not block a step.")
RU = ("- @soc_bar_duty_line: Линия Долга и Свободы на Баре идёт как в оригинальном ТЧ. Командир ворот Долга (сержант Пличко) и капитан Иванцов стоят там, где стояли "
      "в ТЧ; командир продаёт пропуск за 1000, Воронин, Петренко и командир говорят оригинальные реплики. Вступление в Долг: проверка Иванцова (победить псевдособаку "
      "на Арене), задание Воронина на РГ-6 (РГ-6 лежит в тайнике деревни Свободы на Военных складах), присяга и костюм Долга. Работы Бармена \"Убить безумных ветеранов\" "
      "(Счастливчик и два ветерана в лагере на Дикой территории) и \"Уничтожить наёмников\" (Тиран с людьми на стройке, снайперы по дороге) заканчиваются сдачей их КПК; "
      "после наёмников Воронин посылает убить лидера Свободы (Лукаша). Каждое задание получает каждый игрок, в том числе зашедшие позже; смерть НПС или потеря предмета "
      "шаг не блокируют.")
OLD_EN = rb'The Duty (and|/) Freedom (tasks|quests) of the original \([^)]*\) are not in the mod: [^.]*\. '
OLD_RU = ('Задания Долга и Свободы из оригинала \([^)]*\) в моде отсутствуют: [^.]*\. ').encode('utf-8')


def changes(path, line, old, enc, anchor):
    def fn(data):
        data = re.sub(old, b'', data, count=1)
        tag = b'- @soc_bar_duty_line:'
        i = data.find(tag)
        nl = b'\r\n' if b'\r\n' in data else b'\n'
        if i >= 0:
            j = data.find(b'\n', i)
            j = len(data) if j < 0 else j
            end = j - 1 if data[j - 1:j] == b'\r' else j
            return data[:i] + line.encode(enc) + data[end:]
        k = data.find(anchor.encode(enc))
        if k < 0:
            sys.exit('anchor not found in ' + path)
        return data[:k] + line.encode(enc) + nl + data[k:]
    rw(path, fn)


changes(P('installer', 'changes_1.4.en.txt'), EN, OLD_EN, 'utf-8', '- Smaller patch file')
changes(P('installer', 'changes_1.4.ru.txt'), RU, OLD_RU, 'utf-8', '- Файл патча стал меньше')

# ---- 5. bar_soc_quests NOTES pointer
NOTE = ("\r\n> Update: the Duty / Freedom line was done afterwards by patch `soc_bar_duty_line` (see its NOTES.md): gate commander, Ivantsov, Voronin's and Petrenko's SoC dialogs, "
        "the Bulldog 6 job, the oath, the veterans job, Tyran, the Lukash order. The table below is the state before that patch.\r\n")


def notes(data):
    marker = b'## The Duty / Freedom line: what exists in the mod, what is done'
    if b'soc_bar_duty_line' in data or marker not in data:
        return data
    i = data.index(marker)
    j = data.index(b'\n', i) + 1
    return data[:j] + NOTE.encode('ascii') + data[j:]


np_ = P('patches', 'bar_soc_quests', 'NOTES.md')
if os.path.exists(np_):
    rw(np_, notes)

print('changed:', changed if changed else 'nothing (already applied)')
