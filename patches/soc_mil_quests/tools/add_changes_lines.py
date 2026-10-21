"""Adds the one change line of patch soc_mil_quests to installer\\changes_1.4.en.txt and .ru.txt (idempotent, before the line about the smaller patch file).
Both files are UTF-8: bytes are edited, nothing else is touched."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TAG = b'- @soc_mil_quests,'

EN = ("- @soc_mil_quests,freedom_duty,campfires,repeatable_quests: The Army Warehouses quests follow the original SoC. Lukash, Max, Skull and the Barrier "
      "commander (Cap) talk with the original lines (the original has no voice for them). Freedom: Lukash sends you to Max, \"Destroy the Duty squad\" is ONE objective "
      "(not Skull plus eight men), then \"Return to Lukash\"; Lukash then sends you to the Barrier: talk to the commander, help destroy the Monolith squad, talk to the "
      "commander again for his reward, and Lukash pays 4000. Duty: Skull's tower sniper (pays 4000), then the assault with THREE snipers (not four) and Lukash, and "
      "\"Return to the Duty farmstead and receive my fee\" (8000). The money is paid in the dialogs to the player who talks, as in SoC (the old task rewards are gone). "
      "The step \"go to the Radar\" is gone from this level (the Radar job comes from the Barkeep). Every task goes to every player, late joiners included, and a dead "
      "Max, Lukash, Cap or Skull does not block a step. Fixed: the Duty assault never started when you took Skull's job (a lower case letter in a flag name of the "
      "level logic), and the \"kill Lukash\" tasks were never given. Not in the mod: the snitch Pavlik and the Bulldog 6 order.")
RU = ("- @soc_mil_quests,freedom_duty,campfires,repeatable_quests: Задания Армейских складов идут как в оригинальном ТЧ. Лукаш, Макс, Череп и командир Барьера "
      "(Кеп) говорят оригинальными репликами (озвучки у них в оригинале нет). Свобода: Лукаш посылает к Максу, \"Уничтожить группу Долга\" теперь ОДНА цель "
      "(а не Череп и ещё восемь человек), потом \"Вернуться к Лукашу\"; затем Лукаш посылает на Барьер: поговорить с командиром, помочь уничтожить отряд Монолита, "
      "ещё раз поговорить с командиром за наградой, и Лукаш платит 4000. Долг: снайпер на вышке у Черепа (4000), затем штурм с ТРЕМЯ снайперами (не четырьмя) и "
      "Лукашом и \"Вернуться на хутор Долга и получить гонорар\" (8000). Деньги платятся в диалогах тому игроку, кто говорит, как в ТЧ (прежние награды заданий "
      "убраны). Шага \"идти на Радар\" на этой локации больше нет (задание на Радар даёт Бармен). Каждое задание получает каждый игрок, в том числе зашедшие "
      "позже, а погибший Макс, Лукаш, Кеп или Череп не блокирует шаг. Исправлено: штурм Долга не начинался после задания Черепа (строчная буква в имени флага "
      "в логике уровня), а задания \"убить Лукаша\" не выдавались вообще. В моде нет: стукача Павлика и заказа на \"Бульдог 6\".")


def patch(path, line, anchor):
    data = open(path, 'rb').read()
    nl = b'\r\n' if b'\r\n' in data else b'\n'
    enc = line.encode('utf-8')
    i = data.find(TAG)
    if i >= 0:                                   # replace our own line
        j = data.find(b'\n', i)
        j = len(data) if j < 0 else j
        end = j - 1 if data[j - 1:j] == b'\r' else j
        if data[i:end] == enc:
            print('unchanged', os.path.basename(path))
            return
        data = data[:i] + enc + data[end:]
    else:
        i = data.find(anchor.encode('utf-8'))
        assert i >= 0, 'anchor not found in ' + path
        data = data[:i] + enc + nl + data[i:]
    open(path, 'wb').write(data)
    print('changed', os.path.basename(path))


patch(os.path.join(REPO, 'installer', 'changes_1.4.en.txt'), EN, '- Smaller patch file')
patch(os.path.join(REPO, 'installer', 'changes_1.4.ru.txt'), RU, '- Файл патча стал меньше')
