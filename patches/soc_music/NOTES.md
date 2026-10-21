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
- Sound theme `bar_radio_soc` (`sync = true`, so every client hears it), in `patches\bar_speaker\...\script_sound_coop_l05_bar.ltx`
  (only one patch may ship that file). It is `shuffle = rnd`: the first version used `seq`, and a one-file `seq` theme returns "no sound" after
  its first play (`select_next_sound`), so the radio played ONE time per session and then never again.

## Bar radio: SoC against the add-on (round 2, FOSTER: "the music does not play like in the original")
SoC (`bar_radio.ltx`: `[ph_sound1] snd = radio_music`, no conditions; `ph_sound.script`: no min/max idle, `play_at_pos` on the object):
one radio object `bar_radio` at (128.1, -2.9, 19.4); it plays its single track `radio_music_1` (237 s, ogg tags min 2 m, max 30 m, volume 2.0)
again and again as soon as the object is online; no pause, nothing stops it, no player distance gate, 3D at the object.

| | SoC | add-on v1.3 (measured) | now |
|---|---|---|---|
| tracks | radio_music_1 only | SoC track, but only ONCE per session, then silence forever (`seq` theme) | SoC track in a loop |
| when it starts | object online | only when a player stands within 15 m (`dist_to_actor_le(15)`) | object online (started with players 60 m away) |
| gap between plays | none | never replayed (the first version also waited 2 s) | 0.25 s (poll interval of the logic) |
| audible range | 30 m (ogg tag) | 15 m | 30 m (ogg tag) |
| other radios | none | `bar_radio_hunter` (109.3, 1.7, 72.1): 4 add-on tracks, 15 m gate; `bar_rupor_arena` (151.7, -14.6, 73.8): add-on track | silent (SoC has neither) |
| sync | n/a | server starts it, clients play (works) | same, checked on a client |

Files: `configs\scripts\coop_l05_bar\bar_radio_barmen.ltx` (the SoC radio object: asks for `bar_radio_soc` every 250 ms; `play_sound` ignores the call
while it plays, so the track restarts 0.25 s after it ends), `bar_radio_hunter.ltx` and `bar_rupor_arena.ltx` (silent).
All three keep the section names of the earlier versions as "go back to `sr_idle`" stubs: a saved game stores the name of the active section and
a missing one crashes the load ("restoring active section sr_idle@nil", seen in a test). A v1.3 save of the Bar loads with this patch.
Level ambient music: unchanged (already the SoC tracks and level assignment).

Not SoC and left alone (owner decides): the Skamarokh guitar NPC (ordered through a dialog), the stalker guitar/harmonica at the Bar fires.
The Duty loudspeaker is in `patches\bar_speaker\NOTES.md`.

## Also fixed
`patches\bar_speaker` sound paths contained a backspace character instead of `\b` (`coop_l05_bar<BS>ar_megafon_...`), so none of its themes could load files.

## Test (Bar, live session from the `bar_arrival` save, dedicated server + 1 client; logs in `tests\`)
Observer: `tests\obs_server.lua` (server: start/end of every object sound, theme, file, object position) and `tests\obs_client.lua` (client: the
`play_snd_obj_on_client` calls and the client sound objects). Before = v1.3 stage (`tests\baseline_v13_server_log.txt`), after = this patch (`tests\fixed_*_log.txt`).
- Before: the radio started only after the players stood within 15 m, played its 237 s once, then `sr_idle@play` stayed forever and nothing played again
  (checked 25 s after the end).
- After: the radio ran at once with the players 60 m away, object `bar_radio_barmen` at (128.1, -2.9, 19.4), file `bar_radio_soc_1`; track end t=255716, next start
  t=255970 (254 ms). The client got the same event (`BMC PLAY ... bar_radio_soc ... pos 128.1,-2.9,19.4`). `bar_radio_hunter` and `bar_rupor_arena` never started a sound.
- A v1.3 save loads (stub sections), no script error.
- Not exercised: a second client joining while the radio plays (the stock net-spawn path starts it at the running offset; only one real client fits this PC).

## Кратко (RU)
Вернули оригинальную музыку ТЧ: радио в баре «100 рентген» и музыку главного меню. Фоновая музыка локаций уже была из ТЧ.
Раунд 2 (жалоба FOSTER про музыку в баре): радио раньше играло один раз и замолкало навсегда, и только если игрок ближе 15 м. Теперь, как в ТЧ:
один трек радио по кругу, пока объект онлайн, слышно на 30 м (тег ogg), у всех игроков. Лишние радио мода (у охотника, у арены) выключены: в ТЧ их нет.
