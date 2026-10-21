# cordon_megafon - notes

Offline fix, written 2026-10-21. Not yet run in the game: see "Live test plan" below (a hook is in `tests\megafon_hooks.lua`, not shipped).

## Problem (FOSTER)
The army checkpoint loudspeaker on Cordon (soldiers' announcements and the siren) is far too loud; it is audible even past the rookie village
(about 225 m away: speaker `esc_rupor` at (-141.8, -22.8, -353.9), rookie fire `esc_smart_terrain_1_5_camp` at (-196.0, -19.5, -136.2)).

## Cause
1. The add-on's ogg files carry their own 3D parameters in the first vorbis comment (a binary block: version, min distance, max distance,
   volume, game sound type, AI distance; the engine reads it in `CSoundRender_Source::load`, without it the log says "Missing ogg-comment" and
   min 1 / max 300 apply). Measured with `tools\ogg_xray_comment.py show`:

   | file (`sounds\characters_voice\radio_music\coop_l01_escape\`) | add-on | original SoC (same role) |
   |---|---|---|
   | megafon_1..4.ogg | min 40, max 500, vol 1.0 | `scenario\escape\megafon_1..4` (theme "epic"): min 10, max 400, vol 1.0 |
   | esc_sirena.ogg (byte-identical audio size to SoC `ambient\siren1`) | min 40, max 500, vol 1.0 | `ambient\siren1/siren2` (theme "siren"): min 20, max 400, vol 1.0 |

   The engine attenuates 3D sounds with the inverse distance law from the minimum distance: gain = min / distance (about, rolloff factor 1).
   With min 40 instead of 10 the speaker is 4x (12 dB) louder at every distance past 40 m:

   | distance | add-on min 40 | SoC megafon min 10 | SoC siren min 20 |
   |---|---|---|---|
   | 50 m | 0.80 (-2 dB) | 0.20 (-14 dB) | 0.40 (-8 dB) |
   | 100 m | 0.40 (-8 dB) | 0.10 (-20 dB) | 0.20 (-14 dB) |
   | 150 m | 0.27 (-11 dB) | 0.07 (-24 dB) | 0.13 (-18 dB) |
   | 225 m (rookie village) | 0.18 (-15 dB) | 0.04 (-27 dB) | 0.09 (-21 dB) |

2. `configs\scripts\coop_l01_escape\space_restrictors\esc_rupor_space_restrictor.ltx` starts the themes `megafon` and `esc_sirena` as soon as a
   player is within 350 m of the speaker (`dist_to_actor_le(350)`, nearest player). In SoC there is no such gate: the speaker object plays
   as long as it is online, and the alife switch distance is 150 m (`alife.ltx`, `switch_distance = 150`).

## Fix
- Our copies of the five ogg files: the audio is the add-on's own (decoded PCM md5 identical before and after, the speech is not the SoC
  speech), only the comment block is rewritten: megafon_1..4 min 10 / max 400 / vol 1.0, esc_sirena min 20 / max 400 / vol 1.0, which are the SoC
  values of the same role. Game sound type (0x08000080) and AI distance (2 m, nobody reacts to it) are kept as they were.
- `esc_rupor_space_restrictor.ltx`: both `dist_to_actor_le(350)` -> `dist_to_actor_le(150)` (SoC: playing while the speaker is online, 150 m).
  Nothing else in the file changed (CRLF, tabs and the missing final newline are kept).
- The same two sound themes are also used by `agr_rupor_space_restrictor` on Agroprom, so the quieter ogg files apply there too. Its gate
  (350 m) was not touched, it is not part of this report.

## Proof (offline)
`python -I tools\ogg_xray_comment.py show <dir>` before and after (also: every Ogg page CRC valid, `ffmpeg -f md5` of the decoded audio unchanged):

| file | before | after |
|---|---|---|
| megafon_1..4.ogg | v3 min 40 max 500 vol 1.00 type 134217856 ai 2.0 | v3 min 10 max 400 vol 1.00 type 134217856 ai 2.0 |
| esc_sirena.ogg | v3 min 40 max 500 vol 1.00 type 134217856 ai 2.0 | v3 min 20 max 400 vol 1.00 type 134217856 ai 2.0 |

`tools\check_conflicts.py`: no new shared file (this patch is the only one that ships these six files; `esc_sirena_space_restrictor.ltx`
in `any_player_restrictors` is a different file). Build with the usual skip list: BUDGET OK.

## Live test plan (one listen-host run, `tests\megafon_hooks.lua`)
1. Run `run_coop.ps1 -Map coop_l01_escape -Mode listen -Hooks tests\megafon_hooks.lua -ExtraDir <stage>\gamedata`; once with the patch and once without (the
   baseline shows min 40 / max 500 in the probe line and the theme starting in the village).
2. The hook logs once a second in `qa_events.log` (`MEGAFON probe`): distance of the nearest player to the speaker, `playing` of the themes `megafon` and
   `esc_sirena`, and the sound object's `min_distance / max_distance / volume` (what the engine took from the ogg).
3. Walk: teleport to the rookie village (225 m) and wait 45 s -> the theme must not start (assert). Teleport 100 m from the speaker, wait 60 s ->
   the theme must start (assert) and the logged params must be `min 10.0 max 400.0`.
4. Manual by console (if wanted): teleport to the village and to the checkpoint and listen; the speaker should be faint at 100 to 150 m
   and clear at the checkpoint.
5. Engine log: no "Missing ogg-comment" / "Invalid ogg-comment version" line for these files.

## По-русски
Громкоговоритель блокпоста на Кордоне был слишком громким (слышен даже за деревней новичков, около 225 м). Причина: в ogg-файлах мода
(`megafon_1..4`, `esc_sirena`) в комментарии записаны мин. дистанция 40 м и макс. 500 м, а в оригинальной ТЧ мин. 10 м / макс. 400 м
(сирена 20 / 400). Громкость падает как мин/расстояние, поэтому у мода было в 4 раза (12 дБ) громче. Кроме того, триггер
`esc_rupor_space_restrictor` включал звук за 350 м, в ТЧ звук идет, пока объект онлайн (150 м).
Исправлено: в ogg переписаны параметры как в ТЧ (звук не менялся), триггер 350 -> 150 м. Эти же темы использует Агропром (громкость там
тоже стала как в ТЧ, триггер не менялся).
