# Money transfer between players

Requested by FOSTER (maintainer of Shadow of COOP 8.1): "money transfer between players, as an item or via the PDA; money is credited and
debited automatically; convenient".

## Research: did an xrMPE add-on already do this?
No. Checked the MSO Call of Pripyat Co-op Beta adaptation (all four archives: 2623 files, every script/ltx/xml searched for
`transfer_money`, `give_money`, `money_transfer`, `pay`, `send_money`, `executeFunctionOnServer`), the xrMPE base scripts
(`source_base/{vanilla,xrmpe_cop_addon,xrmpe_patch}`) and the Shadow of COOP 8.0 sources. The only "transfer money" code is
player to NPC quest dialogs (`dialogs_jupiter.jup_a10_*_give_money`, `dialogs_zaton.zat_b14_bar_transfer_money`,
`dialogs_money.script`), which call `actor:transfer_money(n, npc)` on the client of the talking player. There is no player to player
transfer, no PDA money page and no money item anywhere. MSO's PDA files (`pda.dscript`, `ui_st_pda_addon.xml`) are unrelated.
So this is a new implementation; no MSO code was copied. Credit as requested: MSO adaptation by B4rs1k, original MSO by Salaam
(reference only: it confirmed that `game_cl.executeFunctionOnServer` is the client to server channel and that it carries no arguments).

## Design
Chosen: a small window opened from the game, not a "money bundle" item and not a PDA tab.
- A bundle item needs a spawned item per amount, can be lost, stolen, destroyed or left on another level, and the money exists
  nowhere while it lies on the ground (duplication/loss risks, save-game edge cases). A PDA tab means rewriting `pda.xml`, which other
  patches and the mod itself edit. A window needs one new XML and one script and cannot create or lose money.
- Open it by looking at a teammate (within 4 m) and pressing the Use key; with nobody in the crosshair, Crouch + Use. Presets
  100 / 500 / 1 000 / 5 000 / 10 000 / Everything; "Next player" changes the target (2 to 4 players). A hint toast shows once, 20 s after spawn.
- The SERVER moves the money. `executeFunctionOnServer(name)` has no arguments, so target and amount are in the function name:
  `coop_mt_<targetPlayerId>_<j>` (j = preset index, 0 = whole balance). The server registers one `game_sv` function per player id in
  `db.mp_actors` (every 0.5 s) and runs the transfer with the caller's id supplied by the engine, so a client cannot spend somebody else's money.
- Server checks: both ends are alive players, sender is not target, balance >= amount, 300 ms cooldown per sender (repeat/lag: a burst of
  identical requests applies once). Debit and credit happen in one step; if either half fails the debit is rolled back (no money created or lost).
  No negative balance is possible.
- Result feedback: the server gives a short-lived story flag `MTX_<t>_<seq>_<from>_<to>_<amount>_<OK|NOFUNDS|BADTARGET>`; flags are synced
  to all clients; the sender and the receiver get a PDA toast with the other player's name; the server removes the flag after 20 s and purges
  leftovers from loaded saves. Clients ignore flags that existed when they joined (no replay).
- Hook: `scripts/bind_stalker.dscript` (appended to the mod's bind_stalker.script) wraps `mp_actor_binder:update` and calls the idempotent
  `coop_money.ensure()`. It does not touch the shared `xr_conditions.dscript` / `xr_effects.dscript`.
- Strings: English and Russian (`st_coop_money.xml`).

## Files (all new, nothing of another patch is edited)
- `gamedata/scripts/coop_money.script`: server transfer, RPC registration, flags, toasts, window, key trigger.
- `gamedata/scripts/bind_stalker.dscript`: the loader hook.
- `gamedata/configs/ui/coop_money.xml`: the window.
- `gamedata/configs/text/{eng,rus}/st_coop_money.xml`.
- `tests/test_money.lua`: in-game QA hook (see below).

## Tests (real game, run_coop with the money_transfer gamedata as test db; see tests/test_money.lua)
Two real clients on one PC collapse into one player on this PC (known harness blocker, see automatedqa.md), so the run uses ONE real
client (listen server, real actor, real `executeFunctionOnServer` and `game_sv` dispatch, real money, flags and toasts) and a FAKE
second player injected into `db.mp_actors` (proxy object). Results are recorded in the final report of the task.

## Known limits
- Amounts are presets only (no free typing); press again for more.
- Money of a REMOTE client is read and changed on the server through `game_object:money()/give_money()`. It was verified with a real local
  actor and a fake peer, not with a second real machine.
- The Use-key trigger itself is not simulated by the tests (the window, the click path and the server are).
