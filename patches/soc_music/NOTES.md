# SoC music - notes

## Problem
Compared with the original Shadow of Chernobyl files (durations measured with ffprobe):
- Bar "100 Rads" radio: the mod plays 4 tracks that are not from SoC (116, 199, 160, 244 s, `bar_radio_barmen_1..4`).
  SoC plays one track, `characters_voice\scenario\bar\radio_music\radio_music_1` (237 s).
- Main menu: the mod's `music\menu` is 285 s; the SoC menu music is 125 s.
- Level ambient music (`music\coop_*_music\ambNN`) already uses the SoC tracks with the SoC level assignment (same lengths), nothing to change.

## Fix
- `gamedata\sounds\characters_voice\scenario\bar\radio_music\bar_radio_soc_1.ogg`: the SoC Bar radio track.
- `gamedata\sounds\music\menu.ogg`: the SoC menu music.
- New sound theme `bar_radio_soc` (`sync = true`, so every client hears it), added to `patches\bar_speaker\...\script_sound_coop_l05_bar.ltx` (only one patch may ship that file).
- `gamedata\configs\scripts\coop_l05_bar\bar_radio_barmen.ltx`: the radio plays `bar_radio_soc`, then again 2 s after it ends
  (SoC played its radio track continuously). Real-time `on_timer` instead of `on_game_timer`, because the game clock does not advance on a dedicated server.

## Also fixed
`patches\bar_speaker` sound paths contained a backspace character instead of `\b` (`coop_l05_bar<BS>ar_megafon_...`), so none of its themes could load files.

## Test (Cordon, dedicated server + 1 client)
PASS: radio track loads, 236915 ms; menu music loads, 125127 ms; theme `bar_radio_soc` registered; bar_speaker paths intact.
Not run: listening on the Bar level itself (the radio restrictor needs the Bar online).

## Кратко (RU)
Вернули оригинальную музыку ТЧ: песня радио в баре «100 рентген» и музыка главного меню. Фоновая музыка локаций уже была из ТЧ.
