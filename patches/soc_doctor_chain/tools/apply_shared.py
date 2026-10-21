"""Edits of files that OTHER patches ship (one patch per file: each edit is made in the copy that is effective in a build = the last patch, in sorted
order, that ships the file). Idempotent: run it as often as you like, it only writes when something is missing.

  python tools\\apply_shared.py [--repo <repo root>] [--check]

Default repo root = the repo this script lives in. --check writes nothing and exits 1 when an edit is still missing.
Edits (all byte level, the files are windows-1251 / UTF-8 with CRLF or LF, nothing else in them is touched):
  1. configs\\system.ltx (repeatable_quests)
       [dialogs] files            + dialogs_coop_soc_doctor          (the Guide topic and the Doctor's dialogs)
       [profiles] files           + npc_profile_soc_doctor           (profile id soc_cit_doctor)
       specific_characters_files  + character_desc_coop_soc_doctor   (the Doctor)
       #include "creatures\\spawn_sections_coop_soc_doctor.ltx" after the include of creatures\\spawn_sections.ltx (the Doctor's spawn section)
  2. configs\\misc\\task_manager.ltx (repeatable_quests): #include "tm_coop_soc_doctor.ltx" after the last tm_coop_*.ltx include (tasks soc_doc_meet_task, soc_doc_stash_task)
  3. configs\\gameplay\\character_desc_coop_l01_escape.xml (repeatable_quests): the Cordon Guide gets the actor dialog soc_doc_guide_dialog
  4. installer\\changes_1.4.en|ru.txt and changes_1.4.1.en|ru.txt: one change line (tag @soc_doctor_chain, dropped from the README when the patch is skipped)
  5. NOTES.md of soc_yan_x16_quests and soc_aes_quests: one line each saying the Doctor chain now exists (patch soc_doctor_chain)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CHECK = '--check' in sys.argv
if '--repo' in sys.argv:
    REPO = os.path.abspath(sys.argv[sys.argv.index('--repo') + 1])
PATCHES = os.path.join(REPO, 'patches')
SELF = 'soc_doctor_chain'
missing = []
changed = []


def effective(rel):
    """Path of the copy of gamedata/<rel> that wins in a build (last patch in sorted order that ships it, ours excluded)."""
    found = None
    for fix in sorted(os.listdir(PATCHES)):
        if fix == SELF:
            continue
        p = os.path.join(PATCHES, fix, 'gamedata', rel)
        if os.path.isfile(p):
            found = p
    return found


def edit(path, fn, what):
    if path is None:
        raise SystemExit('FAILED (no patch ships the file): %s' % what)
    data = open(path, 'rb').read()
    new = fn(data)
    if new is None:
        raise SystemExit('FAILED (anchor not found): %s in %s' % (what, path))
    if new != data:
        missing.append(what)
        if not CHECK:
            open(path, 'wb').write(new)
            changed.append('%s: %s' % (os.path.relpath(path, REPO), what))


def append_list_item(data, header, key, item):
    """Adds ', item' to the end of the `key = a, b, c` line that follows the section header (before the next section). None when not found."""
    m = re.search(rb'^\[' + re.escape(header) + rb'\][^\n]*\n', data, re.M)
    if not m:
        return None
    end = re.search(rb'^\[', data[m.end():], re.M)
    stop = m.end() + (end.start() if end else len(data) - m.end())
    km = re.search(rb'^(' + re.escape(key) + rb'\s*=[^\r\n]*?)([ \t]*)(\r?)$', data[m.end():stop], re.M)
    if not km:
        return None
    line = km.group(1)
    names = [x.strip() for x in line.split(b'=', 1)[1].split(b',')]
    if item.encode() in names:
        return data
    s = m.end() + km.start()
    e = m.end() + km.end(1)
    return data[:s] + line + b', ' + item.encode() + data[e:]


# ---------------------------------------------------------------------------------------------------------------- 1. system.ltx
def system_ltx(data):
    d = append_list_item(data, b'dialogs', b'files', 'dialogs_coop_soc_doctor')
    if d is None:
        return None
    d = append_list_item(d, b'profiles', b'files', 'npc_profile_soc_doctor')
    if d is None:
        return None
    d = append_list_item(d, b'profiles', b'specific_characters_files', 'character_desc_coop_soc_doctor')
    if d is None:
        return None
    inc = b'#include "creatures\\spawn_sections_coop_soc_doctor.ltx"'
    if inc in d:
        return d
    m = re.search(rb'^#include "creatures\\spawn_sections\.ltx"[ \t]*(\r?\n)', d, re.M)
    if not m:
        return None
    return d[:m.end()] + inc + m.group(1) + d[m.end():]


p = effective('configs/system.ltx')
edit(p, system_ltx, 'system.ltx: Doctor dialogs, profile, specific character, spawn section')


# ---------------------------------------------------------------------------------------------------------------- 2. task_manager.ltx
def task_manager(data):
    inc = b'#include "tm_coop_soc_doctor.ltx"'
    if inc in data:
        return data
    last = None
    for m in re.finditer(rb'^#include "tm_coop_[a-z0-9_]+\.ltx"[ \t]*(\r?\n)', data, re.M):
        last = m
    if last is None:
        return None
    return data[:last.end()] + inc + last.group(1) + data[last.end():]


p = effective('configs/misc/task_manager.ltx')
edit(p, task_manager, 'task_manager.ltx: include tm_coop_soc_doctor.ltx')


# ---------------------------------------------------------------------------------------------------------------- 3. the Guide
def guide(data):
    s = data.find(b'<specific_character id="esc_smart_terrain_1_stalker_guide"')
    if s < 0:
        return None
    e = data.find(b'</specific_character>', s)
    block = data[s:e]
    if b'soc_doc_guide_dialog' in block:
        return data
    m = re.search(rb'([ \t]*)<actor_dialog>actor_break_dialog</actor_dialog>[ \t]*(\r?\n)', block)
    if not m:
        return None
    new = block[:m.start()] + m.group(1) + b'<actor_dialog>soc_doc_guide_dialog</actor_dialog>' + m.group(2) + block[m.start():]
    return data[:s] + new + data[e:]


p = effective('configs/gameplay/character_desc_coop_l01_escape.xml')
edit(p, guide, 'character_desc_coop_l01_escape.xml: Guide actor dialog')

# ---------------------------------------------------------------------------------------------------------------- 4. change lines
TAG = b'- @soc_doctor_chain,'
EN = ("- @soc_doctor_chain,repeatable_quests: The Guide and the Doctor of the original SoC. Once you have taken Ghost's documents, the Cordon Guide has a new "
      "topic (\"Guide, I need to see Doctor.\", the original lines): the Doctor waits in Strelok's hiding place, \"Meeting with Doctor\" goes to every player and "
      "the Guide's PDA note shows. In the Agroprom underground the Doctor stands in that hiding place (his original spot), recognises Strelok, hears that Ghost "
      "is dead and hands over the task \"Secret stash at Pripyat\" (diary \"Meeting with the Doctor\"); the original English voice plays for his lines. The task "
      "leads to the decoder in the Pripyat hotel (see the entry above). Nothing blocks: a dead Doctor or a party that goes straight to Pripyat just skips "
      "the chain. Not in the mod: the Dead City (in the original you are knocked out in the underground and wake up in its jail), so the Doctor's jail "
      "talks and the Dead City quests are missing.")
RU = ("- @soc_doctor_chain,repeatable_quests: Проводник и Доктор из оригинальной ТЧ. Когда вы взяли документы Призрака, у Проводника на Кордоне появляется новая "
      "тема (\"Проводник, мне нужно встретиться с Доктором.\", оригинальные реплики): Доктор ждёт в тайнике Стрелка, задание \"Встретиться с Доктором\" получает "
      "каждый игрок, в КПК приходит записка Проводника. В подземельях Агропрома Доктор стоит в этом тайнике (на своём месте из оригинала), узнаёт Стрелка, "
      "слышит, что Призрак мёртв, и даёт задание \"Тайник на Припяти\" (дневник \"Встреча с Доктором\"); его реплики озвучены оригинальной английской озвучкой. "
      "Задание ведёт к декодеру в гостинице Припяти (см. запись выше). Ничто не блокируется: погибший Доктор или отряд, ушедший сразу в Припять, просто "
      "пропускают цепочку. В моде нет Мёртвого города (в оригинале вас оглушают в подземелье и вы приходите в себя в его тюрьме), поэтому разговоров "
      "Доктора в тюрьме и заданий Мёртвого города нет.")


def change_line(line, header):
    def fn(data):
        enc = line.encode('utf-8')
        nl = b'\r\n' if b'\r\n' in data else b'\n'
        i = data.find(TAG)
        if i >= 0:
            j = data.find(b'\n', i)
            j = len(data) if j < 0 else j
            end = j - 1 if data[j - 1:j] == b'\r' else j
            return data[:i] + enc + data[end:]
        h = data.find(nl + header.encode('utf-8'))
        if h < 0:
            return None
        return data[:h] + nl + enc + data[h:]
    return fn


# the lists of the two releases in progress (v1.4 and v1.4.1 both carry the chain lines of the SoC quest patches); a file without the
# "Known issue" header (a new list that has only a few lines, like v1.4.2) is left alone
for ver in ('1.4', '1.4.1'):
    for lang, line, header in (('en', EN, 'Known issue'), ('ru', RU, 'Известная проблема')):
        path = os.path.join(REPO, 'installer', 'changes_%s.%s.txt' % (ver, lang))
        if os.path.isfile(path):
            edit(path, change_line(line, header), 'changes_%s.%s.txt: change line' % (ver, lang))
        else:
            print('NOTE: %s not found, change line not added' % path)

# ---------------------------------------------------------------------------------------------------------------- 5. notes of the two chains
NOTE_YAN = ("\n\nUpdate (patch soc_doctor_chain): the Doctor chain after \"Meet the Guide\" now exists. The Guide has the SoC topic (esc_provodnik_start 12 to 16), which gives "
            "ESC_FIND_DOCTOR_START (this patch's tick also sets YAN_SOC_GUIDE_MET from it) and the task \"Meet with Doctor\"; the Doctor stands in Strelok's hiding place of the "
            "Agroprom underground and gives \"Secret stash at Pripyat\". The 6 m proximity completion above still works as before.\n")
NOTE_AES = ("\n\nUpdate (patch soc_doctor_chain): the Doctor now exists, in Strelok's hiding place of the Agroprom underground (the mod has no Dead City). His talk gives the task "
            "\"Secret stash at Pripyat\" (soc_doc_stash_task) on every level before Pripyat; it ends where the first stash step of this patch ends (the hotel) and fails when the party "
            "leaves for CNPP-1, like those steps. Nothing here reads a flag of that chain, so a party that never met the Doctor still gets the three steps on arrival.\n")


def note(text, marker):
    def fn(data):
        if marker.encode() in data:
            return data
        nl = b'\r\n' if b'\r\n' in data else b'\n'
        add = text.replace('\n', nl.decode()).encode('utf-8')
        return data.rstrip(b'\r\n') + add
    return fn


for fix, text in (('soc_yan_x16_quests', NOTE_YAN), ('soc_aes_quests', NOTE_AES)):
    path = os.path.join(PATCHES, fix, 'NOTES.md')
    if os.path.isfile(path):
        edit(path, note(text, 'patch soc_doctor_chain'), 'NOTES.md of %s' % fix)

if CHECK:
    print('missing edits:', len(missing))
    for m in missing:
        print('  -', m)
    sys.exit(1 if missing else 0)
print('changed %d' % len(changed))
for c in changed:
    print('  +', c)
