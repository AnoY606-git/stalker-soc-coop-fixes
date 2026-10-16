# FPS drops (Sarcophagus, CNPP, CNPP-2)
Root cause: scripts/release_body_manager.script body_max_count was raised by the mod from 7 (xrMPE) to 300, so up to 300 ragdoll corpses stay loaded on the Monolith wave levels.
Fix: body_max_count = 30. Cleanup only removes bodies >30 m from all players and dead >40 s, farthest first; quest/story/keep_items bodies are never removed.
