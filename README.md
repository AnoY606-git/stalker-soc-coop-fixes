# Shadow of COOP fixes

Unofficial bug-fix patch for **Shadow of COOP 8.0**, the S.T.A.L.K.E.R.: Shadow of Chernobyl
co-op add-on for the X-Ray Multiplayer Extension (xrMPE). It fixes crashes and stuck quests and
unlocks the true ending.

This is a fan patch. It is not made by or affiliated with the Shadow of COOP or xrMPE teams.
You need their launcher and add-on first.

## Play in three steps

1. Install the [xrMPE launcher](https://github.com/M4dMurloc/xrMPE_Launcher_Release/releases)
   (version 0.9.x) and run it once so it downloads the game. Then get
   [Shadow of COOP 8.0](https://drive.usercontent.google.com/download?id=1Xl1hKfbzVOKQFEla3wB-5WokiL6FcpAx&export=download&authuser=0)
   (2.2 GB, official link from the [xrMPE wiki](https://xrmpe.fandom.com/ru/wiki/S.T.A.L.K.E.R._Shadow_of_COOP)),
   put `coop.addon` in `X-Ray Multiplayer Extension\gameddons\` and switch it on in the
   launcher's Add-ons tab.
2. Download `SoC_COOP_fixes.zip` from [Releases](../../releases), close the game and launcher,
   open `X-Ray Multiplayer Extension\game\addons\coop.addon` with 7-Zip and drag
   `zzz_soc_coop_fixes.db` into it. Back up `coop.addon` first.
3. Host or join as usual. **Every player needs the same patch**, or the server reports
   "Different versions". Starting a new game is recommended.

To uninstall, open `coop.addon` with 7-Zip again and delete `zzz_soc_coop_fixes.db`.

## What it fixes

- Crash when wearing or buying the bandit jacket or trench coat (`actor_hud_bandit_novice`).
- Freedom turning hostile at the Army Warehouses when Duty or anyone else shoots them; only a
  player hitting Freedom counts now.
- Getting stuck in dialogue with the Freedom squad leader (Skull).
- Traders refusing quest artifacts (both artifact versions are accepted).
- X16: Controller door staying locked after a death or a save load, levers that stop working,
  the lab autosave firing again.
- Cordon: main quest stuck after handing the flash drive to Sidorovich (cut-off dialogue,
  helicopter never flying), and Sidorovich's door closing on the second player.
- X18: Barman refusing the documents when players split them up.
- The Hunter's family shotgun never spawning.
- Arena: Arnie only saying "talk to the boss", and the teleport to Arnie on every Bar visit.
- **True ending unlocked:** crash entering the Monolith control bunker and the server crash when
  CNPP-2 loads, caused by breakable-object models the levels reference but never shipped. Small
  stand-in models fix this on all 18 levels.

Optional: `optional/corpse_cap_30` keeps 30 corpses instead of 300 for better FPS in the big
Monolith fights. Build with `python build.py --corpse-cap-30`. Everyone on the server must use
the same build.

## Status

Tested automatically on the real game:

- All 18 levels boot on a dedicated server with a local client and no crash (`tools/boottest.ps1`).
- An in-engine self-test script checks every fix from inside the running game: 20 of 20 pass
  (`tests/coop_selftest.script`).

## Known issues

- FPS can still drop in very large Monolith firefights. It is CPU-bound (AI vision and physics),
  and the optional corpse cap helps only somewhat.

## How it works

`coop.addon` is a tar of X-Ray `.db` archives, and the launcher loads every `.db` inside it, so
the patch is one extra archive that overrides the files it fixes. The server checksums the
add-on, which is why every player needs an identical copy. Each fix lives in its own folder under
`patches/` with a `NOTES.md` explaining the root cause.

## Building and tests

```
python build.py                 # writes build/zzz_soc_coop_fixes.db
python build.py --corpse-cap-30 # same, with the optional corpse cap
```

`tools/` holds the archive reader (`xdb.py`, LZHUF index + LZO1X data), `extract.py`, `pack.py`,
a Lua block checker and model checkers. `tools/boottest.ps1 -Levels <level> ...` boots levels on
the dedicated server and reports OK or the crash text. `tests/` holds the in-engine self-test and
census scripts (test builds only, not in the release).

## Part of coop-anything

This is one of the projects in [coop-anything](https://github.com/cranebeaker/coop-anything).

## Credits

- **Shadow of COOP** by Arcanum Team. This patch only exists because of their add-on.
  Official pages: [VK](https://vk.com/shadowofcoop), [Discord](https://discord.gg/bE4D7G4jAK),
  [wiki page with downloads](https://xrmpe.fandom.com/ru/wiki/S.T.A.L.K.E.R._Shadow_of_COOP).
- **X-Ray Multiplayer Extension (xrMPE)** by the xrMPE team, launcher by M4dMurloc:
  [launcher releases](https://github.com/M4dMurloc/xrMPE_Launcher_Release/releases),
  [xrMPE wiki](https://xrmpe.fandom.com/ru/wiki/).
- **S.T.A.L.K.E.R.: Shadow of Chernobyl** by GSC Game World.

## License

The tools and build scripts in `tools/`, `tests/` and `build.py` are MIT licensed (see
`LICENSE`). The files under `patches/` and `optional/` are edited versions of Shadow of COOP and
GSC Game World files and stay theirs; they are shared here only as a non-commercial fan fix.
If the Shadow of COOP or xrMPE authors want anything changed or taken down, open an issue and it
will be done.
