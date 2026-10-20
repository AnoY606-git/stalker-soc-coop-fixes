# NPC weapons with scope / silencer / launcher installed

Request: spawn attachments on NPCs, or guns with modules already installed. Owner rule says no custom features, so this is a small optional patch: drop the folder if not wanted.

## How it works
- NPC guns come from `<supplies>` in the character_desc xml (563 profiles in `character_desc_general.xml`). The engine parses `scope`, `silencer`, `launcher`, `prob=` and `cond=` in those lines, but there is no way to make "25% of guns get a scope" without editing every profile and the rolls are independent (guns could vanish).
- Instead `se_item.script` (copy of the xrMPE one, 5 added lines) calls `npc_attachments.on_weapon_register(se)` when a weapon server object registers. If its parent is a living NPC (`clsid.script_stalker`) each addon the weapon supports (status 2) is rolled with `chance` percent (default 25, `configs/misc/npc_attachments.ltx`). The roll is a hash of the weapon id, so save loads never change it.
- Addon flags are not exported to Lua; the script rewrites the weapon's STATE packet. The flags byte is the third byte from the end for every weapon class; verified on 8 weapons (AK74, PM, BM16, Protecta, Winchester, SVD, RPG-7, Abakan) with `clone_addons` (only that byte moved).

## Evidence (census hook `census_hook.lua`, whole alife, same start, 1 client)
- before: 711 NPC weapons, attachable scope 74 / silencer 69 / launcher 30, installed 0 / 0 / 0.
- after:  704 NPC weapons, attachable 63 / 79 / 30, installed scope 16, silencer 23, launcher 8 (40 guns with at least one addon); server and client alive.
- Not tested: appearance on the client model, save/load of an NPC gun (the roll is deterministic by design).

Кратко (RU): шанс 25% (файл `npc_attachments.ltx`) на каждый поддерживаемый модуль у оружия живых NPC; перепись до/после: 0 -> 40 стволов с модулями.

## Boot-safety (2026-10-19)
- The config path was written with a lost backslash, so `npc_attachments.ltx` was never read (chance was always the built-in 25). Fixed.
- An installed grenade launcher aborts spawn with "Can't open section ''": launcher is now off by default (`launcher = false`).
- Scope: only weapons with a valid `scope_name` section are eligible (weapons using only `scopes_sect` would abort). In this game that leaves almost none, so in practice the patch installs silencers.
- Silencer: the PB pistol aborts at spawn with an installed silencer, so `wpn_pb` is skipped. All other silencer weapons booted fine.
- Boot checks at chance 100 (worst case): all 17 start maps (Sarcophagus cannot be a start map) PASS; Radar, X10, Agroprom, X16, CNPP-2 twice each together with weapon_upgrades PASS.
