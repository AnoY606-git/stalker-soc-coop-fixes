--@qa_lib
-- Cordon start check (test only), ONE listen-host run, covers: spawn place, no PDA prompt / no subtitles / no hint pop-ups, the start task chain,
-- and the voice language per player setting (rus, eng, auto) incl. the start dialog voice.
--   run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner openchk -ExtraDir <stage>\gamedata -Hooks <this file> -SoakSeconds 200 -ResultDir <dir>
--   Russian game for the auto phase:  qa_lang.ps1 -Lang rus ... (same -RunCoopArgs), see the test plan in NOTES.md
-- Lines in qa_events.log:  OPENCHK ...  (and BOT SCENE opening SAY ... / BOT SOCOPEN ... copied from the scripts' own log calls)
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("OPENCHK " .. s) end

-- the scripts log through cs_bot.log when it exists: capture those lines (SAY / VOICE / VOICE_PLAY / NOVOICE)
local said = {}
rawset(_G, "cs_bot", { log = function(s) said[#said + 1] = s; qa.event("BOT " .. tostring(s)) end })

local SIDOR = { x = -244.69, z = -133.96 }           -- Sidorovich behind the counter (cover esc_smart_terrain_1_animpoint_3)
local FRONT = { x1 = -248.0, x2 = -246.0, z1 = -135.9, z2 = -133.2 }   -- the room in front of the counter: door wall at x -248.2, counter at x -246.0
local SETFILE = nil
local function setfile()
	if SETFILE == nil then SETFILE = getFS():update_path("$app_data_root$", "coop_settings.ltx") end
	return SETFILE
end

local function write_setting(v)
	local f = io.open(setfile(), "w")
	f:write("[client]\nvoice_language = " .. v .. "\n")
	f:close()
	coop_soc_opening.voice_reset()
end

local function game_lang()
	local l = L.language()
	return l or "eng"
end

-- number of SAY / VOICE lines seen so far, to look only at new ones
local function since(n, pat)
	for i = n + 1, #said do
		if string.find(said[i], pat, 1, true) then return said[i] end
	end
	return nil
end

-- modal windows (message box) seen during the run: the PDA prompt used to be a yes / no message box at the end of the intro
local modal_seen = 0
local talking_phase = false
qa.hooks.openchk_modal = function(t, lo)
	if not safe(OnServer) then return end
	local r = safe(function() return level.main_input_receiver() end)
	if r ~= nil and not talking_phase then
		modal_seen = modal_seen + 1
		if modal_seen == 1 then ev("MODAL window seen at t=" .. string.format("%.0f", t)) end
	end
end

local function spawn_report()
	local lo = L.local_player()
	if lo == nil then ev("no local player") return end
	local p, d = lo:position(), lo:direction()
	local dx, dz = SIDOR.x - p.x, SIDOR.z - p.z
	local len = math.sqrt(dx * dx + dz * dz)
	local dot = (dx * d.x + dz * d.z) / math.max(len, 0.001) / math.max(math.sqrt(d.x * d.x + d.z * d.z), 0.001)
	local in_front = p.x >= FRONT.x1 and p.x <= FRONT.x2 and p.z >= FRONT.z1 and p.z <= FRONT.z2 and p.y > -25.4 and p.y < -24.4
	ev(string.format("SPAWN pos=%.2f,%.2f,%.2f sidor_dist=%.2f facing_dot=%.2f in_front_room=%s past_door_x=%s", p.x, p.y, p.z, len, dot, tostring(in_front), tostring(p.x > -248.0)))
	qa.assert("spawn: inside the room in front of Sidorovich's counter (x -248.0..-246.0, z -135.9..-133.2, floor y -24.8), not behind the door", in_front,
		string.format("%.2f %.2f %.2f", p.x, p.y, p.z))
	qa.assert("spawn: faces Sidorovich", dot > 0.7, string.format("%.2f", dot))
	qa.assert("spawn: close to Sidorovich (less than 3 m)", len < 3.0, string.format("%.2f", len))
end

local function tasks_report(tag)
	local lo = L.local_player()
	local have, ids = 0, { "esc_start_main_quest_task", "esc_start_talk_to_the_sidorovich_quest_task" }
	local out = {}
	for _, id in ipairs(ids) do
		local t = lo and safe(function() return lo:get_task(id, true) end)
		out[#out + 1] = id .. "=" .. (t ~= nil and "yes" or "no")
		if t ~= nil then have = have + 1 end
	end
	ev(tag .. " TASKS " .. table.concat(out, " "))
	return have
end

-- greeting round trip: leave Sidorovich (> 12 m), come back (< 3 m): sidor_greet plays a hello line on THIS client
local function greet_phase(name, setting, expect_lang)
	local mark = 0
	local steps = {
		function(c) write_setting(setting); mark = #said
			local got = coop_soc_opening.voice_lang()
			ev("PHASE " .. name .. " voice_lang()=" .. tostring(got) .. " game=" .. game_lang())
			qa.assert("voice phase " .. name .. ": voice_lang() is " .. expect_lang, got == expect_lang, tostring(got))
			return L.now(true) end,
		function(c) return L.teleport(nil, { -206.9, -19.6, -140.1 }) end,                           -- far away: resets the greeting state
		function(c) return L.wait(4) end,
		function(c) return L.teleport(nil, { -246.4, -24.8, -134.4 }, vector():set(1, 0, 0)) end,   -- 1.7 m in front of Sidorovich
		function(c) return L.wait(7) end,
		function(c)
			local line = since(mark, "SAY hello")
			ev("PHASE " .. name .. " line: " .. tostring(line))
			qa.assert("voice phase " .. name .. ": a hello line was chosen in " .. expect_lang, line ~= nil and string.find(line, "lang=" .. expect_lang, 1, true) ~= nil, tostring(line))
			if line ~= nil then
				local eng_dir = string.find(line, "script_replics\\trader\\eng\\", 1, true) ~= nil
				local ok = (expect_lang == "eng") == eng_dir
				qa.assert("voice phase " .. name .. ": the sound path is under " .. (expect_lang == "eng" and "trader\\eng" or "trader (Russian)"), ok, line)
				qa.assert("voice phase " .. name .. ": the file exists (audio=true)", string.find(line, "audio=true", 1, true) ~= nil, line)
			end
			return L.now(true)
		end,
	}
	return steps
end

local function add(list, more) for _, f in ipairs(more) do list[#list + 1] = f end end

qa.once("openchk_run", function(t, lo)
	-- deleted API of the PDA prompt
	qa.assert("PDA prompt code is gone (coop_scn_opening.offer_pda_tutorial_client)", coop_scn_opening.offer_pda_tutorial_client == nil)
	qa.assert("PDA prompt code is gone (coop_scn_opening.on_pda_yes)", coop_scn_opening.on_pda_yes == nil)
	local steps = {
		function(c) return L.wait(3) end,
		function(c) spawn_report(); tasks_report("t+3"); return L.screenshot("openchk_spawn") end,
		function(c) return L.wait(25) end,
		function(c) ev("t+30 tutorial_active=" .. tostring(safe(game.has_active_tutorial)) .. " (monolog is playing, nothing else on screen)"); return L.screenshot("openchk_monolog") end,
		function(c) return L.wait(80) end,
		function(c)
			-- the intro (Sidorovich's speech) is over: no yes / no box, no tutorial window, both start tasks present
			local act = safe(game.has_active_tutorial)
			ev("t+110 tutorial_active=" .. tostring(act) .. " modal_seen=" .. modal_seen)
			qa.assert("no PDA prompt / message box appeared during the start (main input receiver stayed empty)", modal_seen == 0, modal_seen)
			qa.assert("no tutorial / hint window is open after the intro", act ~= true, tostring(act))
			qa.assert("start chain still gives both first tasks", tasks_report("t+110") == 2)
			return L.screenshot("openchk_after_intro")
		end,
	}
	-- voice per setting (hello lines); the game language decides what auto means
	local gl = game_lang()
	add(steps, greet_phase("rus", "rus", "rus"))
	add(steps, greet_phase("eng", "eng", "eng"))
	add(steps, greet_phase("auto", "auto", gl))
	add(steps, greet_phase("bad", "banana", gl))
	-- start dialog voice with the setting left by the last phase: English files exist for phrases 3 and 321, no Russian ones
	steps[#steps + 1] = function(c) write_setting("auto"); talking_phase = true; return L.now(true) end
	steps[#steps + 1] = function(c) return L.open_talk("esc_smart_terrain_1_trader_sidorovich", { shot = "openchk_talk" }) end
	steps[#steps + 1] = function(c, ok, why) ev("open_talk ok=" .. tostring(ok) .. " " .. tostring(why)); return L.wait(6) end
	steps[#steps + 1] = function(c)
		local play = since(0, "VOICE_PLAY key=3")
		local none = since(0, "NOVOICE key=3")
		ev("DIALOG voice: play=" .. tostring(play) .. " none=" .. tostring(none))
		if gl == "eng" then
			qa.assert("dialog phrase 3 voice: English file played (auto in an English game)", play ~= nil and string.find(play, "lang=eng", 1, true) ~= nil and string.find(play, "dialogs\\eng\\", 1, true) ~= nil, tostring(play))
		else
			qa.assert("dialog phrase 3 voice: silent (no Russian recording) in a Russian game", none ~= nil and play == nil, tostring(none))
		end
		L.close_talk()
		talking_phase = false
		ev("done")
		return L.done(true)
	end
	L.task("openchk", steps)
end)
