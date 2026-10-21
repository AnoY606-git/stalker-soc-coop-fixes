--@qa_lib
-- Sidorovich's bunker door and the flash drive hand-in (test only, never shipped).
-- Bug (v1.4): a player with the flash drive and the quest could not get into the bunker. The door closed again in the same frame because its
-- zone was a small box at the top of the entrance stairs (esc_trader_door_space_restrictor, 11 m from the door). New logic: the door follows
-- esc_sr_no_weapon_space_restrictor (the whole bunker): open while any player is inside, closed when nobody is.
--
-- ONE listen-host run per mode (in listen mode client A IS the host, so -Clients 1 is one player):
--   STORY mode (default): the host is the Marked One and spawns in the bunker in front of Sidorovich's counter.
--   NON-STORY mode (environment variable DOOR_NONSTORY=1 in the shell that starts run_coop.ps1): the hook gives the story flag
--     COOP_OPEN_TEST_NONSTORY at load, so the host counts as a non-story player and is moved to the rookie village campfire (v1.4.1 start).
--
-- Steps (door state read from the real object: db.storage[id].active_section and door_action:is_open() / is_closed(), the joint angle):
--   1  spawn state: story = door open (a player is inside the bunker), non-story = door closed (nobody inside)
--   2  stage of the bug: the flash drive is given, the talk flags are set, ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO is NOT set;
--      the hand-in precondition (dialogs_coop_l01_escape.if_actor_has_dev_flash_sidorovich) is true and the dialog is not blocked by its flag
--   3  teleport to the village (outside the bunker): the door closes (nobody inside)
--   4  teleport to the stairs bottom / the first room: the door OPENS by itself (any player inside) and stays open
--   5  the player at the door presses "use" (door_action:use_callback, like the engine's use): still open, never closes in his face
--   6  teleport in front of Sidorovich's counter, open the talk window with Sidorovich: is_talking, precondition still true, door open
--   7  teleport out again: the door closes; teleport in once more: it opens again
-- Lines in qa_events.log: DOORCHK ...
-- run_coop.ps1 -Map coop_l01_escape -Mode listen -Clients 1 -Owner doorchk -ExtraDir <stage>\gamedata -Hooks patches\cordon\tests\door_check.lua -SoakSeconds 150 -CompareTimeout 10 -ResultDir <dir>
local L = qa_lib
local function safe(f, ...) local ok, r = pcall(f, ...) if ok then return r end return nil end
local function ev(s) qa.event("DOORCHK " .. s) end

local NONSTORY = (safe(function() return os.getenv("DOOR_NONSTORY") end) == "1")
local FLASH = "dev_flash_sidorovich"
local FLESH_STOP = "ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_FLESH_STOP_DIALOG_INFO"
local P = {
	village = { -242.9, -19.4, -123.9 },      -- outside, 11 m from the stairs top, not in any bunker zone
	stairs_bottom = { -254.1, -23.4, -134.4 }, -- inside the bunker box (corridor start)
	first_room = { -249.9, -24.8, -134.4 },    -- first room, 1.6 m west of the door
	front_room = { -247.1, -24.8, -134.4 },    -- in front of Sidorovich's counter (the story spawn room)
}

-- ---------------------------------------------------------------------------------------------- door state
local function door()
	local o = safe(function() return level.object("esc_trader_door") end)
	if o == nil then return nil end
	local id = o:id()
	local st = db.storage[id]
	local act = st and st.ph_door and st.ph_door.door_action
	return {
		obj = o, id = id, st = st, act = act,
		section = st and st.active_section or "?",
		open = act ~= nil and safe(function() return act:is_open() end) == true,
		closed = act ~= nil and safe(function() return act:is_closed() end) == true,
	}
end
local function dstate(tag)
	local d = door()
	if d == nil then ev(tag .. " door object not online") return nil end
	ev(string.format("%s door section=%s is_open=%s is_closed=%s", tag, tostring(d.section), tostring(d.open), tostring(d.closed)))
	return d
end
local function is_open() local d = door() return d ~= nil and d.open end
local function is_closed() local d = door() return d ~= nil and d.closed end

local function pos_of(lo)
	local p = lo and lo:position()
	return p and string.format("%.2f,%.2f,%.2f", p.x, p.y, p.z) or "?"
end
local function dist2(lo, a)
	local p = lo:position()
	return math.sqrt((p.x - a[1]) ^ 2 + (p.z - a[3]) ^ 2)
end

local function precondition(lo)
	local ok, r = pcall(function() return dialogs_coop_l01_escape.if_actor_has_dev_flash_sidorovich(lo, nil) end)
	return ok and r == true
end

-- the test flag must exist before the host's first settle (2.5 s after he left the lobby)
if NONSTORY then
	qa.once("door_flag", function(t, lo)
		if safe(OnServer) then pcall(story_flags.give_flag, "COOP_OPEN_TEST_NONSTORY"); ev("test flag COOP_OPEN_TEST_NONSTORY given (host counts as non-story)") end
	end)
end

qa.once("door_run", function(t, lo0)
	ev("mode=" .. (NONSTORY and "NON-STORY" or "STORY"))
	local lo
	L.task("door_check", {
		function(c) return L.wait(NONSTORY and 18 or 12) end,
		-- 1 spawn state
		function(c)
			lo = L.local_player()
			if lo == nil then qa.assert("a local player exists", false) return L.done(false) end
			ev("host at " .. pos_of(lo))
			if NONSTORY then
				qa.assert("non-story: moved to the campfire (not in the bunker)", dist2(lo, P.front_room) > 20, pos_of(lo))
				return L.wait_for(is_closed, 15)
			end
			qa.assert("story: spawned in the bunker", dist2(lo, P.front_room) < 4, pos_of(lo))
			return L.wait_for(is_open, 15)
		end,
		function(c, ok)
			local d = dstate("spawn state")
			if NONSTORY then
				qa.assert("non-story: nobody inside the bunker, the door is closed", ok == true and d ~= nil and d.closed, d and d.section)
			else
				qa.assert("story: a player is inside the bunker, the door is open", ok == true and d ~= nil and d.open, d and d.section)
			end
			return L.screenshot(NONSTORY and "door_spawn_nonstory" or "door_spawn_story")
		end,
		-- 2 the stage of the bug: flash drive + quest, not handed in yet
		function(c)
			for _, f in ipairs({ "COOP_SOC_OPENING_TALKED", "ESC_START_TALK_TO_THE_SIDOROVICH_QUEST_TASK_INFO", "ESC_SMART_TERRAIN_1_TRADER_SIDOROVICH_TALK_TO_THE_WOLF_STOP_DIALOG_INFO" }) do
				if not L.flag_has(f) then L.flag_give(f) end
			end
			if L.flag_has(FLESH_STOP) then L.flag_clear(FLESH_STOP) end
			L.give_item(nil, FLASH, 1)
			return L.wait(3)
		end,
		function(c)
			local n = L.count_item(nil, FLASH) or 0
			ev("flash drives in the inventory: " .. tostring(n))
			qa.assert("the player carries the flash drive", n >= 1, tostring(n))
			qa.assert("hand-in flag " .. FLESH_STOP .. " is NOT set", not L.flag_has(FLESH_STOP))
			qa.assert("hand-in dialog precondition (if_actor_has_dev_flash_sidorovich) is true for the carrier", precondition(lo))
			return L.teleport(nil, P.village)
		end,
		-- 3 outside: closed
		function(c, ok) qa.assert("teleported to the village", ok == true) return L.wait_for(is_closed, 20) end,
		function(c, ok)
			local d = dstate("village")
			qa.assert("nobody inside the bunker: the door closes", ok == true and d ~= nil and d.closed, d and d.section)
			return L.teleport(nil, P.stairs_bottom)
		end,
		-- 4 entering: opens by itself and stays open
		function(c, ok) qa.assert("teleported to the stairs bottom", ok == true) return L.wait_for(is_open, 15) end,
		function(c, ok)
			local d = dstate("stairs bottom")
			qa.assert("a player entered the bunker: the door opens by itself", ok == true and d ~= nil and d.open and d.section == "ph_door@open", d and d.section)
			return L.teleport(nil, P.first_room)
		end,
		function(c, ok) return L.wait(4) end,
		function(c)
			local d = dstate("first room")
			qa.assert("first room (1.6 m from the door): still open", d ~= nil and d.open, d and d.section)
			-- 5 use at the door: never closes it
			local used = d ~= nil and d.act ~= nil and pcall(function() d.act:use_callback(d.obj, lo) end)
			ev("use_callback called: " .. tostring(used))
			return L.wait(4)
		end,
		function(c)
			local d = dstate("after use")
			qa.assert("after 'use' at the door: still open (never closes in the player's face)", d ~= nil and d.open and d.section == "ph_door@open", d and d.section)
			return L.teleport(nil, P.front_room)
		end,
		-- 6 in front of Sidorovich: talk
		function(c, ok) qa.assert("teleported in front of the counter", ok == true) return L.wait(3) end,
		function(c)
			local d = dstate("front room")
			qa.assert("in front of the counter: door open", d ~= nil and d.open, d and d.section)
			return L.open_talk("sidorovich", { shot = NONSTORY and "door_talk_nonstory" or "door_talk_story" })
		end,
		function(c, ok, why, shot)
			qa.assert("Sidorovich's talk window opens for the carrier (is_talking)", ok == true, tostring(why) .. " " .. tostring(shot))
			qa.assert("hand-in dialog precondition still true while talking", precondition(lo))
			L.close_talk()
			return L.wait(2)
		end,
		-- 7 out and in again
		function(c) return L.teleport(nil, P.village) end,
		function(c, ok) return L.wait_for(is_closed, 20) end,
		function(c, ok)
			local d = dstate("out again")
			qa.assert("outside again: the door closes again", ok == true and d ~= nil and d.closed, d and d.section)
			return L.teleport(nil, P.first_room)
		end,
		function(c, ok) return L.wait_for(is_open, 15) end,
		function(c, ok)
			local d = dstate("in again")
			qa.assert("inside again: the door opens again", ok == true and d ~= nil and d.open, d and d.section)
			qa.assert("hand-in dialog precondition true at the end", precondition(lo) and not L.flag_has(FLESH_STOP))
			return L.screenshot(NONSTORY and "door_end_nonstory" or "door_end_story")
		end,
		function(c) ev("done") return L.done(true) end,
	})
end)
