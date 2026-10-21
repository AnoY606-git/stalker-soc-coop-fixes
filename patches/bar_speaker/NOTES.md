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

## What changed (round 2: SoC loudspeaker behaviour, FOSTER: "the music does not play like in the original")
SoC has ONE Duty loudspeaker, the physic object `dolg_megafon` at (158.0, 13.7, 115.6), ogg tags min 30 m / max 300 m (heard over the whole Bar).
The add-on has that object (`bar_dolg_megafone`) plus two more `rupor` objects with the same cfg (`bar_dolg_megafone_0000` at (158.1, 5.3, 66.6) and
`_0001` at (105.5, 4.9, 114.8)). A sound theme is ONE shared state object (`can_play_sound`, `played_id`): the three speakers fought over it, in the
measured v1.3 run only `_0000` ever spoke and the real speaker stayed silent. Round 1 also used 7 long non-SoC tracks (145 to 315 s) in a FIXED order
with FIXED pauses.

| | SoC | v1.3 (measured) | now |
|---|---|---|---|
| speakers | 1 (158.0, 13.7, 115.6) | 3 objects, one theme: only `_0000` spoke | only `bar_dolg_megafone` speaks (the other two stay silent) |
| pool | 7 phrases + 3 `megafon_music_1..3` (66, 70, 75 s) | 10 phrases + 7 non-SoC tracks | 9 add-on phrases + the 3 SoC `megafon_music_1..3` |
| order | random, never the same twice in a row | fixed sequence | random, never the same twice (`select_next_sound`) |
| pause | random 5-15 s after each | fixed 5/7/9/12/15 s | random 5-15 s after each (theme `idle = 5,15`) |
| range / volume | ogg tags (min 30, max 300) | same | same |
| sync | n/a | server starts, clients play | same, checked on a client |

- `configs\scripts\coop_l05_bar\bar_dolg_megafone.ltx`: `sr_idle` asks for the theme `bar_dolg_speech` every 0.5 s, only for the object whose name ends in
  `megafone` (`check_npc_name(megafone$)`); the theme enforces the pause. Stub sections `sr_idle@s0..s20` / `@p0..p20` of round 1 stay, each going back
  to `sr_idle`: a saved game stores the name of the active section and a missing one crashes the load.
- `configs\misc\script_sound_coop_l05_bar.ltx`: theme `bar_dolg_speech` (`sync = true`, `idle = 5,15,100`); the round 1 themes `bar_megafon_speech` and
  `bar_megafon_music_1..7` are gone. `bar_radio_soc` is `rnd` (see soc_music).
- `sounds\...\coop_l05_bar\bar_megafon_speech_1..9.ogg`: the add-on phrases (`bar_megafon_1, 2, 19..25`; `_18` was a byte-identical copy of `_2` and is dropped,
  it doubled that phrase's chance); `bar_megafon_speech_10..12.ogg` = SoC `megafon_music_1..3` (0.9 MB). The add-on's own long tracks are no longer played.
- The phrases are the add-on's own recordings (their length differs from the Steam SoC `megaphone_barman` / `mega_duty_propaganda` files, probably another
  voice language); they were kept because I cannot tell which add-on phrase is which SoC line. Replace them if the exact SoC lines are wanted.
- Not restored: SoC's arena / territory-hit / alarm / "bar_start_megafon" announcements from the same speaker. They need infos (`bar_arena_start`, `bar_territory_*`)
  and a restrictor (`bar_start_megafon`) that the add-on's arena does not have.

## How tested
Live session from the `bar_arrival` save (dedicated server + 1 client), observer logs in `patches\soc_music\tests\` (`fixed_server_log.txt`, `fixed_client_log.txt`,
`baseline_v13_server_log.txt`).
- Server log, only `bar_dolg_megafone` (id 3459, (158.0, 13.7, 115.6)) played: file #10 (SoC music 1, 24.0 s seen), pause 6.1 s, #3, pause 10.9 s, #11 (SoC music 2, 70.6 s),
  pause 16.0 s (15 s + 0.5 s poll + detection), #7, pause 15.1 s, #12 (SoC music 3). Random order, no immediate repeat, pauses in 5-15 s, extra speakers silent.
- The client logged the same files in the same order (#3, #11, #7, #12), `start_from=nil` (live events).
- A v1.3 save loads without a script error.
- Not exercised: a client joining in the middle of a pause (the stock net-spawn path would start the already finished phrase at an offset; one real client fits this PC).

## Кратко (RU)
Громкоговоритель Долга в баре теперь как в ТЧ: один динамик (раньше три делили одно состояние, говорил не тот), случайный порядок без повтора подряд,
случайная пауза 5-15 с, музыка только оригинальная (megafon_music_1..3), у всех игроков синхронно. Объявления про арену и тревогу не возвращены (в моде нет их условий).
