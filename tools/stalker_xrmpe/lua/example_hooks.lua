-- Example assertion hooks for run_coop.ps1 -Hooks <this file>.  Appended AFTER qa_harness.lua, so qa.* is available.
-- Runs on every client (the server/listen client is OnServer() == true, the joined client is false).
-- API:  qa.once(name, fn(t, lo))            run fn once, after this client's own player spawned (t = seconds since spawn)
--       qa.hooks.name = fn(t, lo)           run fn every second after spawn (return value ignored)
--       qa.eventually(name, fn, timeout_s)  poll fn() every second; fn returns ok[, detail]; PASS on first true, FAIL at timeout
--       qa.assert(name, ok, detail)         one-shot PASS/FAIL line in qa_assert.log (run_coop prints it, any FAIL fails the run)
--       qa.event(text)                      free-form line in qa_events.log
--       qa.cfg.role / qa.cfg.scenario / qa.cfg.<anything you pass with run_coop -Cfg key=value>
-- Do not call OnServer()/LocalActor()/getFS() at file top level (this runs at script load, before the game exists): do it in a hook.
qa.once("example_server_gives_flag", function(t, lo)
	if OnServer() then
		story_flags.give_flag("QA_EXAMPLE_FLAG")
	end
	-- BOTH clients must see it within 30 s (this is the poll-not-check-once pattern)
	qa.eventually("example flag reaches this client", function()
		return story_flags.has_flag("QA_EXAMPLE_FLAG"), "role " .. tostring(qa.cfg.role)
	end, 30)
end)
