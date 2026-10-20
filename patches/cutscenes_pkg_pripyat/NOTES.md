# cutscenes_pkg_pripyat: Pripyat stadium flyover to the CNPP

Restores the SoC camera scene `pri_fly_to_aes` in Shadow of COOP, synced through the Scene Director
(`patches/cutscenes_core`, API in `CONTRACT.md`).

## Original behaviour (SoC `alife_l11_pripyat.ltx`, `pri_space_restrictor_0011`)
```
[sr_idle@wait]  on_actor_inside = sr_cutscene %+pri_stadium_reached%
[sr_cutscene]   point = pri_stadium_eff_point, look = pri_stadium_eff_look, cam_effector = pri_fly_to_aes
                on_signal = cameff_end | nil %=teleport_actor(pri_tele_point:pri_tele_look)%
```
The player enters the stadium box, is put on `pri_stadium_eff_point`, the camera flies over the stadium towards the
CNPP, and when the camera ends the player is teleported to `pri_tele_point` (far ahead, z = 463), not back.

## What this package does
- `gamedata/scripts/coop_scn_pripyat.script` registers scene `pri_stadium_fly` (kind camera, level `coop_l10_pripyat`, skip `any`, once).
- Trigger (server, script side, because the mod's all.spawn has no such restrictor): any alive player inside the box
  centre (31.285, 3.074, 266.347), half sizes (13.96, 4.00, 4.86) (from the shape axes 27.91 / 8.00 / 9.71 of the SoC restrictor, no rotation).
- Steps on every client: `ui_off`, move to `pri_stadium_eff_point` (31.449, 1.570, 279.992) looking at `pri_stadium_eff_look`,
  global camera effector `pri_fly_to_aes` (waits for its end), move to `pri_tele_point` (33.459, -0.681, 463.038) looking at `pri_tele_look`, `ui_on`.
  `on_client_end` does the final move if the scene was skipped or stopped early (the original teleports on `cameff_end` whatever ended the camera).
- `on_go` gives the story flag `PRI_STADIUM_REACHED` (the original info portion; nothing in the mod reads it).
- Whole party moves with the scene (all clients play it), like every core camera scene. Late joiners and loaded saves never replay it (core baseline).
- Note: CUTSCENES_v2 WP5 says "teleport back to the trigger centre"; the SoC source teleports to `pri_tele_point`. The package follows the SoC source.
- Coordinates are SoC coordinates (the mod levels use them; verified earlier for `pri_heli4_wait_stadium_path`).
- Yaw for the moves is computed as `atan2(look.x - pos.x, look.z - pos.z)` (radians), same as the SoC `-dir:getH()`.

## Files
- `gamedata/scripts/coop_scn_pripyat.script`
- No tutorial block and no strings are needed (camera scene only); the core stub `configs/ui/coop_scn_pripyat.xml` stays.
- `tests/pripyat.lua`: test hook (a copy lives in `%USERPROFILE%\Downloads\SoC_COOP_cutscenes\tests\hooks\`).

## Original SoC files needed (NOT in this patch; the rebuild script `tests/rebuild_soc_media.py` extracts them from the player's own install)
- `anims/camera_effects/pri_fly_to_aes.anm` (2669 bytes)
Without it the scene logs `NOCAM`, the player is still moved to the destination and nothing else breaks.

## Test
`run_scene_test.ps1 -Map coop_l10_pripyat -Hook pripyat -Media -Soak 120` (see results below).
