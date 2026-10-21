"""Adds the one change line of patch garbage_soc_quests to installer\\changes_1.4.en.txt and .ru.txt (idempotent, before the line about the smaller patch file).
Both files are UTF-8: bytes are edited, nothing else is touched."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

EN = ("- @garbage_soc_quests,garbage_duty,campfires,repeatable_quests: The Garbage quests follow the original SoC. \"Meet with Seriy\" comes from Fox on Cordon "
      "(or when you arrive on the Garbage) and is one task: first Fox's words, then \"Learn something of Strelok from Seriy\" with his marker; the level maker's "
      "\"help the Gray fight off the bandits\" step is gone, the fight at the hangar stays. Seriy and Bes can be talked to as soon as you arrive (Bes no longer waits for "
      "the Yurik steps, Seriy does not wait for Bes, their radio calls are gone), Seriy's talk has the original SoC lines, pays 2500 to the player who talks (Bes pays 2000, as in SoC; the old 5000 task reward is gone) and gives the Agroprom task. \"Help the Duty "
      "checkpoint\" has its second objective \"Talk with the Duty commander\": the commander (now really talkable) thanks you and pays 1500 to the player he talks to "
      "after a boar was killed by a player, and he offers the favor (kill the boars) in his dialog. The wave also starts when any player stays near the checkpoint. "
      "Every task goes to every player, late joiners included; if Seriy, Bes or the commander die the quests do not get stuck.")
RU = ("- @garbage_soc_quests,garbage_duty,campfires,repeatable_quests: Задания Свалки идут как в оригинальном ТЧ. \"Встретиться с Серым\" даёт Лис на Кордоне "
      "(или она появляется при приходе на Свалку) и это одно задание: сначала слова Лиса, потом \"Узнать у Серого о Стрелке\" с меткой на нём; шаг автора уровня "
      "\"помочь Серому отбиться от бандитов\" убран, бой у ангара остался. С Серым и Бесом можно говорить сразу после прихода (Бес больше не ждёт шагов Юрика, "
      "Серый не ждёт Беса, их радиовызовы убраны), разговор с Серым с оригинальными репликами ТЧ платит 2500 тому, кто говорит (Бес платит 2000, как в ТЧ; прежняя награда 5000 за задание убрана), и даёт задание про Агропром. У задания \"Помочь заставе Долга\" "
      "появилась вторая цель \"Поговорить с командиром заставы\": командир (с ним теперь действительно можно говорить) благодарит и платит 1500 тому игроку, который "
      "с ним говорит, если кабана убил игрок, и в диалоге предлагает услугу (убить кабанов). Волна начинается и когда любой игрок стоит у заставы. "
      "Каждое задание получает каждый игрок, в том числе зашедшие позже; если Серый, Бес или командир погибнут, задания не зависнут.")


def patch(path, line, enc, anchor_start):
    data = open(path, 'rb').read()
    nl = b'\r\n' if b'\r\n' in data else b'\n'
    tag = b'- @garbage_soc_quests,'
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


    print('changed', os.path.basename(path))


patch(os.path.join(REPO, 'installer', 'changes_1.4.en.txt'), EN, 'utf-8', '- Smaller patch file')
patch(os.path.join(REPO, 'installer', 'changes_1.4.ru.txt'), RU, 'utf-8', '- Файл патча стал меньше')
