# SoC economy, artifacts, damage and weapon zones - notes

Status: the damage multiplier (section A) was run and measured in game on 2026-10-20 (listen server, Cordon). The rest is code and config written from static analysis.

## Where the SoC values come from
The reference folder `soc_ai_port\extracted\src` holds no weapon, ammo or outfit configs, so the values were read
(read only, nothing copied into the repo) from the original S.T.A.L.K.E.R.: Shadow of Chernobyl game files: the plain-text
`configs\weapons`, `configs\misc\outfit` and `configs\misc\trade` sections inside its `gamedata.dbb`/`gamedata.dba`.
The numbers below are the SoC values; the files in the patch are edited copies of the mod's own files.

Damage and price values are on hold (see Task 2); nothing in this patch changes them.

## Task 1: only SoC artifacts, and detectors

What was found:
- Every artifact exists twice: the CoP `af_x` (artefacts.ltx, twice the SoC price) and the SoC twin `af_x_soc` (artefacts_soc.ltx).
- The world (all.spawn) places the plain ids (for example `esc_af_medusa`, `ros_af_eye`: 26 af_medusa, 17 af_vyvert, 8 af_eye, 7 af_fire,
  6 af_baloon, 3 af_ice ...), stashes and loot already use the `_soc` ids. NPC corpse loot tables (death_items_*) list artifacts with chance 0.
  The anomaly zone configs (`zones\*.ltx`) carry no artifact lists; the lists are baked into the binary all.spawn and cannot be edited here.
- So the removal is done on the item sections instead: wherever the world or a quest uses a plain id, the item now *is* the SoC artifact.

Change (`patches\no_mp_items\...\misc\artefacts.ltx`, file already shipped by that patch):
- The 24 CoP bodies were removed and replaced by one-line aliases at the end of the file, for example `[af_medusa]:af_medusa_soc`.
  Same id (quests, spawns and `dialogs_item.script` keep working), SoC name, model, cost, effects and absorption.
- 17 twins: medusa, cristall_flower, night_star, vyvert, gravi, gold_fish, cristall, blood, mincer_meat, soul, electra_sparkler, electra_flash,
  electra_moonlight, fireball, fuzz_kolobok, dummy_battery, dummy_glassbeads -> `_soc` twin.
- 7 CoP-only artifacts, mapped to the SoC artifact closest in price tier and effect (they still exist as ids because all.spawn places them):
  af_eye -> af_gravi_soc, af_fire -> af_gold_fish_soc, af_ice -> af_electra_moonlight_soc, af_baloon -> af_cristall_soc,
  af_glass -> af_soul_soc, af_mica -> af_ameba_mica_soc, af_dummy_dummy -> af_dummy_pellicle_soc.
  Side effect: the Yantar quest item `af_eye` now shows the name and icon of the Gravi artifact (the hand-in still works, it checks the id).
- `af_compass` and `af_oasis_heart` (CoP quest artifacts, not placed in any coop level) were left as they are.
- The `*_absorbation` sections stay (items_mp.ltx refers to `af_electra_flash_absorbation`).
- Removed from lists: nothing. The trader buy/sell lists keep both ids because world-placed plain artifacts must stay sellable; they now sell as SoC artifacts.
  Miser (Army Warehouses trader) only listed the plain ids, so the 26 `_soc` ids were added to his buy and sell lists (same 0.88 / 2,2 as his plain lines).
- Checked offline: the flattened artefacts.ltx has no duplicate section and every parent is defined before its child; the set of section names is unchanged.

Detectors (the CoP engine only shows artifacts to a player with a detector in hand):
| Trader | Now sells |
|---|---|
| Sidorovich (esc) | detector_simple (cost 500) |
| Barman (bar) | detector_simple, detector_advanced (1000) |
| Petrenko (bar, Duty) | detector_advanced |
| Sakharov (yan) | detector_advanced, detector_elite (2000) |
Each is in `[supplies_start]` (count 1, chance 1.0) and the `NO TRADE` line in `[trade_generic_sell]` became `= 1, 3`. Miser and detector_scientific are unchanged.
Files: `patches\soc_economy\...\misc\trade\*.ltx` (Sidorovich, Barman, Petrenko, Miser) and, in place, `patches\yantar_restore\...\trade\yan_smart_terrain_1_ecolog_saharov.ltx`.

## Task 2: SoC damage and prices - REJECTED by the maintainer, all edits reverted (tables kept as information only)
The maintainer rejected SoC values for damage and prices (tuning is done by A below instead). No damage, HP or price
value is changed by this patch. The weapon files, `weapons.ltx`, outfit costs and trader price factors that were edited earlier were restored to the mod's values
(the soc_economy copies were deleted; values in weapon_upgrades, val_special_scope, bandit_jacket and marked_one were set back).
The trader files keep only the detector and Miser artifact edits from task 1.

Findings kept for the decision (original SoC values, stalker difficulty, damage per shot = hit_power x ammo k_hit, mod -> SoC):
AK-74 0.43 -> 0.39, AK-74U 0.31 -> 0.36, LR-300 0.30 -> 0.48, SIG-550 0.35 -> 0.52, L85 0.32 -> 0.44, G36 0.23 -> 0.54, FN2000 0.33 -> 0.64,
SVD 1.0 -> 0.90, Val 0.70 -> 0.62, PM 0.55 -> 0.34, Walther 0.66 -> 0.35, USP 0.75 -> 0.46, shotgun slug 1.4 -> 0.8-0.9.
The mod keeps hit_power near 1.0 and cuts ammo k_hit to 0.3-0.65 (AP ammo is weaker than FMJ); SoC keeps k_hit near 1 and hit_power 0.3-0.6.
Prices: the mod sells every gun and suit at factor `2, 3` of the item cost, SoC uses `1, 3` for most items; SoC base costs are lower for guns
(AK-74 2000 vs 3300, MP5 1100 vs 3600) but higher for most suits (stalker suit 15000 vs 5000, exo 50000 vs 35000).
The edit scripts and the full SoC value list are in the session scratchpad (economy_soc) and can be re-applied after the decision.

## A. One global player damage multiplier (`configs\misc\coop_balance.ltx`, `[damage] player_damage_mult = 1.5`)
Players' weapons deal `mult` times the damage to every NPC and mutant. 1.0 = off; the maintainer tunes the number (+0.5 to +1.0 means 1.5 to 2.0).
How: `scripts\coop_balance.script`, function `on_npc_hit`, is called as the first line of the two hit callbacks that cover every NPC and mutant:
`motivator_binder:hit_callback` (all stalkers, `scripts\xr_motivator.script`, copy of the xrMPE one with one line added) and
`generic_object_binder:hit_callback` (all monsters, `bind_monster.script`, one line added). If the attacker (`who`) is a player (`db.mp_actors`)
and the target is alive and not invulnerable, the hits of one burst are collected; about 0.12 s after the last one (the engine has applied them by then)
`(mult - 1) * (health the burst really took)` more health is removed. If that would kill the target, a real
fire-wound `hit()` with the player as draftsman is applied instead, so death, loot and kill credit run through the normal paths.
Why this way (instead of immunity factors): the immunity sections are static config, cannot read one tunable number, and would also change
NPC-versus-NPC fights; a per-NPC binder callback gets the attacker, so only players' shots are boosted and the value is read from one ltx at server start.
Why not a second `set_callback(callback.hit)`: it would replace the binder's own callback (a game_object has one slot), breaking wounded/combat logic.
`cb.log` (logs folder) lists errors and the config line.

### v1.4 fix: the multiplier healed the target (found 2026-10-20, FOSTER: "12 PM rounds to the body, 2-3 to the head")
Measured in the game (listen server, Cordon, scripted hits of one PM round, hit power 0.89 x k_hit 0.62 = 0.55, attacker = the player):
- The callback `amount` is hit power x 100 (55.18 for 0.5518) and the callback runs BEFORE the engine applies the hit (health is still 1.0 inside it).
- The script property `health` is RELATIVE in this engine: `obj.health = 0.8` adds 0.8, `obj.health = -0.2` took 1.0 to 0.8 (vanilla scripts hurt with
  `db.actor.health = -0.05`). The first version wrote `obj.health = hp - extra`, i.e. it healed the target by about its whole health on every
  player hit, which cancels the hit: a chest shot with x1.5 left the bandit at 100% in 9 hits out of 9 (fixed point about 70% health). Only head, leg and arm
  hits, which take more than that, killed him: that is the "12 rounds to the body, 2-3 to the head" report. The same code ran for mutants.
- Now the extra is taken off after the engine's own damage as a negative number and is proportional to the damage that really happened, so bone scale
  (head x3, hand x0.1), armor and immunities still count. The `hit_amount_scale` setting is gone (the fix does not need it).
- Other things checked and found fine: NPC health regeneration is off in this build (a wounded bandit stayed at 0.5861 for 10 s, although
  `satiety_health_v = 0.1` in the config; SoC has 0.0), `player_scaling` does not change NPC toughness at all (it only adds members and reinforcement squads,
  so the two never cancel; with one player `player_count` = 1, mp_actors = get_players_count = 1; a dead player or spectator is not counted).

Hits needed to kill a Cordon bandit (`sim_default_bandit_0`, no armor) with PM-sized hits, one per second, 1 player, same test before/after the fix:
| player_damage_mult | body (spine1), before | body, after | head, before | head, after |
|---|---|---|---|---|
| 1.0 (off) | 3 | 3 | 1 | 1 |
| 1.25 | never (9 hits: health stays 100%) | 3 | - | - |
| 1.5 (shipped) | never (9 hits: health stays 100%) | 2 | 2 | 1 |
| 2.0 | never (9 hits) | 2 | - | - |
Stock mod without any fix patch (measured separately, same test): 3 body hits / 1 head. v1.3 (x1.5): body never / head 2. Fixed (x1.5): 2 / 1.
The v1.3 release was checked file by file: the only damage-relevant changes in it are `coop_balance` and its two hook lines; it ships no ammo
section and no weapon hit values (`w_val.ltx` differs from the mod only in two bone lists), `player_scaling` only adds NPCs. So there is no reason to
raise `hit_power` of the guns: that would also raise what NPCs deal to players, while `player_damage_mult` is a single player-only knob for all guns.
The 3rd body hit at x1.0 and the 2nd at x1.5 are the finishing hit on a wounded NPC (health under about 0.2). Limbs at x1.5: hand never dies in 9
hits (x0.1 bone scale), arm and calf 5 hits (before: never).

SoC compared (original game files; PM, stalker difficulty): hit_power 0.34 (0.30/0.34/0.37/0.40 by difficulty) x ammo k_hit 1.0 = 0.34 per round vs 0.55 here;
bone scale spine 1.0, spine1/spine2 0.5, pelvis 1.0, head 2.0 (SoC `stalker_damage`) vs 0.75 and 3.0 here (`stalker_damage_half`); SoC jacket armor 0.15 with
ammo k_pierce 1.0 passes 85% of the damage, here the Cordon bandits wear armor 0 (`models\capture\stalker_bandit_1` -> `body_damage_1`). In SoC a
jacketed bandit takes about 3.5 (spine) to 7 (spine1/2) PM rounds, a headshot kills; here the base game needs 3 and 1, and 2 and 1 with x1.5.
Not changed (the maintainer rejected SoC damage values, see Task 2). Not measured with real bullets: bandits of rank 1 and up wear `body_damage_2`
(armor 0.1) against FMJ k_ap 0.15, which the CoP armor formula lets through at about 33% (SoC: k_pierce 1.0).
Per weapon type (Cordon bandit, real hit powers and types of this mod, attacker = the player; a volley is every hit of one trigger pull in the same
frame, one volley per second; hits to kill, x1.0 = stock, x1.5 = shipped):
| Type (power per hit) | x1.0 | x1.5 |
|---|---|---|
| PM, fire_wound 0.55, 1 hit | 3 | 2 |
| AK-74 burst of 3, fire_wound 0.43 each | 2 volleys | 1 volley |
| Shotgun buckshot, 5 pellets of 0.36 in one frame | 2 volleys | 1 volley |
| SVD, fire_wound 1.09 | 2 | 1 |
| Knife, wound 1.0 | never in 9 stabs (health 0.13) | 6 |
| F-1 style explosion 0.5 / RPG explosion 1.0 | 1 | 1 |
Bursts and pellets are multiplied once as a whole (the burst loss is measured after the engine has applied all of it), so a burst is not over or under
multiplied. Nothing misbehaved. The knife is weak even without the multiplier: `wound` damage goes through `wound_immunity = 0.32` of the `no_resistance`
section (SoC stalkers have 1.0); not touched here. Client hits: dedicated server plus one client with the client as attacker gave the same numbers as the
host (x1.5: body 1.0 -> 0.38 -> dead = 2 hits, head 1), and `player_count` = 1 with `get_players_count` = 2.
Not measurable here: armored targets with real bullets. A shooter NPC spawned with a single weapon never fired in 16 trials (bare spawned NPCs run no
combat logic), and the `hit` script class has no armor-piercing field, so scripted hits cannot show armor. Config values only: bandit ranks 2-4 and Freedom rank 2
wear armor 0.1, Freedom rank 3 armor 0.3, against k_ap 0.15 (PM FMJ), 0.45 (AK-74 FMJ), 0.8 (SVD 7h1).
Mutants (v1.4): the monster callback differs from the stalker one: it runs AFTER the hit and `amount` is the health already lost (a dog at 1.0 went to
0.5861 with amount 0.4139), so for monsters the amounts of a burst are summed instead of measuring the health afterwards. Measured on `dog_normal` with the same
PM-sized hit: x1.0 = 3 hits, x1.5 = 2 hits (before this change the monster path also did nothing useful). `bind_gigant.script` (the two gigant bosses, one
`bind_gigant` copy in this patch) now calls the same function, except for the light-anomaly boss whose health is scripted; that copy was not run (one added line; no boss exists on Cordon).
Not covered: fights between NPCs, explosions fired by NPCs. Players' grenades count (the attacker is the player).
`bind_monster.script` is shipped by two patches (darkvalley_restore and mutant_loot, the second marked do-not-merge); the same one line was added to both.

## B. Trader ammo scales with the player count (`[ammo]` in `coop_balance.ltx`)
Every extra player adds `ammo_per_extra_player` (default 1.0) times the trader's normal ammo stock, up to `max_players` (default 4);
2 players = double stock, 4 players = four times. A fraction is rolled as a chance for one more batch. Stock is never removed when players leave.
How: `scripts\trade_manager.script` (copy of the xrMPE one, two lines added). Right after the vanilla `npc:buy_supplies` (1 player's stock) it calls
`coop_balance.on_supplied`; every tick `coop_balance.trader_ammo` compares the living players (`db.mp_actors`, capped by `get_players_count`, the same
count as `player_scaling.player_count`) with the number already served and, for each missing player, calls `npc:buy_supplies` again with a new
section `[<supplies section>_ammo]`. These sections hold only the `ammo_*` lines of the supplies section and were generated into the trader files
(Sidorovich, Barman, Petrenko, Miser, and Sakharov in yantar_restore: `supplies_start_ammo`). Players who join later top the stock up within 3 s.
Limits: the served-player counter is not saved, so after a save load the stock is not topped up again for the players already present (and
not duplicated either); the `_ammo` sections are plain copies, regenerate them if the ammo lines change.

## Task 1b: no detectors on zombified stalkers
Zombified stalker profiles (108 in `gameplay\character_desc_general.xml`) included `character_items_nl.xml`, `_2_nl` or `_3_nl`, which spawn
`detector_simple` (45%), `detector_advanced` (35%) or `detector_elite` (25%). In the 99 such zombied profiles the include is now
`character_items_nd_nl.xml` (guitar, harmonica, binoculars, no detector; the original CoP file). The other 9 already used it. Death-loot tables
(`death_items_*`) had no detector entry for zombied, so nothing else to change. File: `configs\gameplay\character_desc_general.xml` (new copy in this patch).

## Task 3: weapons in safe zones
Found: five space restrictors in all.spawn (Escape 1, Bar 2, Yantar 2, all `cfg = scripts\sr_no_weapon_space_restrictor.ltx`) and the Garbage meeting-place
restrictor. Inside them the logic switched to `sr_no_weapon`, and `bind_stalker.script` (`check_for_weapon_hide_by_zones`) force-holstered the weapon.
SoC never forces this (Bar guards only warn). Fix: the transition into `sr_no_weapon@wait` is commented out in
`scripts\sr_no_weapon_space_restrictor.ltx` and in `scripts\coop_l02_garbage\space_restrictors\gar_player_meeting_place_space_restrictor.ltx`;
the zones stay idle. Holstering while talking to an NPC (engine behaviour) is unchanged.

## Task 4: AS Val (config notes only)
`wpn_val` in val_special_scope vs SoC: rpm 840 (SoC 650), fire_distance 200 (SoC 400), hit_impulse 100 (87), `use_aim_bullet = false` (SoC true),
`scope_status = 2` with silencer_name set (SoC: scope 0). Only hit_power was changed here. `wpn_val_m1` has `scope_name = wpn_addon_scope` and its zoom keys
are covered by the val_special_scope patch. `wpn_colt1911_m1` inherits `wpn_fort` (probably a typo in weapon_upgrades, left alone).

## Files
Also new: `configs\misc\coop_balance.ltx`, `scripts\coop_balance.script`, `scripts\xr_motivator.script`, `scripts\trade_manager.script`; one line added to bind_monster.script in darkvalley_restore and mutant_loot; `supplies_start_ammo` sections appended to the five trader files.
New in this patch: `configs\gameplay\character_desc_general.xml`, `configs\misc	rade\{esc_smart_terrain_1_trader_sidorovich,bar_smart_terrain_1_trader_barman,bar_smart_terrain_4_duty_petrenko,mil_smart_terrain_2_trader_miser}.ltx`,
`configs\scripts\sr_no_weapon_space_restrictor.ltx`, `configs\scripts\coop_l02_garbage\space_restrictors\gar_player_meeting_place_space_restrictor.ltx`.
Edited in place in other patches: yantar_restore (Sakharov trade file: detector lines only) and no_mp_items (artefacts.ltx: aliases).
Encoding kept (cp1251), CRLF kept, no control characters other than tab/CR/LF.

## Not tested, risks
- Alias sections need the parent defined earlier in the same ini load; the check was done on the flattened file, the game was not started.
- Item name and icon of aliased CoP-only artifacts change; af_eye quest text still says "Eye".
- Detector stock depends on the trader restock; first stock is `[supplies_start]`.

## Кратко (RU)
Артефакты: все обычные af_* наследуют SoC-версии, CoP-артефакты заменены на ближайшие SoC. Детекторы продаются у Сидоровича, Бармена, Петренко, Сахарова; у зомбированных сталкеров их нет.
Урон и цены по SoC отклонены, всё откачено. Вместо этого: один множитель урона игроков по всем NPC и мутантам (coop_balance.ltx, player_damage_mult = 1.5) и запас патронов у торговцев растёт с числом игроков (ammo_per_extra_player).
Зоны запрета оружия отключены.
Множитель урона (v1.4): раньше он ЛЕЧИЛ цель. Свойство `health` в этом движке относительное (obj.health = x прибавляет x), а скрипт писал obj.health = hp - extra, то есть лечил почти на всё здоровье при каждом попадании игрока и сводил попадание на нет (поэтому у FOSTER бандит держал 12 патронов ПМ в корпус и 2-3 в голову). Теперь лишний урон снимается отрицательным числом после урона движка и пропорционально реально снятому здоровью (голова, кость, броня учитываются). Замер в игре, бандит Кордона, патрон ПМ: x1.0: корпус 3 / голова 1; x1.5 до правки: корпус никогда (здоровье 100%) / голова 2; x1.5 после правки: корпус 2 / голова 1. Настройка hit_amount_scale убрана. player_scaling не делает NPC крепче (только больше NPC), с множителем они не гасят друг друга.
