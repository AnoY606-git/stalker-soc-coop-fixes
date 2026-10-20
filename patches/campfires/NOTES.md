# Campfires: seats around the fire, SoC guitar songs

Status 2026-10-19: written from static analysis, **untested in game** (code-only pass, no game was started).

## Report
Maintainer, with a screenshot of an industrial hall with a barrel fire and two stalkers on a bed or crates: "fix the placement of the stalkers
and how they sit, like in the original: they sit on the floor around the campfire with different animations".

## What SoC did
Scheme `kamp` (Stohe): a stalker walks to a seat on a circle around the fire (8 sectors, a patrol path gives the centre), turns to the fire and
sits on the floor. Every 15 to 25 s he changes the pose between `sit`, `sit_ass` and `sit_knee` (also eats and drinks); the circle is the same
for everybody in the camp, so the group sits around the fire and faces it. The guitar and harmonica come with the camp state machine.

## What the mod did (found in all.spawn and the job files)
The mod uses the Call of Pripyat `animpoint` scheme: a job names a `smart_cover` object (`cover_name`) of all.spawn. The stalker takes that
object's position AND its yaw. The covers near the fires are mostly `animpoint_stay_table` (a standing "at the table" cover), and the job forces
`avail_animations = sit_ass`. Result: one pose only (sit_ass), seat and facing decided by one hand-placed object, in the fire hall the objects sit
on beds and crates and many of them face away from the fire (yaw relative to the fire is spread over the whole circle, measured on the covers
within 14 m of a fire). all.spawn cannot be edited here (another patch already ships a full copy), so the covers cannot be moved.

## Update 2026-10-19 (maintainer: the screenshot is the Bar factory hall camp and the Cordon rookie village)
Bar: the covers there are `animpoint_sit_normal` / `animpoint_sit_high` objects placed on benches, beds and crates (sit_high is a raised seat), so the
stalkers sat on furniture. Fires 11, 12 and 13 now use `kamp` (table below); all three have a `camp_zone`, so guitar and harmonica work (`use_camp = true`).
Cordon: the village fires were already `kamp` (esc_smart_terrain_1_kamp.ltx, 8 seats, jobs have no `suitable`, `prior` 40). Stock jobs of that smart
terrain are only the three named NPCs, so the seats are filled by roaming stalkers; if too few sit there in game, raise `prior` or `max_population`.

## Fix
The fire-side sitting jobs now use `kamp` with `center_pos` = the campfire object position (read from all.spawn) and a radius of the old seat ring
(1.9 to 2.4 m; the seat is found on the AI map, so it is on the floor next to the fire). `scripts/xr_kamp.script` (already in this patch, from the
Cordon fix) hands out the seats, turns each stalker to the fire and changes `sit` / `sit_ass` / `sit_knee`. Job conditions, priorities, `meet`,
`invulnerable` and every story transition (`on_info`) are unchanged: only the section type changed, and `animpoint@x` references to a converted
section became `kamp@x`. Story stalkers keep `use_camp = false` (as before, they do not play music); generic ones are `true`.

| Level | Camp (fire object) | Centre x, y, z | Radius | Job files | Seats |
|---|---|---|---|---|---|
| Cordon | rookie village, 2 fires (earlier fix) | see esc_smart_terrain_1_kamp.ltx | 2.2 to 2.4 | esc_smart_terrain_1_kamp.ltx | 8 |
| Cordon | esc_campfire_0009 (bandit ruins with the idiot stalker) | 312.66, 3.45, 118.45 | 2.2 | esc_smart_terrain_9_animpoint_stalker | 3 |
| Garbage | gar_campfire_0003 (Devil, Renger, Yurik) | -60.90, -2.30, -217.87 | 2.1 | gar_smart_terrain_1_walker_yurik, _2_walker_devil, _2_walker_renger | 5 |
| Garbage | gar_campfire_0002 (Gray, Renger) | -60.98, 0.82, 5.18 | 1.9 | gar_smart_terrain_7_walker_gray, _7_walker_renger | 2 |
| Garbage | gar_campfire_0005 (Duty camp) | 47.95, 0.41, 231.19 | 1.9 | gar_smart_terrain_9_animpoint_duty | 4 |
| Bar | level_prefix_campfire (Bar fire 11) | 130.09, 0.10, 60.11 | 2.4 | bar_smart_terrain_11_animpoint_stalker | 2 |
| Bar | bar_campfire_dinamic (factory hall, fire 12; Skamarokh's guitar animpoint stays) | 98.56, 0.10, 93.14 | 2.4 | bar_smart_terrain_12_animpoint_stalker | 2 |
| Bar | bar_campfire_dinamic_0000 (fire 13) | 117.44, 0.07, 122.10 | 2.4 | bar_smart_terrain_13_animpoint_stalker | 2 |
| Army Warehouses | mil_campfire_0011 (Freedom hangar, 2 stalkers) | -58.42, -10.40, 26.28 | 2.4 | mil_smart_terrain_11_animpoint_freedom (in freedom_duty) | 2 |
| Army Warehouses | mil_campfire_0004 (Duty and Freedom ambush camp) | -235.73, -12.65, 52.49 | 1.9 | mil_smart_terrain_14_animpoint_duty, mil_smart_terrain_3_walker_freedom_ordinary (in freedom_duty) | 5 + 5 |

Files outside this folder: `mil_smart_terrain_11_animpoint_freedom.ltx` and `mil_smart_terrain_3_walker_freedom_ordinary.ltx` already belong to
`patches/freedom_duty` (one patch per file), so the edit is in that copy (its line endings, LF, are kept).

Camps checked and **left as they are**:
- Radar Monolith fires (`rad_smart_terrain_*`, `trans_0` stand pose) and the Sarcophagus preacher: not a sitting camp in the mod design.
- `*_stay_wall` covers (leaning on a wall, 6 to 12 m from the fire): intentionally not at the fire.
- Dark Valley and Rostok fire jobs in the files checked are `camper` guards on patrol paths (standing watch), not sitting jobs.

## Songs (guitar and harmonica)
Sound themes `play_guitar` / `play_harmonica` use `npc_prefix = true`, `path = music\guitar_`: the song set is the `music` folder of the NPC's
voice (`snd_config`). What the game ships (checked in the xrMPE sounds db):
- `human_01\stalker`, `human_02\stalker`: `guitar_17..27` are byte-identical to the SoC songs `guitar_1..11` (md5 checked against the SoC archive).
  Plus `guitar_30` (a 2 MB Call of Pripyat song). No harmonica.
- `human_01\bandit`: `guitar_17..27` (SoC) plus `guitar_28`, `guitar_29` (CoP).
- `human_03\csky` (Clear Sky voice, 7 characters): 28 Clear Sky songs and 6 CoP harmonica tunes.
- `human_02\newbie`: 16 CoP songs, 5 harmonica tunes (no character in the mod uses this voice).
- SoC itself: `human_01\newbie\music\guitar_1..11` and one tiny `harmonica_1` (3.8 KB).

Changes (files in `gamedata\sounds\characters_voice\...\music\`, original SoC ogg files from the SoC archive, 5.4 MB in total):
- stalker voices (`human_01`, `human_02`): `guitar_30` replaced by the SoC song `guitar_5`; added the SoC `harmonica_1`.
- `human_01\bandit`: `guitar_28`, `guitar_29` replaced by SoC songs; added the SoC `harmonica_1`.
- `human_03\csky`: `guitar_1..16` and `guitar_30` are SoC songs now; `harmonica_1..6` are the SoC harmonica file.
So every voice that has a camp song folder plays only the SoC songs. Two or three SoC songs appear twice in a set (slightly more likely), because
the engine picks every file of the folder and old CoP files cannot be deleted, only overridden. Dolg, Freedom and `human_03\stalker` voices have no
music folder in the game (unchanged, they never played a song).
No sync change: NPC sounds are not `sync` themes; the server sends the song index (`GE_STALKER_SND`) and every machine plays its own file with that
index, so all players need the same patch (as always).

## Not changed / limits
- The seat is chosen on the AI map; a fire inside a hall with little free floor falls back to the fire's own node (the script walks the radius
  down in 0.5 m steps).
- When a story section switches (for example after a dialogue) the stalker leaves the seat and takes a new one (the animpoint also restarted).
- Of the fires converted here only gar_campfire_0003 and mil_campfire_0011 have a `camp_zone` object in all.spawn (besides the Cordon and Bar
  camps), so only those can play guitar songs through `sr_camp`; the other converted fires have no camp zone and no song (a spawn edit would be needed).
- Not tested: nothing was run. Check in game: stalkers sit on the floor facing the fire at the camps in the table, poses change every 15 to 25 s,
  the story NPCs (Devil, Gray, Skull's partner, Max's partner) still react to their dialogue triggers, no `kamp` Lua error in the log.

## Кратко (RU)
В оригинале ТЧ сталкеры садятся на пол вокруг костра (схема kamp: круг, лицом к огню, позы sit / sit_ass / sit_knee, меняются). В моде у костров
стояли точки animpoint из all.spawn (стоячие столы, позы только sit_ass, направление произвольное). Теперь костры в Кордоне (две стоянки), Свалке
(3 костра), Армейских складах (2 костра) используют kamp: круг радиусом 1,9 - 2,4 м вокруг костра, лицом к огню, разные позы. Песни: у голосов
stalker и bandit гитара уже играла песни ТЧ (guitar_17..27 = guitar_1..11 ТЧ), лишние песни CoP (guitar_30, 28, 29) заменены песнями ТЧ, у csky
тоже; добавлена гармоника ТЧ. Не проверено в игре.
