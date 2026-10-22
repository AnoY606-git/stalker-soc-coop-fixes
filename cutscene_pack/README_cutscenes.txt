Shadow of COOP - cutscene pack (original S.T.A.L.K.E.R. movies)
================================================================

ENGLISH
-------
What it is: the original Shadow of Chernobyl movie files and movie sound tracks for the cut-scenes of the unofficial fix patch
(zzz_soc_coop_fixes.db): the dream in the X18 lab, the dream at the Radar, the doctor dream in Yantar, the Monolith join dream, the
sound of the opening movie, and the "teleport" voice line at the Monolith. Without this pack those scenes play their short fallback
instead of the movie. The endings and the opening picture are already inside the mod, they need nothing.
Size: about 78 MB (67.6 MB movies + 10 MB sound of ONE language). It is a separate download because coop.addon cannot grow any more.
Files: zz_soc_cutscenes.db (movies), zz_soc_cutscenes_voice_rus.db (original Russian sound), zz_soc_cutscenes_voice_eng.db (English sound).

Do you need it? Only if you want to SEE the movies. Every player installs it on his own PC (host and clients). A dedicated server does not
need it. A player without the pack still plays normally and sees the short fallback while the others see the movie.
It does not change coop.addon, so it NEVER causes "Different Versions" (the game compares only the checksum of *.addon files).

Install (easy way):
1. Close the game and the xrMPE launcher.
2. Unzip this archive anywhere.
3. Double-click install_cutscenes.bat. It finds the X-Ray Multiplayer Extension folder (or asks for its path) and copies the movie
   archive and ONE sound archive into X-Ray Multiplayer Extension\game\patches\.
   The sound language is chosen for you: voice_language of your coop_settings.ltx, else the launcher language. To force one:
   install_cutscenes.bat -Voice rus   or   install_cutscenes.bat -Voice eng
4. Start a new game (or load a save before the scene): the movie plays with its sound.

Install by hand: copy zz_soc_cutscenes.db and ONE of zz_soc_cutscenes_voice_rus.db / zz_soc_cutscenes_voice_eng.db (never both) into
X-Ray Multiplayer Extension\game\patches\ .

If the launcher ever deletes the files from patches\ (it has not been seen doing that): run install_cutscenes.bat -Loose. That unpacks the
same files into X-Ray Multiplayer Extension\game\gamedata\ instead, where the game also reads them.

Uninstall: install_cutscenes.bat -Uninstall (or delete the zz_soc_cutscenes*.db files from game\patches\).

How to check it works: in the game log the scene lines "SCENE ... FALLBACK" for a movie scene are gone, and the movie plays.
Credits: the movies and sounds are from S.T.A.L.K.E.R.: Shadow of Chernobyl by GSC Game World; the Full HD movies are by neatodev (Nexus mod 1098).

Full HD movies (optional, included in this zip): zz_soc_cutscenes_hd.db (about 1.3 GB) holds the 11 movies (intro, the four dreams and all six
endings) in Full HD, from "SoC Enhanced Edition Cutscenes" by neatodev (https://www.nexusmods.com/stalkershadowofchernobyl/mods/1098): the AI
upscaled cutscenes of the Enhanced Edition, cleaned up and ported to the original engine. install_cutscenes.bat installs it automatically when the
file is next to it. The sound stays the files of this pack (original Russian or English), the HD files are video only. Without the HD file the
normal movies play, nothing else changes.

РУССКИЙ
-------
Что это: оригинальные видеоролики и звуковые дорожки роликов S.T.A.L.K.E.R. Тень Чернобыля для сцен неофициального патча
(zzz_soc_coop_fixes.db): сон в лаборатории Х18, сон на Радаре, сон доктора на Янтаре, сон "присоединиться" у Монолита, звук
вступительного ролика и голосовая реплика "телепорт" у Монолита. Без этого пакета эти сцены показывают короткую заставку-замену
вместо ролика. Концовки и картинка вступления уже есть в самом моде, им ничего не нужно.
Размер: около 78 МБ (67,6 МБ ролики + 10 МБ звук ОДНОГО языка). Это отдельная загрузка, потому что coop.addon больше расти не может.
Файлы: zz_soc_cutscenes.db (ролики), zz_soc_cutscenes_voice_rus.db (оригинальный русский звук), zz_soc_cutscenes_voice_eng.db (английский звук).

Нужно ли это вам? Только если вы хотите ВИДЕТЬ ролики. Пакет ставит каждый игрок на своём ПК (хост и клиенты). Выделенному серверу он не нужен.
Игрок без пакета играет как обычно и видит короткую заставку-замену, пока остальные смотрят ролик.
coop.addon пакет не меняет, поэтому он НИКОГДА не вызывает "Различные версии" (игра сравнивает только контрольную сумму файлов *.addon).

Установка (простой способ):
1. Закройте игру и лаунчер xrMPE.
2. Распакуйте этот архив в любую папку.
3. Запустите install_cutscenes.bat двойным щелчком. Он найдёт папку X-Ray Multiplayer Extension (или спросит путь) и скопирует архив с
   роликами и ОДИН архив со звуком в X-Ray Multiplayer Extension\game\patches\.
   Язык звука выбирается сам: voice_language из вашего coop_settings.ltx, иначе язык лаунчера. Чтобы задать язык:
   install_cutscenes.bat -Voice rus   или   install_cutscenes.bat -Voice eng
4. Начните новую игру (или загрузите сохранение до сцены): ролик пойдёт со звуком.

Вручную: скопируйте zz_soc_cutscenes.db и ОДИН из файлов zz_soc_cutscenes_voice_rus.db / zz_soc_cutscenes_voice_eng.db (не оба сразу) в
X-Ray Multiplayer Extension\game\patches\ .

Если лаунчер когда-нибудь удалит файлы из patches\ (такого замечено не было): запустите install_cutscenes.bat -Loose. Он распакует те же
файлы в X-Ray Multiplayer Extension\game\gamedata\, оттуда игра их тоже читает.

Удаление: install_cutscenes.bat -Uninstall (или удалите файлы zz_soc_cutscenes*.db из game\patches\).

Как проверить: в логе игры у сцен с роликами пропадают строки "SCENE ... FALLBACK", и ролик идёт.
Авторские права: ролики и звуки принадлежат GSC Game World (S.T.A.L.K.E.R.: Shadow of Chernobyl).

Ролики Full HD (по желанию, есть в этом архиве): zz_soc_cutscenes_hd.db (около 1,3 ГБ), 11 роликов (вступление, четыре сна и все шесть концовок)
в Full HD из мода "SoC Enhanced Edition Cutscenes" автора neatodev (https://www.nexusmods.com/stalkershadowofchernobyl/mods/1098): улучшенные
нейросетью ролики Enhanced Edition, исправленные и перенесённые на оригинальный движок. install_cutscenes.bat ставит его сам, если файл лежит рядом.
Звук остаётся из этого пакета (оригинальная русская или английская озвучка), HD файлы только видео. Без HD файла играют обычные ролики.
