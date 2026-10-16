# Bandit jacket / trench coat crash fix

## Root cause
`source/gamedata.db0/configs/misc/outfit.ltx:489` ([bandit_outfit]) sets `player_hud_section = actor_hud_bandit_novice`, and line 569 ([black_coat_outfit], the trench coat) sets `actor_hud_bandit_trench`. Neither section exists anywhere (mod, xrmpe_patch, vanilla, cop_addon): `configs/creatures/actor.ltx` only defines actor_hud_00..19, _exo, _dolg_exo, _svoboda_exo, _merc, _monolit. The engine calls CInifile::r_section on the hud section when the outfit is equipped (and on every hand-HUD use while worn, e.g. drinking), hence the fatal error `Can't open section 'actor_hud_bandit_novice'`. The chainmail jacket (outfit_soc.ltx:73 -> actor_hud_01) and merc suit (actor_hud_merc) reference existing sections, so they work.

Missing sections: `actor_hud_bandit_novice`, `actor_hud_bandit_trench`. A scan of every `player_hud_section` in outfit.ltx found no other dangling ones.

## Vodka
[vodka]:booster (items.ltx:140) has no custom hud section; booster uses `hud = antirad_hud`, which exists (items.ltx:613), and `[vodka_hud]` exists too. No missing section found. The vodka crash is almost certainly the same bug: the player was wearing the bandit jacket/coat, and the hand HUD lookup during the drink animation hit the missing outfit hud section. Not confirmed in-game.

## Change
`patches/bandit_jacket/gamedata/configs/misc/outfit.ltx`: both lines now point at `actor_hud_01` (existing "bandit outfit" hands, `wpn_hand_01`, same as the SoC bandit outfit). CRLF preserved; byte-copy otherwise.

```diff
--- source/gamedata.db0/configs/misc/outfit.ltx	2026-10-15 20:03:10.430121600 +0100
+++ patches/bandit_jacket/gamedata/configs/misc/outfit.ltx	2026-10-15 20:37:06.747332300 +0100
@@ -486,7 +486,7 @@
 cform           = skeleton
 visual          = dynamics\outfit\bandit_outfit
 actor_visual	= actors\stalker_mp\player_bandit_outfit.ogf
-player_hud_section	= actor_hud_bandit_novice
+player_hud_section	= actor_hud_01
 
 ef_equipment_type	= 3
 
@@ -566,7 +566,7 @@
 cform           = skeleton
 visual          = dynamics\outfit\black_coat_outfit
 actor_visual	= actors\stalker_mp\player_black_coat_outfit.ogf
-player_hud_section	= actor_hud_bandit_trench
+player_hud_section	= actor_hud_01
 
 ef_equipment_type	= 3
 
```

## Confidence
High that the missing sections cause the crash (exact name match, no definition anywhere). Medium that nothing else crashes afterwards: I cannot inspect archived assets, so mesh existence (`wpn_hand_01`, player_bandit_outfit.ogf, player_black_coat_outfit.ogf, dynamics\outfit\black_coat_outfit) is unverified. If a mesh is missing it cannot be fixed by config.

## Multiplayer risks
Host and clients must all install the same outfit.ltx (configs are checked/synced by the engine; mismatch may cause desync or kick). Hands will look like the bandit jacket's hands for the trench coat; cosmetic only.

## Test
Start a coop game, spawn/buy bandit_outfit and black_coat_outfit, equip each as host and as a client, then drink vodka while wearing each. Expect no crash and bandit hands in first person.
