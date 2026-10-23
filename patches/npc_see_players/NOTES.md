# npc_see_players: NPCs react to players at normal range

## Report
Side-quest bandits stand around and only notice a player at point blank; Agroprom soldiers walk past a firefight (Forest35, v1.4.3).

## Cause (found by diffing against the original SoC)
xr_combat_ignore.script of the xrMPE base (copied from Call of Pripyat) has a rule that the original SoC does not have: an NPC of a registered simulation squad ignores an enemy farther than 30 m when the enemy has a group_id that is not 65535 and is not in the simulation registry (it saves AI time for NPC vs NPC fights). In xrMPE a player's server entity has group_id = nil (not 65535, checked live), so for every NPC squad every player counts as such an enemy: NPCs ignore players beyond 30 m.

## Fix
One condition: the rule no longer applies when the enemy is a player (not is_object_actor_by_id(enemy:id())). NPC vs NPC keeps the CoP rule. The rest of the file is the xrMPE copy, unchanged.
