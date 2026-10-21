"""Adds the Garbage lines to installer\\changes_1.4.en.txt / .ru.txt once (idempotent), before the "Smaller patch file" line."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.path.normpath(os.path.join(HERE, "..", "..", "..", "installer"))

EN = [
    "- @campfires: Garbage, Bes: after his quest is finished he no longer repeats the request greeting (\"you came just in time, bandit scum wants the Garbage\"), he has a short normal line like in the original",
    "- @campfires,garbage_gray,player_scaling: Garbage, \"Total Lawlessness\" (Gray at the hangar): the bandits now really attack once the task is given (they no longer stand around until a player happens to step on the hill) and walk towards Gray's stalkers; there are six of them at the foot of the hill by the road with the concrete blocks, like the six bandits of the original (before: four there and one far away)",
    "- @garbage_duty,garbage_gray,campfires,freedom_duty: Garbage, Duty checkpoint on the road to the Bar as in the original: the soldiers wear the original Duty suits (gas-tank suits and the gas mask), the commander (Prapor) the original officer suit and talks like in the original (\"Halt, stalker, you can't go any further\"). The road to the Bar is closed until the group gets a pass: the commander lets you through when you have the Agroprom military documents, or for 2000 rubles (paid by one player, the pass is for the whole group and saved with the game). After the boar attack (task \"Wave of Mutants\") the commander speaks with the original voice (Russian or English like the opening): praise and a free pass when the players killed 3 or more boars, scorn and no pass when fewer",
]
RU = [
    "- @campfires: Свалка, Бес: после выполнения его задания он больше не повторяет приветствие с просьбой о помощи (\"вы как раз вовремя, бандитское отребье хочет Свалку\"), у него короткая обычная реплика, как в оригинале",
    "- @campfires,garbage_gray,player_scaling: Свалка, \"Полный беспредел\" (Серый у ангара): бандиты теперь действительно нападают, как только задание выдано (раньше они стояли, пока игрок случайно не зайдёт на холм), и идут к сталкерам Серого; у подножия холма у дороги с бетонными блоками их шестеро, как в оригинале (раньше там было четверо, ещё один стоял далеко)",
    "- @garbage_duty,garbage_gray,campfires,freedom_duty: Свалка, блокпост Долга на дороге к Бару как в оригинале: солдаты в оригинальных костюмах Долга (с баллонами и противогазом), командир (Прапор) в оригинальном костюме офицера и говорит как в оригинале (\"Стой, сталкер, дальше тебе нельзя\"). Дорога к Бару закрыта, пока группа не получит пропуск: командир пропускает, если есть документы военных с Агропрома, или за 2000 рублей (платит один игрок, пропуск для всей группы и сохраняется в игре). После нападения кабанов (задание \"Волна мутантов\") командир говорит оригинальным голосом (русским или английским, как в начале игры): похвала и бесплатный пропуск, если игроки убили 3 кабана и больше, упрёк и без пропуска, если меньше",
]


def add(name, lines):
    p = os.path.join(INST, name)
    raw = open(p, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    if "@garbage_duty" in text:
        return
    nl = "\r\n" if crlf else "\n"
    rows = text.split(nl)
    i = next(k for k, r in enumerate(rows) if r.startswith("- Smaller patch file") or r.startswith("- Файл патча стал меньше"))
    rows[i:i] = lines
    open(p, "wb").write(nl.join(rows).encode("utf-8"))


add("changes_1.4.en.txt", EN)
add("changes_1.4.ru.txt", RU)
print("ok")
