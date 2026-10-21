Shadow of COOP - unofficial fix patch v{VERSION} ({DATE})
=====================================================

ENGLISH
-------
Unofficial fan patch for Shadow of COOP 8.1 on xrMPE. Back up coop.addon before installing.
This replaces the earlier zzz_soc_coop_fixes.db (same file name).

Install (the host AND every client must install the same file, or you get "Different Versions"):
Easy way (recommended):
1. Close the game and the launcher.
2. Unzip this archive anywhere.
3. Double-click installer\install.bat. It finds coop.addon (or asks for its path) and adds zzz_soc_coop_fixes.db
   the same way on every PC, so everyone gets the same add-on fingerprint. Compare the fingerprint it prints.
4. Start a new game (recommended).

Manual way with 7-Zip:
1. Close the game and the launcher.
2. Go to X-Ray Multiplayer Extension\game\addons\
3. Open coop.addon with 7-Zip (right-click > 7-Zip > Open archive).
4. Drag zzz_soc_coop_fixes.db into the 7-Zip window, click OK and confirm replacing the old one.
5. Start a new game (recommended).
If players still see "Different Versions", use installer\install.bat on every PC.

Uninstall: run installer\install.bat -Uninstall, or open coop.addon with 7-Zip again and delete zzz_soc_coop_fixes.db.

Host settings (only the HOST needs this; other players do nothing):
The balance numbers (player damage, enemies per player, box loot, mutant parts, repeatable quests, roaming squads) can be changed WITHOUT reinstalling.
The first time the host starts a game with this patch it creates the file coop_settings.ltx with every setting, its default and a short comment:
- you host and play: X-Ray Multiplayer Extension\game\_appdata_\coop_settings.ltx
- dedicated server:  X-Ray Multiplayer Extension\game\_appdata_server\coop_settings.ltx
Open it with Notepad, change a number (for example player_damage_mult = 2.0), save, then change the level or restart the server.
A line you delete or a wrong value simply uses the default; delete the whole file to get a fresh one. The log line "[HOSTCFG]" shows what is in effect.
Other players never read this file and it does not change the add-on fingerprint, except one personal setting: the [client] section is read by EVERY player from HIS OWN coop_settings.ltx (the file is created for you at the first start, also if you only join).
  voice_language = auto | rus | eng : voice of Sidorovich's opening speech (auto = the language of your game, default; rus = Russian; eng = English).
  A line with no recording in that language is silent. There are no on-screen subtitles.

{CHANGES_EN}

РУССКИЙ
-------
Неофициальный фан-патч для Shadow of COOP 8.1 на xrMPE. Перед установкой сделайте бэкап coop.addon.
Заменяет прежний zzz_soc_coop_fixes.db (то же имя файла).

Установка (ставят ХОСТ И ВСЕ игроки один и тот же файл, иначе будет ошибка "Различные версии"):
Простой способ (рекомендуется):
1. Закройте игру и лаунчер.
2. Распакуйте этот архив в любую папку.
3. Запустите installer\install.bat двойным щелчком. Он найдёт coop.addon (или спросит путь) и добавит
   zzz_soc_coop_fixes.db одинаково на каждом ПК, поэтому у всех получится один и тот же отпечаток. Сравните отпечаток, который он выводит.
4. Начните новую игру (рекомендуется).

Вручную через 7-Zip:
1. Закройте игру и лаунчер.
2. Зайдите в X-Ray Multiplayer Extension\game\addons\
3. Откройте coop.addon через 7-Zip (ПКМ > 7-Zip > Открыть архив).
4. Перетащите zzz_soc_coop_fixes.db в окно 7-Zip, нажмите ОК и подтвердите замену старого файла.
5. Начните новую игру (рекомендуется).
Если игроки всё равно видят "Различные версии", запустите installer\install.bat на каждом ПК.

Удаление: запустите installer\install.bat -Uninstall или снова откройте coop.addon через 7-Zip и удалите zzz_soc_coop_fixes.db.

Настройки хоста (нужны только ХОСТУ, остальные ничего не делают):
Числа баланса (урон игроков, враги на каждого игрока, добыча из ящиков, части мутантов, повторяемые задания, ходящие отряды) можно менять БЕЗ переустановки.
При первом запуске игры с этим патчем хост получает файл coop_settings.ltx со всеми настройками, значениями по умолчанию и короткими комментариями:
- вы создаёте игру и играете: X-Ray Multiplayer Extension\game\_appdata_\coop_settings.ltx
- выделенный сервер:         X-Ray Multiplayer Extension\game\_appdata_server\coop_settings.ltx
Откройте файл в Блокноте, измените число (например player_damage_mult = 2.0), сохраните и смените локацию или перезапустите сервер.
Удалённая строка или неверное значение = значение по умолчанию; удалите файл целиком, чтобы получить новый. Строка "[HOSTCFG]" в логе показывает, что действует.
Остальные игроки этот файл не читают, отпечаток аддона он не меняет, кроме одной личной настройки: раздел [client] читает КАЖДЫЙ игрок из СВОЕГО coop_settings.ltx (файл создаётся при первом запуске, и у тех, кто только подключается).
  voice_language = auto | rus | eng : язык озвучки вступления Сидоровича (auto = язык вашей игры, по умолчанию; rus = русский; eng = английский).
  Если записи на этом языке нет, реплика без звука. Субтитров на экране нет.

{CHANGES_RU}
