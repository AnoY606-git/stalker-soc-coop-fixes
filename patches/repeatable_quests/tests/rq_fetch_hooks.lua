--@qa_lib
-- TEST ONLY (never shipped). Fetch jobs (bring an artifact / a mutant part): every job of misc\coop_repeat_quests.ltx (kind = gen_fetch), on a LISTEN host
-- (1 game process, Cordon start). No talk window: the hook calls the dialog functions the phrases use (precondition / action of coop_rq_dialogs.script)
-- with the local player as first speaker and a friendly stalker spawned next to him as second speaker, sets the flags the phrases set, gives items and
-- looks at tasks, money, items and flags. Bar / Yantar / Military jobs run the same way on Cordon (the PDA task of a job only appears on its own level).
--
-- run_coop.ps1 -Map coop_l01_escape -Owner <unique> -Mode listen -Clients 1 -DbFile <db built by build.py> -Hooks <this file> -SoakSeconds 420 -CompareTimeout 10 -TimeoutSeconds 900 -ResultDir <dir>
-- Result: qa_assert.log of the host + qa_events.log; python tools\stalker_xrmpe\qa_verdict.py <dir>
--
-- One qa.assert per step. Parts:
--  S  Sidorovich on his own level (real flow): offers (lowest priority per kind), hand-in hidden with no job, PDA task + giver icon, offers while a job runs,
--     hand-in shown, pay (item taken, money, reward items), task completed, cooldown flag, offers afterwards, the gated bloodsucker part after the case flag.
--  A  every fetch job (all givers): accept flag -> hand-in function has/open true -> pay -> item taken, money, every reward item, cooldown flag, hand-in closed.
local L = qa_lib

local function sf(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end

-- the jobs, read from the shipped ltx (what the script reads)
local function load_jobs()
	local ini = ini_file("misc\\coop_repeat_quests.ltx")
	local jobs = {}
	for i = 0, ini:line_count("list") - 1 do
		local _, id, _ = ini:r_line("list", i, "", "")
		if ini:line_exist(id, "kind") and ini:r_string(id, "kind") == "gen_fetch" then
			local function s(k, def) if ini:line_exist(id, k) then return ini:r_string(id, k) end return def end
			local j = { id = id, level = s("level"), prior = tonumber(s("prior", "0")), money = tonumber(s("pay_money", "0")), secs = {}, items = {}, gate = {} }
			for w in string.gmatch(s("item", ""), "[%w_%-]+") do j.secs[#j.secs + 1] = w end
			for w in string.gmatch(s("pay_items", "none"), "[%w_%-]+") do if w ~= "none" then j.items[#j.items + 1] = w end end
			for w in string.gmatch(s("gate", "none"), "[%w_]+") do if w ~= "none" then j.gate[#j.gate + 1] = w end end
			j.giver = string.match(id, "^rq_(%a+)_")
			j.kind = string.find(id, "_art", 1, true) and "art" or "part"
			jobs[#jobs + 1] = j
		end
	end
	return jobs
end

local function fl(j, suf) return "RQG_" .. string.upper(j.id) .. "_" .. suf end

local function call(name, p, npc) return sf(function() return coop_rq_dialogs[name](p, npc) end) end

-- the ids a giver offers right now, sorted
local function offers(jobs, giver, p, npc)
	local r = {}
	for _, j in ipairs(jobs) do
		if j.giver == giver and call("offer_" .. j.id, p, npc) == true then r[#r + 1] = j.id end
	end
	table.sort(r)
	return table.concat(r, ",")
end

-- what the SoC rule gives with no gate flag set and nothing accepted: the lowest priority of each kind (gated jobs are not available)
local function fresh_expect(jobs, giver)
	local best = {}
	for _, j in ipairs(jobs) do
		if j.giver == giver and #j.gate == 0 then
			if best[j.kind] == nil or j.prior < best[j.kind].prior then best[j.kind] = j end
		end
	end
	local r = {}
	for _, j in pairs(best) do r[#r + 1] = j.id end
	table.sort(r)
	return table.concat(r, ",")
end

local function cooldown_flags(j)
	local pre = "RQ_" .. string.upper(j.id) .. "_R"
	local ids = {}
	for k, v in pairs(story_flags.story_flags) do
		if v == true and string.sub(k, 1, #pre) == pre then ids[#ids + 1] = k end
	end
	return ids
end

local function counts(p, j)
	local c = {}
	for _, s in ipairs(j.items) do c[s] = L.count_item(p, s) end
	return c
end

-- steps that run one job: accept, hand in, pay. level_task = true: also the PDA task (the job is on this level)
local function job_steps(steps, j, ctx, level_task, opts)
	opts = opts or {}
	local tag = j.id
	local function add(f) steps[#steps + 1] = f end
	add(function(c)
		if not opts.item_given then L.give_item(ctx.p(), j.secs[#j.secs], 1) end   -- the SoC twin (af_x_soc) where the job has one: both are accepted
		L.flag_give(fl(j, "ACC"))                  -- what the accept phrase sets
		c.m0 = L.money(ctx.p())
		c.inv0 = counts(ctx.p(), j)
		if level_task then
			return L.wait_for(function() return sf(function() return getLocalActor():get_task(j.id, true) ~= nil end) == true end, 40)
		end
		return L.wait(3)
	end)
	if level_task then
		add(function(c, got)
			qa.assert("rq_fetch S: PDA task " .. tag .. " given", got == true, tostring(got))
			return L.wait(1)
		end)
		add(function(c)
			local ic = sf(function() return getLocalActor():get_task(j.id, true):get_icon_name() end)
			local want = (j.giver == "sid") and "ui_rq_job_trader" or nil
			qa.assert("rq_fetch S: task icon is the giver icon " .. tag, want == nil or ic == want, tostring(ic))
		end)
	end
	if opts.while_running then add(opts.while_running) end
	add(function(c)
		local p, npc = ctx.p(), ctx.npc()
		qa.assert("rq_fetch A: hand-in precondition has_" .. tag .. " true (job running, item carried)", call("has_" .. tag, p, npc) == true, tostring(call("has_" .. tag, p, npc)))
	end)
	add(function(c)
		local p, npc = ctx.p(), ctx.npc()
		qa.assert("rq_fetch A: giver hand-in dialog open " .. tag, call("fetch_open_" .. j.giver, p, npc) == true, tostring(call("fetch_open_" .. j.giver, p, npc)))
	end)
	add(function(c)
		local p, npc = ctx.p(), ctx.npc()
		sf(coop_rq_dialogs["pay_" .. tag], p, npc)   -- the action of the hand-in phrase
		L.flag_give(fl(j, "DONE"))                  -- the phrase's give_flag
		return L.wait(4)
	end)
	add(function(c)
		local n = 0
		for _, s in ipairs(j.secs) do n = n + L.count_item(ctx.p(), s) end
		qa.assert("rq_fetch A: the item is taken (nothing left) " .. tag, n == 0, tostring(n))
	end)
	add(function(c)
		local m1 = L.money(ctx.p())
		qa.assert("rq_fetch A: money paid to the player who hands in " .. tag, m1 == (c.m0 or 0) + j.money, "before " .. tostring(c.m0) .. " after " .. tostring(m1) .. " want +" .. j.money)
	end)
	add(function(c)
		local want, got = {}, {}
		for _, s in ipairs(j.items) do want[s] = (want[s] or 0) + 1 end
		for s in pairs(want) do got[s] = L.count_item(ctx.p(), s) - (c.inv0[s] or 0) end
		local ok, info = true, {}
		for s, n in pairs(want) do
			if got[s] ~= n then ok = false end
			info[#info + 1] = s .. " " .. tostring(got[s]) .. "/" .. n
		end
		qa.assert("rq_fetch A: reward items arrive " .. tag, ok, table.concat(info, ", "))
	end)
	add(function(c)
		local p, npc = ctx.p(), ctx.npc()
		qa.assert("rq_fetch A: hand-in closed after the job is done " .. tag, call("fetch_open_" .. j.giver, p, npc) == false, tostring(call("fetch_open_" .. j.giver, p, npc)))
		if level_task then
			return L.wait_for(function()
				local t = sf(function() return getLocalActor():get_task(j.id, true) end)
				return t == nil or sf(function() return t:get_state() == task.completed end) == true
			end, 30)
		end
		return L.wait(3)
	end)
	if level_task then
		add(function(c, done)
			qa.assert("rq_fetch S: task completed / closed " .. tag, done == true, tostring(done))
		end)
	end
	add(function(c)
		local ids = cooldown_flags(j)
		qa.assert("rq_fetch A: cooldown flag set (refresh later) " .. tag, #ids >= 1, table.concat(ids, ","))
	end)
end

qa.once("rq_fetch_run", function(t, lo)
	if not OnServer() then return end
	local lvl = level.name()
	local ctx = { _npc = nil }
	ctx.p = function() return L.local_player() end
	ctx.npc = function() return ctx._npc end
	local jobs = load_jobs()
	local by_id = {}
	for _, j in ipairs(jobs) do by_id[j.id] = j end
	local steps = {
		function(c) qa.assert("rq_fetch: the ltx lists fetch jobs", #jobs >= 20, tostring(#jobs)) L.god(true) return L.wait(12) end,
		function(c)
			local se, id = L.spawn_npc("sim_default_bandit_0", { relation = "friend", offset = { 4, 0, 0 } })   -- the second speaker of every dialog call
			c.id = id
			return L.wait_for(function() return id ~= nil and L.online(id) ~= nil end, 40)
		end,
		function(c, up)
			ctx._npc = c.id and L.online(c.id) or nil
			qa.assert("rq_fetch: a friendly stalker is online as the second speaker", up == true and ctx._npc ~= nil, tostring(up))
		end,
		function(c)
			local p, npc = ctx.p(), ctx.npc()
			qa.assert("rq_fetch S: every job has offer / has / pay functions", (function()
				for _, j in ipairs(jobs) do
					for _, f in ipairs({ "offer_", "has_", "pay_" }) do if coop_rq_dialogs[f .. j.id] == nil then return false end end
				end
				return true
			end)(), "missing function")
		end,
	}
	-- S: Sidorovich, real flow with the PDA task (only on his level)
	if lvl == "coop_l01_escape" then
		steps[#steps + 1] = function(c)
			local p, npc = ctx.p(), ctx.npc()
			local got, want = offers(jobs, "sid", p, npc), fresh_expect(jobs, "sid")
			qa.assert("rq_fetch S: fresh Sidorovich offers the lowest priority of each kind", got == want, got .. " | want " .. want)
		end
		steps[#steps + 1] = function(c)
			local p, npc = ctx.p(), ctx.npc()
			qa.assert("rq_fetch S: hand-in hidden with no job", call("fetch_open_sid", p, npc) == false, tostring(call("fetch_open_sid", p, npc)))
			L.give_item(p, "af_medusa_soc", 1)   -- the item alone does not open it
			return L.wait(3)
		end
		steps[#steps + 1] = function(c)
			local p, npc = ctx.p(), ctx.npc()
			qa.assert("rq_fetch S: hand-in hidden with the item but no job", call("fetch_open_sid", p, npc) == false, tostring(call("fetch_open_sid", p, npc)))
		end
		job_steps(steps, by_id.rq_sid_art1, ctx, true, { item_given = true, while_running = function(c)
			local p, npc = ctx.p(), ctx.npc()
			local got = offers(jobs, "sid", p, npc)
			qa.assert("rq_fetch S: art1 running: no other artifact order, the part order stays", got == "rq_sid_part2", got)
		end })
		steps[#steps + 1] = function(c)
			local p, npc = ctx.p(), ctx.npc()
			local got = offers(jobs, "sid", p, npc)
			qa.assert("rq_fetch S: art1 on cooldown: art2 (next priority) is offered", got == "rq_sid_art2,rq_sid_part2", got)
		end
		job_steps(steps, by_id.rq_sid_part2, ctx, true)
		steps[#steps + 1] = function(c)
			local p, npc = ctx.p(), ctx.npc()
			local got = offers(jobs, "sid", p, npc)
			qa.assert("rq_fetch S: the bloodsucker part needs the military case flag: not offered yet", got == "rq_sid_art2", got)
			L.flag_give("AGR_START_BREAK_INTO_A_MILITARY_BASE_QUEST_TASK_INFO")
			return L.wait(1)
		end
		steps[#steps + 1] = function(c)
			local p, npc = ctx.p(), ctx.npc()
			local got = offers(jobs, "sid", p, npc)
			qa.assert("rq_fetch S: with the case flag the bloodsucker part is offered", got == "rq_sid_art2,rq_sid_part1", got)
		end
	end
	-- A: every other job through the same functions (no PDA task: the task needs the job's own level)
	for _, j in ipairs(jobs) do
		local done_above = (lvl == "coop_l01_escape") and (j.id == "rq_sid_art1" or j.id == "rq_sid_part2")
		if not done_above then job_steps(steps, j, ctx, j.level == lvl) end
	end
	steps[#steps + 1] = function(c)
		local p, npc = ctx.p(), ctx.npc()
		local bad = {}
		for _, g in ipairs({ "sid", "bar", "sak", "fre" }) do
			if call("fetch_open_" .. g, p, npc) ~= false then bad[#bad + 1] = g end
		end
		qa.assert("rq_fetch: hand-in closed at every giver after all jobs", #bad == 0, table.concat(bad, ","))
		qa.event("rq_fetch done level " .. tostring(lvl) .. " jobs " .. tostring(#jobs))
	end
	L.task("rq_fetch", steps)
end)
