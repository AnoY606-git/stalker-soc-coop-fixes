# Sea Urchin / Kolobok artifact crash (model artefact_rusty_hairs.ogf)

## Symptom
Crash when a player gets near a Sea Urchin or Kolobok artifact (both use this model) (reported on Yantar, near the psi zone):
`CResourceManager::_GetBlender ... Shader 'models\water' not found in library.` Only the player
whose game draws the artifact crashes, so a friend on the same server can be fine.

## Root cause
`meshes\physics\anomaly\artefact_rusty_hairs.ogf` (Shadow of COOP gamedata.db1) gives its
tendril mesh (texture `artifact\artifact_liana2`) the shader `models\water`. That shader is not
in the xrMPE `shaders.xr` and no renderer has a script for it. Tested in game by spawning both
artifacts in front of a player: the DX9 renderer (R2) crashes with this error; static lighting (R1)
and DX11 (R4) do not. It is the only file in the base game, xrMPE and the add-on that uses
`models\water`.

## Fix
Same model with the shader name changed to `models\model` (same length, so the file size and
chunk layout are unchanged). The texture is the same. With the fix, both artifacts load in front
of a player with no crash on R2, R2a and R3, and with the Sarcophagus FPS build on R2.
