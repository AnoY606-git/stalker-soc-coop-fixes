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


## Update 2026-10-20: rookie village fire, no chair sitter, SoC head count
Report (maintainer FOSTER, Cordon, the fire between the brick shed and the plastered house): about 9 stalkers around the fire, "more precisely the
one sitting on the chair"; none sits on a chair there in SoC.

### What SoC has at that fire (reference: original SoC 1.0006 `alife_l01_escape` spawn dump)
Smart terrain `esc_lager` (capacity 13): seven novices `esc_lager1..7` (character `esc_stalker_novice`), Wolf (`esc_wolf`, 4.4 m from the fire) and, only after
the quest flag `esc_fanat_spawn`, Fanatic. Next to the fire (2.6 to 3.2 m) sit `esc_lager2`, `esc_lager3`, `esc_lager5`; `esc_lager1` is 8 m, `esc_lager6`
13 m and `esc_lager7` 20 m away. Nobody sits on a chair.

### Measured before (stock v1.3 stage, listen server, 4 samples between 60 and 340 s after spawn)
Stalkers within 15 m of the fire: 10 to 13 (all online), the village smart terrain held 18 NPCs. At 60 s: 6 on `kamp` seats 1 to 6 (1.3 to 3 m), 1 on the
**chair** (`sim_default_stalker_0`, job `logic@esc_smart_terrain_1_animpoint_7`, 2.1 m from the fire), 3 standing guards (`guard_6_walk` 4.3 m, `guard_2_walk`
12 m, plus the stalker on `animpoint_8`, 12 m, sitting on the steps), Wolf (8.6 m).
Who the chair sitter is: one of the 16 generic village stalkers of the mod (squads `esc_smart_terrain_1_stalker_1..6_squad`: 3+3+3+3+2+2 members of
`sim_default_stalker_0`). He is NOT the Cordon technician (`cordon_technician`), and not from `alife_roaming` (that patch only moves squads).
The chair is the smart cover `esc_smart_terrain_1_animpoint_7` (`animpoint_sit_normal`, in all.spawn 1.7 m from the fire): the base script
`gulag_general.script` makes a generic job (prior 15) for every cover named `<smart>_animpoint_<N>`, so every cover placed by the map author is used.
The five other seated stalkers were our own `kamp` seats (this patch, six at the fire).

### Fix
1. `scripts/gulag_general.script` (copy of the xrMPE base file, the mod does not change it; verified in game that this flat file is the one loaded):
   the generic animpoint loop skips the covers listed in the smart terrain ini line `[smart_terrain] skip_animpoints = N, M`. Nothing else changed
   (3 added lines plus one `if`). Other smart terrains have no such line, so nothing changes on other levels.
2. `smart/esc_smart_terrain_1.ltx`: `skip_animpoints = 7` (the chair). Kamp seats 4 to 6 of the village fire removed (the fire keeps seats 1 to 3 = the three
   SoC novices; the second fire keeps seats 7 and 8). `esc_smart_terrain_1_kamp.ltx`: sections 4 to 6 removed.
3. `configs/misc/simulation.ltx` (file owned by `sarcophagus_count`, edited there): the village statist squads `esc_smart_terrain_1_stalker_2/3/4_squad` are
   no longer created at the start (16 generic stalkers become 7, SoC has 7 `esc_lager` novices). The squad definitions stay in `squad_descr_coop_l01_escape.ltx`.
   Wolf, Sidorovich and the guide (Globus, appears with his quest) are untouched; the rest of the Cordon squads are untouched.

### Measured after (same stage plus this fix, same run length)
Stalkers within 15 m of the fire: 4 at every sample (3 sitting on the `kamp` seats at 2.3 to 2.8 m, Wolf at 8.6 m); nobody on `animpoint_7`; the village
smart terrain holds 9 NPCs (Wolf, Sidorovich, 7 statists: 3 on the village fire, 2 on the second fire, 2 guards). Test hook: `patches/cordon/tests/fire_count.lua`
(`run_coop.ps1 -Mode listen -Clients 1`, logs `FIRE ...` lines with name, section, job, scheme, distance).

### Limits
- The stalkers that SoC places 8 to 20 m from the fire (`esc_lager1`, `6`, `7`) are on guard paths of the map now, so only 4 stand within 15 m (SoC has about 6).
- `skip_animpoints` only removes the generic job; the cover object stays in all.spawn (nobody uses it).
- The chair-free fire needs the same patch on host and clients (scripts and ltx are part of the db).

### Кратко по-русски
У костра в деревне новичков на Кордоне было 10 to 13 сталкеров, один сидел на стуле (смарт-ковёр `esc_smart_terrain_1_animpoint_7`, обычный
сталкер `sim_default_stalker_0` из 16 статистов мода; это не техник и не `alife_roaming`). В оригинальной ТЧ у костра сидят трое новичков, на стуле никто.
Исправлено: `gulag_general.script` пропускает ковры из строки `skip_animpoints` в ini смарт-террейна (для деревни: 7); мест `kamp` у главного костра теперь 3
(было 6); статистов деревни 7 вместо 16 (как `esc_lager1..7` в ТЧ; правка в `simulation.ltx` патча `sarcophagus_count`). Замер в игре: до 10 to 13 сталкеров в 15 м от
костра, после 4 (трое у костра и Волк); на стуле никого. Волк, Сидорович и проводник не тронуты.


### Follow-up 2026-10-20: chair sitters in the village houses
FOSTER's new screenshots show a rookie village house room (sofa, nightstand with a candle) with a stalker sitting on a chair and one standing at the wall.
SoC has no such stalkers anywhere in the village: the cover objects `esc_smart_terrain_1_animpoint_1..11` (CoP `animpoint_sit_normal`, `sit_high`,
`stay_wall`) were placed by the map author, and the base `gulag_general.script` turns every one of them into a generic job (prior 15). Measured before
(16 statists as in v1.3, same census as above, 390 s): 5 statists on animpoint jobs (6 and 8 `sit_normal` in the guide house and the house at the fire,
9 `sit_high`, 10 `stay_wall`, 11 `sit_normal` in the west hut); visuals `stalker_neutral_0_N` (novice models).
Fix: `skip_animpoints = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11` in `smart/esc_smart_terrain_1.ltx` (all village covers). Sidorovich (cover 3) and the guide
(cover 4) keep their exclusive jobs, which are separate job sections. After: 0 animpoint jobs at all four samples (60 to 390 s), the village holds 9 NPCs
(Wolf, Sidorovich, 5 on `kamp` seats, 2 on guard paths). Test hook `patches/cordon/tests/all_stalkers.lua` (whole-level census with job, scheme, visual).
Not proven: the exact NPC of the screenshots (no engine screenshot is possible, the harness lobby window covers the scene); the dead stalkers on the floor in
the screenshot are not part of this logic.

### Кратко (дополнение)
Все ковры `esc_smart_terrain_1_animpoint_1..11` (стулья/стены в домах деревни, нет в ТЧ) отключены строкой `skip_animpoints`; до: 5 статистов на этих заданиях,
после: 0. Сидорович и проводник не затронуты.


### Note 2026-10-21: the hooded sitter in the village cellar is the guide
FOSTER's picture of a hooded stalker sitting on an iron bed in a cellar under a village house (broken wall hole, wooden floor, wall lamp) is the level guide `esc_smart_terrain_1_stalker_guide` on the exclusive cover `esc_smart_terrain_1_animpoint_4` (-213.1, -23.2, -121.9). It is NOT a generic animpoint job (those, covers 1 to 11, are skipped above, including `_5` and `_6` that stand beside the beds of the same cellar), and the guide gives the level-travel flags, so `skip_animpoints` does not touch him and he stays. The Cordon technician stands in the same cellar since this update (see `cordon_technician/NOTES.md`).

## Update 2026-10-21: Garbage story edits that live in this patch's job files (one patch per file)
* `gar_smart_terrain_2_walker_devil.ltx` (Bes, FOSTER: after his quest the request greeting came up again). The greeting is the character's start dialog; it now only exists
  before the quest. `meet@gar_smart_terrain_2_walker_devil` (talk after the bandits are dead) sets `meet_dialog = gar_smart_terrain_4_stalker_devil_2_start_dialog` (the existing short
  line "Ну и бойня..."), and the final camp section `kamp@..._animpoint_1_no_meet` uses the new `meet@gar_smart_terrain_2_walker_devil_done` (talkable, same short line) instead of `no_meet`.
  Same `meet_dialog` mechanism the mod uses for Fox and Lucky. Not tested in game.
* `gar_smart_terrain_7_walker_gray.ltx`: only the camp sections (no Gray fight edit any more: the server gives the fight info when a player is near, see `garbage_gray\NOTES.md`).
* `gar_smart_terrain_9_animpoint_duty.ltx`: jobs take `check_npc_name(gar_dolg_blokpost)` (see `garbage_duty\NOTES.md`).

## Update 2026-10-21: Seriy and Bes wait for the arrival (patch garbage_soc_quests)
`gar_smart_terrain_7_walker_gray.ltx` and `gar_smart_terrain_2_walker_devil.ltx`: the first state now leaves for `..._idle` on `GAR_WAITING_FOR_THE_ORDER_TO_KILL_YURIK_INFO` (the arrival) instead of waiting for Bes's job / the Yurik outcome. The level maker's radio calls (`grey_grey_1`, `neutrals_commander_pda_1`, not used by SoC) and the step "help the Gray fight off the bandits" are no longer reached (their sections stay for old saves). Seriy's fight is unchanged. See `garbage_soc_quests\NOTES.md`.


## Update 2026-10-21: stalkers walking on the spot / on top of each other at the fires (report on v1.4)
Report (FOSTER, Cordon rookie village, barrel fire with a stool, blue bus behind the fence): stalkers stand at the fire in walking poses, "they try to
go somewhere and cannot"; two stand on top of each other next to the stool, one stands frozen on the other side.

### Cause (offline analysis, no game; the job count is NOT the problem)
- Jobs are plentiful. `tools\check_camp_jobs.py`: the village smart terrain `esc_smart_terrain_1` has 31 slots for stalkers (5 kamp seats, 6 guard paths, the 20
  `point` jobs every smart terrain has) for 10 stalkers (9 at start, up to 12 with a late squad, roaming cap 10); enemy scaling only touches hostile factions, the
  village dwellers are neutral. Every smart terrain with a fire has more slots than people.
- The seat logic of `xr_kamp.script` was brittle. A stalker only counted as seated when his AI node was EXACTLY the seat node (`level_vertex_id() == pos_vertex`),
  and the seat node was a random sector of the circle that nobody checked: (1) when the sector has no AI node (the map has holes where the building / bus stand) the
  script fell back to the fire's own node, which is inside the barrel; several sectors fall back to the same node, so stalkers walk at the barrel for ever, on top of
  each other; (2) a node next to a stool, bench or crate is reachable on the map but not for the body, and the stalker pushes against it for ever; (3) two seats could be
  the same node or neighbours (0.7 m apart). Nothing ever gave up or chose another seat. The second village fire (`esc_campfire_0000`, the west half of its ring is a
  building) is the worst: with the v1.4 rule a seat falls on the barrel node in 64 % of the starts (`tools\check_camp_seats.py`); the Bar fire 13 and the Army Warehouses
  camp (10 stalkers on a 1.9 m circle that holds 8 seats) have the same kind of problem, the Garbage fires put two seats under 1 m apart in 40 % of the starts.
- Reproduced with the REAL script in a Lua VM on the REAL AI maps (`tests\kamp_seat_mock_test.py`, solid barrel and stool, stalkers pushed out to the rim). v1.4 script,
  runs with a stalker that never sits down: second village fire 24 %, Bar fire 13 about 10 %, a village fire with obstacles the script does not know about 79 %; Army
  Warehouses camp: two stalkers within 0.5 m in 99 % of the runs. With the fix: 0 in every scene.

### Fix
- `scripts\xr_kamp.script`: a seat is a free node of the ring that is (a) not within 1.3 m of the fire, (b) not within `r` of an `avoid` point (new optional line
  `avoid = x, y, z, r | ...` of the kamp section: the stool / bench covers of the map, written by `tools\check_camp_seats.py --fix`), (c) not within 1.1 m of the seat of any
  other stalker of the same fire, (d) on the floor of the fire (2 m). The stalker looks in his own sector first, then anywhere on the ring. A stalker who stands within 1 m
  of his seat for 2.5 s counts as arrived; one who moved less than 0.3 m in 5 s is stuck: the spot is remembered as blocked (with 1 m around it, for 5 minutes) and he gets
  another seat, up to 3 times; after that he sits down where he stands. Nobody walks in place any more.
- `avoid` entries: the village fire (the stool `esc_smart_terrain_1_animpoint_7`) and the Bar fires 11, 12, 13 (the benches the old animpoint jobs used).
- Army Warehouses camp (`mil_campfire_0004`, 10 stalkers): radius 1.9 to 2.5 (also in `freedom_duty\...\mil_smart_terrain_3_walker_freedom_ordinary.ltx`), the circle holds 10
  seats 1.1 m apart.
- "3 at the fire, nobody on chairs, 7 extras" is unchanged (jobs, `skip_animpoints`, squads untouched).

### Checks (offline, seconds)
`python tools\check_camp_seats.py` (every fire of the merged configs against its level.ai: node at the fire, empty sectors, seats that fit, furniture without `avoid`),
`python tools\check_camp_jobs.py` (job slots vs stalkers per smart terrain), `python tests\kamp_seat_mock_test.py --ai-root <dir> --old tests\xr_kamp_v1.4.script.txt --all-camps`
(the real script, old and new, every fire), `python tests\village_npcs_mock_test.py` (the in-game hook against a mock), plus `check_conflicts.py`, `luabal.py` and the build budget.
In game: `tests\village_npcs.lua` (listen mode, from 120 s on every NPC of the village smart terrain: has a job, kamp stalkers sit within 1.3 m of the seat, nobody that wants
to move stays within 0.3 m for 20 s, no two online NPCs closer than 0.5 m; logs `VILLAGE ...` lines with job and scheme). Not run in the game yet.
Not touched: the `cover` point jobs (random spot 3 to 8 m around the smart terrain) and the guard jobs; if the hook still finds a stuck NPC, its log line names the job and scheme.

### Кратко (RU)
Причина: место у костра выбиралось случайно на круге, а сталкер считался севшим, только если стоял точно в узле AI-карты. Если в секторе нет узлов (второй костёр деревни: половина
круга это здание), место падало на узел самого костра (внутри бочки), сталкеры упирались в бочку на одном месте; узел у табурета или скамьи недостижим для тела; два места могли
совпасть. Теперь место свободное, не ближе 1,3 м к костру, не у табурета или скамьи (строка `avoid`), не ближе 1,1 м к чужому месту; застрявший берёт другое место, потом садится где
стоит. Работ хватает (31 на 10 сталкеров). Проверено офлайн настоящим скриптом на настоящих картах AI: до исправления у второго костра 24 % запусков со сталкером, вечно идущим на месте, после 0.
