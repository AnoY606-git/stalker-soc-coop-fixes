# Rusty Hair artifact crash

## Symptom
Crash when a player gets near a Rusty Hair artifact (reported on Yantar, near the psi zone):
`CResourceManager::_GetBlender ... Shader 'models\water' not found in library.` Only the player
whose game draws the artifact crashes, so a friend on the same server can be fine.

## Root cause
`meshes\physics\anomaly\artefact_rusty_hairs.ogf` (Shadow of COOP gamedata.db1) gives its
tendril mesh (texture `artifact\artifact_liana2`) the shader `models\water`. That shader is not
in the xrMPE `shaders.xr` and no renderer (r1 to r4) has a script for it, so every renderer
aborts when the model is first drawn. It is the only file in the base game, xrMPE and the
add-on that uses `models\water`.

## Fix
Same model with the shader name changed to `models\model` (same length, so the file size and
chunk layout are unchanged). The texture is the same.
