# Bar loudspeaker repeats one phrase (coop_l05_bar)

## Root cause
The Bar loudspeaker object runs `configs\scripts\coop_l05_bar\bar_dolg_megafone.ltx`. The add-on replaced the original
SoC logic with a one-theme restrictor loop (lines 1-9):

    [sr_idle]       on_info = {...=dist_to_actor_le(150)} sr_idle@wait %=play_sound(bar_megafon)%
    [sr_idle@wait]  on_game_timer = 150 | sr_idle

and the theme `bar_megafon` (`configs\misc\script_sound.ltx:563`, `idle = 1,1,20`, `shuffle = rnd`) builds its file
list in `sound_theme.script` (`object_sound:__init`) with `while exist(path..num..".ogg") do num = num + 1`, i.e. it
stops at the first missing number. The add-on ships `bar_megafon_1, 2, 4, 5, 7, 12, 14, 15, 16, 18..25` (17 files,
the announcements AND the long music tracks of the original SoC `dolg_speech` list, with gaps), so the theme only
ever contains files 1 and 2 (two short announcements, 12 s and 19 s). With two entries the "random, never the same
twice" picker (`select_next_sound`) simply alternates 1,2,1,2, after only a 1 s idle: the Duty phrase plays non-stop.
The 15 other files (music and the other announcements) can never be reached. The theme is also not `sync`, so
the phrase is played by the server process only.

Original SoC (ixray-1.0-stsoc, `gamedata\config\scripts\bar_dolg_megafone.ltx`, `scripts\sound_theme.script`):
`[ph_sound@idle] snd = dolg_speech, min_idle = 5000, max_idle = 15000`, where `dolg_speech` is a list of 10 files
(2 barman megaphone phrases, 5 Duty propaganda phrases, 3 `megafon_music_*` tracks) played in random order with a
5-15 s pause after each, until the arena / alarm / territory-hit sections interrupt it.

## What changed
- `configs\scripts\coop_l05_bar\bar_dolg_megafone.ltx`: state machine, no distance gate (the speaker keeps its
  cycle for everybody, the 3D sound is attenuated by distance as before):
  announcement -> pause (5-15 s) -> announcement -> pause -> music track k -> pause -> ..., through all 7 tracks and
  then around again. A state ends on the theme's `sound_end` signal, the pause is an `on_timer`. The old
  `bar_player_music_info` / `bar_megafon_alarm` infos still stop the cycle (it restarts from `[sr_idle]`).
- `configs\misc\script_sound_coop_l05_bar.ltx`: new themes `bar_megafon_speech` (random of 10 announcements) and
  `bar_megafon_music_1..7` (one long track each), all `sync = true` so every client hears the same sound. The old
  `bar_megafon` theme is left in place (unused).
- `sounds\...\coop_l05_bar\bar_megafon_speech_1..10.ogg`: copies of `bar_megafon_1, 2, 18..25` renumbered without
  gaps (0.7 MB), so the loader sees one contiguous list. The music files are used in place.
- Not touched: `bar_radio_*`, `bar_rupor_arena` (same loop style, separate objects), the arena commentator.

## How tested
See the bottom of this file (test log).
