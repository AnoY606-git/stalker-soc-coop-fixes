"""Adds the one change line of patch bar_soc_quests to installer\\changes_1.4.en.txt and .ru.txt (idempotent, before the line about the smaller patch file).
Both files are UTF-8: bytes are edited, nothing else is touched."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

EN = ("- @bar_soc_quests,soc_dv_x18_quests,quest_dialogs,repeatable_quests,hunter_shotgun: The Barkeep's jobs follow the original SoC. After the X-18 documents he offers "
      "\"Find the documents in X16 lab\" in his talk (accepting gives the task to everybody); it is ONE task whose text and marker follow its steps (talk to the scientists, "
      "find the X16 documents, bring them to the Barkeep), the copies on the Wild Territory and Yantar are gone. The X16 documents are handed in to the Barkeep (original lines, "
      "English voice), and only then he offers \"Turn off the Brain Scorcher\" (one task up to the Radar; the Army Warehouses are optional). The hunter has the original lines, "
      "pays 4000 and a new step \"Return the rifle to the hunter at the Bar\". Kruglov has the steps \"Talk to professor Kruglov\" (Wild Territory) and \"Talk to Kruglov\" (Yantar), "
      "the escort starts when you reach him. \"The meeting place cannot be changed\" is gone. The Duty / Freedom quests of the original (joining Duty, the mad veterans, Tyran, "
      "Ivantsov's test) are not in the mod: they need NPCs and items it does not have. Every task goes to every player, late joiners included; a dead NPC or a lost item does not "
      "block the chain.")
RU = ("- @bar_soc_quests,soc_dv_x18_quests,quest_dialogs,repeatable_quests,hunter_shotgun: Работы Бармена идут как в оригинальном ТЧ. После документов X-18 он предлагает в "
      "разговоре \"Найти документы в лаборатории X16\" (согласие даёт задание всем); это ОДНО задание, его текст и метка идут по шагам (поговорить с учёными, найти документы Х-16, "
      "принести Бармену), копий на Дикой территории и на Янтаре больше нет. Документы X16 сдаются Бармену (оригинальные реплики, английская озвучка), и только потом он "
      "предлагает \"Отключить Выжигатель Мозгов\" (одно задание до Радара; Военные склады необязательны). У охотника оригинальные реплики, награда 4000 и новый шаг "
      "\"Вернуть ружьё охотнику в баре\". У Круглова шаги \"Поговорить с профессором Кругловым\" (Дикая территория) и \"Поговорить с Кругловым\" (Янтарь), сопровождение начинается, "
      "когда дойдёшь до него. \"Место встречи изменить нельзя\" убрано. Задания Долга и Свободы из оригинала (вступление в Долг, безумные ветераны, Тиран, проверка Иванцова) "
      "в моде отсутствуют: для них нужны персонажи и предметы, которых в нём нет. Каждое задание получает каждый игрок, в том числе зашедшие позже; смерть НПС или потеря "
      "предмета цепочку не блокируют.")


def patch(path, line, enc, anchor_start):
    data = open(path, 'rb').read()
    nl = b'\r\n' if b'\r\n' in data else b'\n'
    tag = b'- @bar_soc_quests,'
    i = data.find(tag)
    if i >= 0:                                   # replace our own line
        j = data.find(b'\n', i)
        j = len(data) if j < 0 else j
        end = j - 1 if data[j - 1:j] == b'\r' else j
        if data[i:end] == line.encode(enc):
            print('unchanged', os.path.basename(path))
            return
        data = data[:i] + line.encode(enc) + data[end:]
    else:
        i = data.find(anchor_start.encode(enc))
        assert i >= 0, 'anchor not found in ' + path
        data = data[:i] + line.encode(enc) + nl + data[i:]
    open(path, 'wb').write(data)
    print('changed', os.path.basename(path))


patch(os.path.join(REPO, 'installer', 'changes_1.4.en.txt'), EN, 'utf-8', '- Smaller patch file')
patch(os.path.join(REPO, 'installer', 'changes_1.4.ru.txt'), RU, 'utf-8', '- Файл патча стал меньше')
