# The Marked One as the story character

## Root cause (how the model is chosen)
- The lobby character list is `[coop_team] skins` in `configs/mp/cooperative_game.ltx` (`<skin>:<spawn section>`). `<skin>` is a mesh in `meshes/actors/stalker_mp/` (`mp_skins_path`) and also the UI icon id (torso icon, `ui_models_torso_addon.xml`). The first entry maps to `actor_the_main_character` (the gold-star "story character"); the rest map to `actor_partner_regular`. The mod shipped `stalker_neutral_blouse_1` (balaclava) as the story character.
- On spawn the skin becomes the player's visual (in-game log: `Skin - actors\stalker_mp\stalker_marked_one.ogf`), is replicated to every client like any skin, and `character_desc_selo.xml` / `spawn_sections.ltx` repeat the visual for the profile and section.
- Wearing an outfit replaces the visual with the outfit's `actor_visual` (outfit.ltx / outfit_soc.ltx). The mod pointed every outfit at generic CoP-multiplayer `player_*_outfit.ogf` meshes, so a worn suit no longer looked like the Shadow of Chernobyl hero.

## What changed
- New skin `stalker_marked_one` (first entry, still `:actor_the_main_character`, so quests keyed on the story character are unchanged). Mesh = the engine's `actors\stalker_hero\stalker_hero_1.ogf` (the SoC hero; xrMPE's multiplayer build of it), copied to `meshes/actors/stalker_mp/stalker_marked_one.ogf`. The other five faces (`stalker_neutral_blouse_2..6`) stay as optional partner characters.
- Icon: the SoC Marked One portrait (vanilla `ui_actor_portrets` at 246,870, 123x87) cropped into `textures/ui/ui_marked_one_icons.dds` (120x120 torso icon `stalker_marked_one`, plus 165x108 `ui_actor_p_stalker_marked_one`), registered in `configs/ui/textures_descr/ui_marked_one_icons.xml`. Upscaled from a small source, so it is soft; the maintainer can swap the DDS for a better crop.
- `character_desc_selo.xml` (main character visual) and `spawn_sections.ltx` (`[actor_the_main_character]` visual) point at the new skin.
- Outfits: `actor_visual` of 27 sections in `configs/misc/outfit.ltx` and 8 derived sections in `configs/misc/outfit_soc.ltx` now use the SoC hero meshes in `actors\stalker_hero\` (all exist in vanilla.db0), following the SoC mapping: novice -> `stalker_hero_novice_1`, stalker -> `_stalker_1`, scientific/ecolog -> `_neutral_nauchniy`, exo (incl. Freedom/Duty exo) -> `_exo`, Freedom light/mid -> `_freedom_1`, Freedom heavy -> `_freedom_2`, Duty -> `_dolg_1`, Duty heavy -> `_dolg_2`, military/soldier -> `_military`, specops -> `_specops`, CS heavy -> `_cs_heavy`. Suits SoC never had for the hero (bandit jacket, black coat -> `stalker_hero_1`; merc, monolith, CS light/mid -> `_stalker_1`) use the nearest hero mesh.
- **outfit.ltx lives in `patches/bandit_jacket`** (that patch already overrides the file for the hud fix). I edited that single copy; this patch does not ship its own outfit.ltx. The two patches must be built together (build.py does).
- Not changed: hero hands in first person (`player_hud_section`), stray `actor_visual` key in `[sect_specops_outfit_therapeutic_immunities_add]` (outfit_soc.ltx, not a real outfit section, unused).

## How tested (real game, listen server, coop_l01_escape, test copy of coop.addon)
- Boot clean, no engine errors from the new files. Engine log: `Skin - actors\stalker_mp\stalker_marked_one.ogf`.
- Script probe in the running game: player section `actor_the_main_character`, `get_visual_name()` = `actors\stalker_mp\stalker_marked_one`; after creating and equipping `novice_outfit` the visual became `actors\stalker_hero\stalker_hero_novice_1.ogf` (outfit swap works). Each other outfit's `actor_visual` read back from the live ini resolves to the intended hero mesh.
- Lobby screenshot (`lobby_new_text_and_marked_one_slot.jpg`): the player slot shows the Marked One portrait (before: `BEFORE_lobby_demo_text.jpg`).

## Not verified
- Could not see the 3D model: the test lobby overlay covers the world and a mirror NPC never rendered in frame, so the mesh/texture look in 3D and the other outfit meshes are verified only by name and load (no engine errors), not visually. Please eyeball one session.
- Equipping a second outfit while one is worn, and multi-client replication, were not run (one local player only). Visuals travel as the standard skin/outfit visual, so remote clients need the same patch (they do for the usual "Different versions" check).
- The new texture/mesh must exist on every client (same patch on all).
