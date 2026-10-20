# Cutscene package "endings" (WP2): wish-granter endings, true ending, credits, return to menu

Scene Director package (`patches/cutscenes_core`, contract `SoC_COOP_cutscenes/CONTRACT.md`). Nothing here edits core files.

## What was wrong
- `sar_monolith_space_restrictor.ltx` rolled a dice per client (`{~50} ... {~30}`): each player could see a different ending, and the
  original deterministic rule (`xr_effects.sar_monolith_miracle`, SoC `xr_effects.script:1992-2020`) was lost.
- `aes_2_the_end_space_restrictor.ltx` ran `run_tutorial(final_peace)` on every client separately.
- Neither ending ever reached the credits (`game_credits` only sets `_G.show_credits_in_menu`, nobody calls it) or the menu.

## What it does now
1. The prompt "press USE" (`bad_final_monolith`) is unchanged. When a player presses it the shared flag `SAR_BAD_FINAL_MONOLITH_INFO`
   is given. The restrictor now runs `%=scene_request(end_wish)%` (the dice line is gone) and the scene also has a server trigger on
   the same flag, so it does not matter on which machine the restrictor logic runs. Requests are idempotent.
2. `end_wish` (server `pick`, rolled exactly once) decides ONE ending for the whole party, writes it to the shared flag
   `SCN_END_WISH_VAR_<n>_<VARIANT>`; every client plays the same `soc_end_<x>` movie. `skip = "none"`: a forced skip vote is ignored.
3. `end_peace` (true ending at CNPP-2, `AES_2_THE_END_SPACE_RESTRICTOR_INFO`): one play for the party instead of one per client.
4. `on_end` of both requests `credits`: the original `credits_seq` tutorial (credits.ogg). A majority vote may skip the credits.
   Whatever ends the credits run (finished, skipped, watchdog) ends with `disconnect` for everybody = main menu
   (clients after 1 s, the host after 3 s so nobody is dropped mid-scene). `xr_effects.after_credits` of xrMPE talks to the main-menu
   object which does not exist in game and raises; the package wraps it in a pcall (logged as `credits after_credits ignored error`).

## Decision rules (owner: whole party combined, original rules)
In this order, first match wins:
1. both faction leaders dead (any player's kill counts; world state) -> `final_to_monolith`
2. party money >= 50000 -> `final_gold`
3. party reputation >= 1000 -> `final_blind`
4. party reputation <= -1000 -> `final_apocal`
5. otherwise -> `final_immortal`

Boundaries are inclusive (50000, 1000, -1000), as in the original.

### Sum or average: AVERAGE (`coop_scn_endings.cfg.mode = "average"`)
Evidence and reasoning (the test `E6_average_not_sum` and the table checks in `E0_decide_table` prove the code, the argument is below):
- With the SUM, the original 50000 means 25000 per player for 2 players and 12500 per player for 4 players. Money is earned per
  player from the same quests and trades, so a 4 player party reaches 50000 in total very early in the game and "gold" (priority 2)
  would hide blind, apocal and immortal for nearly every party: trivially reachable.
- Reputation behaves the same: +-1000 in total is only +-250 each for four players, a threshold reached by normal play, so
  "immortal" (the neutral ending) would almost never happen.
- The average keeps the original single player difficulty for any party size; with one player average == sum == original rules.
- It is also robust to dead or absent players: `party()` only counts alive players in both numerator and denominator.
- The owner's default (sum) is one line away: `coop_scn_endings.cfg.mode = "sum"` (tested by the table checks).
  Not measured in a real playthrough: typical late-game money per player. If playtesting shows 50000 is too easy or too hard for
  a single player, change `cfg.gold` (one number), not the mode.

### Leaders dead
Original infos `mil_lukash_dead` and `bar_voronin_dead` are not given by any script of the mod. The package therefore checks
(a) the shared flags `MIL_LUKASH_DEAD` / `BAR_VORONIN_DEAD` (another patch may give them) and (b) the alife server entities by
name (`mil_smart_terrain_3_freedom_lukash`, `bar_smart_terrain_4_duty_voronin`, scanned once at the roll) and `alive()`.
The roll logs the state of both (`leaders_dead=... [npc=state ...]`): `alive`, `dead(alife)`, `dead(flag)`, `missing`, `unknown`.
In the test on the Cordon start map both names were `missing` (not found in the server object list there), so the alife route is
UNVERIFIED on the real Military/Bar levels. Also: Voronin has `invulnerable = true` in `bar_smart_terrain_4_walker_voronin.ltx`,
so in the stock mod the "both leaders dead" ending cannot be reached by killing him. Fixing that needs a Bar logic change
(out of scope for this package, see Open issues).

## Files
- `gamedata/scripts/coop_scn_endings.script`: scenes `end_wish`, `end_peace`, `credits`; `decide(stats)` is the pure rule function.
- `gamedata/configs/ui/coop_scn_endings.xml`: fallback cards `scn_endings_card_<x>` (shown when a movie file is missing).
- `gamedata/configs/text/{eng,rus}/st_coop_scn_endings.xml`: card strings (rus is windows-1251).
- `gamedata/configs/scripts/coop_l11_sarcofag/space_restrictors/sar_monolith_space_restrictor.ltx` (dice removed).
- `gamedata/configs/scripts/coop_l11_stancia_2/space_restrictors/aes_2_the_end_space_restrictor.ltx` (`scene_request(end_peace)`).
- Test hooks (not packed into the db): `SoC_COOP_cutscenes/tests/hooks/endings.lua`, `endings_cfg_<a..z>.lua` (case groups),
  `endings_2client.lua` (run_coop.ps1).

## Original SoC files needed (NOT in this patch)
The patch ships no original SoC file. Needed at runtime, all already in the Shadow of COOP add-on:
`textures/ui/final_{blind,gold,to_monolith,apocal,immortal,peace}.ogm`, `sounds/intro/final_*.ogg`, `sounds/music/credits.ogg`,
the mod's `credits_seq` (`ui_credits.xml` + `ui_credits_base.xml` from xrMPE) and `textures/intro/intro_back`.
The rebuild script needs nothing extra for this package. If a movie is missing the scene runs `fallback` (a text card).

## Tests (all automated, in game)
Listen server on the Cordon start map (the Sarcophagus has no player respawn points): `tests/run_scene_test.ps1 -Hook endings_cfg_<g>,endings`.
The hook widens the scenes' level guard to the start map and fakes party stats through `coop_scenes.party` (the director's ctx reads it).
- E0 decision table (21 checks: every boundary, priority order, n=0, average vs sum, pick() through the registered def).
- E1..E5 each ending end to end (request or `scene_request` effect, PICK, REQUEST, GO, CLIENT_START, CLIENT_VAR, CLIENT_END, ACK, END, then credits the same way, exactly one GO each, `coop_scenes.variant` equals the pick).
- E6 four players with 120000 total: average -> immortal (sum mode would be gold).
- E7 no skip: a forced skip vote is sent and ignored, the scene ends by acks.
- E8/E9 server trigger by flag alone (`SAR_BAD_FINAL_MONOLITH_INFO`, `AES_2_THE_END_SPACE_RESTRICTOR_INFO`), no request call.
- E10 one roll: a second request in the same tick is refused, one PICK, one GO.
- R_* the five real ending movies and Z real ending + real credits + majority skip + disconnect (see results in the report).
- `run_coop.ps1` (dedicated server + clients qaA, qaB): both clients log the same variant, one GO, both ACK, END, credits for both.
Real-movie playback note: ticks keep running while a movie or the credits play (heartbeat `HB` lines, `time_global` advances), the world is not paused.

## Open issues
- Leaders-dead rule: Voronin is invulnerable in the mod; Lukash/Voronin names `missing` on the start map; infos never given. Needs a
  Bar/Military logic change (e.g. a death flag) if the owner wants that ending reachable.
- Real money/reputation of remote players on the server (`a:money()`, `a:character_reputation()`) is read through `coop_scenes.party()`;
  in the listen test only the local player was real (0/0). The 2-client run used faked stats; remote values are UNVERIFIED.
- Players can be attacked during a 50 to 106 s movie (pause is off for MP safety). The Monolith room is normally cleared at that point.
- The ending stops being "once": a new game needs fresh flags (`SCN_END_WISH_PLAYED`, `SCN_CREDITS_PLAYED` live in the save).
