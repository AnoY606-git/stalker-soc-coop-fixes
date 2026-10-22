--@qa_lib
-- TEST ONLY: finds which step of the coroutine scheduler hard-crashes LuaJIT in the game (one line per step, written BEFORE the step runs).
local L = qa_lib
local function ev(m) qa.event("DIAG " .. m) end

qa.once("qa_lib_diag", function(t, lo)
	if not L.on_server() then return end
	ev("step 1: coroutine.create + resume without yield")
	local co = coroutine.create(function(a) ev("  inside co, arg " .. tostring(a)) return 7 end)
	local ok, r = coroutine.resume(co, 5)
	ev("  step 1 done ok=" .. tostring(ok) .. " r=" .. tostring(r))

	ev("step 2: coroutine with yield, resumed from a later tick")
	local co2 = coroutine.create(function()
		ev("  co2 before yield")
		local v = coroutine.yield({ wake = 1 })
		ev("  co2 resumed with " .. tostring(v))
		coroutine.yield(2)
		ev("  co2 finished")
	end)
	local ok2, req = coroutine.resume(co2)
	ev("  step 2 first resume ok=" .. tostring(ok2) .. " req type=" .. type(req))
	local n = 0
	qa.hooks.diag_tick = function(t2, lo2)
		n = n + 1
		if n == 1 then
			ev("step 2b: second resume")
			local o, rr = coroutine.resume(co2, true)
			ev("  step 2b done ok=" .. tostring(o) .. " status=" .. coroutine.status(co2))
		elseif n == 2 then
			ev("step 3: coroutine.running() in main and in a coroutine")
			ev("  main running=" .. tostring(coroutine.running()))
			local co3 = coroutine.create(function() ev("  in co3 running=" .. tostring(coroutine.running())) end)
			coroutine.resume(co3)
			ev("  step 3 done")
		elseif n == 3 then
			ev("step 4: engine calls inside a coroutine (level.name, io.open, getFS)")
			local co4 = coroutine.create(function()
				ev("  level " .. tostring(level.name()))
				ev("  state_get " .. tostring(L.state_get("x", "dflt")))
				ev("  pcall inside co " .. tostring(pcall(function() return 1 end)))
			end)
			local o, e = coroutine.resume(co4)
			ev("  step 4 done ok=" .. tostring(o) .. " err=" .. tostring(e))
		elseif n == 4 then
			ev("step 5: L.task with wait")
			L.task("diag5", function()
				ev("  task slice 1")
				L.wait(2)
				ev("  task slice 2")
			end)
			ev("  step 5 task created")
		elseif n == 8 then
			ev("all steps survived")
			qa.hooks.diag_tick = nil
		end
	end
end)
