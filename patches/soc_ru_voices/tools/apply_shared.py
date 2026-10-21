"""Patch soc_ru_voices: edits of files that OTHER patches ship (the Lua voice tables get a Russian slot), plus their offline tests and notes.
usage: python -I patches\\soc_ru_voices\\tools\\apply_shared.py <repo root>
Idempotent: an edit whose new text is already in the file is skipped; an edit whose old text is missing (and new text absent) stops the script.
The Russian recordings themselves are in patches\\soc_ru_voices\\gamedata (stock SoC paths sounds\\characters_voice\\dialogs\\<name>.ogg,
the English ones stay under ...\\dialogs\\eng\\).
"""
import os, sys

root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
BS = "\\"
changed = []
skipped = []


def edit(rel, old, new, what):
    path = os.path.join(root, *rel.split("/"))
    raw = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    if new in text:
        skipped.append(what)
        return
    if old not in text:
        sys.exit("FAIL: %s: expected text not found in %s" % (what, rel))
    if text.count(old) != 1:
        sys.exit("FAIL: %s: text found %d times in %s" % (what, text.count(old), rel))
    text = text.replace(old, new)
    if crlf:
        text = text.replace("\n", "\r\n")
    open(path, "wb").write(text.encode("utf-8"))
    changed.append(what)


# ------------------------------------------------------------------------------------------------ Barkeep (soc_dv_x18_quests)
BAR = "patches/soc_dv_x18_quests/gamedata/scripts/coop_soc_bar.script"
edit(BAR,
     '-- SoC phrase id -> recording (English Steam SoC: sounds\\characters_voice\\dialogs\\<id>.ogg, here under ...\\dialogs\\eng\\)\n'
     'local VOICE = {}\n'
     'for _, id in ipairs({ "2", "221", "151", "15111", "171", "1721", "17212", "121", "13121", "1314" }) do\n'
     '\tVOICE[id] = { eng = "characters_voice\\\\dialogs\\\\eng\\\\bar_bar_barmen_start_" .. id }\n'
     'end\n',
     '-- SoC phrase id -> recording: English Steam SoC under ...\\dialogs\\eng\\, original Russian SoC at the stock path ...\\dialogs\\<name>.ogg\n'
     '-- (the Russian files ship in patch soc_ru_voices)\n'
     'local VOICE = {}\n'
     'for _, id in ipairs({ "2", "221", "151", "15111", "171", "1721", "17212", "121", "13121", "1314" }) do\n'
     '\tVOICE[id] = { eng = "characters_voice\\\\dialogs\\\\eng\\\\bar_bar_barmen_start_" .. id,\n'
     '\t              rus = "characters_voice\\\\dialogs\\\\bar_bar_barmen_start_" .. id }\n'
     'end\n',
     "barkeep voice table: rus slot")

# ------------------------------------------------------------------------------------------------ Sakharov / Kruglov (soc_yan_x16_quests)
YAN = "patches/soc_yan_x16_quests/gamedata/scripts/coop_soc_yan.script"
edit(YAN,
     'for _, id in ipairs(VOICE_S) do VOICE.s[id] = "characters_voice\\\\dialogs\\\\eng\\\\yantar_general_ucheniy_talk_start_" .. id end\n'
     'for _, id in ipairs(VOICE_K) do VOICE.k[id] = "characters_voice\\\\dialogs\\\\eng\\\\yantar_help_scientist_" .. id end\n',
     '-- English Steam SoC under ...\\dialogs\\eng\\, original Russian SoC at the stock path ...\\dialogs\\<name>.ogg (ships in patch soc_ru_voices)\n'
     'for _, id in ipairs(VOICE_S) do\n'
     '\tVOICE.s[id] = { eng = "characters_voice\\\\dialogs\\\\eng\\\\yantar_general_ucheniy_talk_start_" .. id,\n'
     '\t                rus = "characters_voice\\\\dialogs\\\\yantar_general_ucheniy_talk_start_" .. id }\n'
     'end\n'
     'for _, id in ipairs(VOICE_K) do\n'
     '\tVOICE.k[id] = { eng = "characters_voice\\\\dialogs\\\\eng\\\\yantar_help_scientist_" .. id,\n'
     '\t                rus = "characters_voice\\\\dialogs\\\\yantar_help_scientist_" .. id }\n'
     'end\n',
     "yantar voice tables: rus slot")
edit(YAN,
     '\tif lang() ~= "eng" then return nil end\n'
     '\treturn VOICE[kind] and VOICE[kind][id] or nil\n',
     '\tlocal v = VOICE[kind] and VOICE[kind][id]\n'
     '\treturn v and v[lang()] or nil\n',
     "yantar voice_path per language")

# ------------------------------------------------------------------------------------------------ Sidorovich start dialog (cutscenes_pkg_opening)
OPEN = "patches/cutscenes_pkg_opening/gamedata/scripts/coop_soc_opening.script"
edit(OPEN,
     '\t["3"]   = { eng = "characters_voice\\\\dialogs\\\\eng\\\\escape_trader_start_dialog_3" },\n'
     '\t["321"] = { eng = "characters_voice\\\\dialogs\\\\eng\\\\escape_trader_start_dialog_321" },\n',
     '\t["3"]   = { eng = "characters_voice\\\\dialogs\\\\eng\\\\escape_trader_start_dialog_3",\n'
     '\t            rus = "characters_voice\\\\dialogs\\\\escape_trader_start_dialog_3" },\n'
     '\t["321"] = { eng = "characters_voice\\\\dialogs\\\\eng\\\\escape_trader_start_dialog_321",\n'
     '\t            rus = "characters_voice\\\\dialogs\\\\escape_trader_start_dialog_321" },\n',
     "opening dialog voice table: rus slot")
edit(OPEN,
     '--     (English recording only: the Russian SoC voice files for these two lines are not in the add-on, so with voice_language rus\n'
     '--     they stay silent; the dialog text is on screen as usual)\n',
     '--     (English recordings under dialogs\\eng\\, the original Russian ones at the stock path dialogs\\ from patch soc_ru_voices)\n',
     "opening header comment")

# ------------------------------------------------------------------------------------------------ offline tests
ROOTS_OLD = 'roots = [PATCH, os.path.join(os.path.dirname(PATCH), "bar_soc_quests")]\n'
ROOTS_NEW = 'roots = [PATCH, os.path.join(os.path.dirname(PATCH), "bar_soc_quests"), os.path.join(os.path.dirname(PATCH), "soc_ru_voices")]\n'

DV = "patches/soc_dv_x18_quests/tests/mock_test.py"
edit(DV, ROOTS_OLD, ROOTS_NEW, "dv test: roots incl. soc_ru_voices")
edit(DV,
     '                check("voice %s rus: silent (no Russian recording exists)" % pid, p is None)\n',
     '                ok = p == "characters_voice\\\\dialogs\\\\bar_bar_barmen_start_" + pid and any(os.path.isfile(os.path.join(r, "gamedata", "sounds", p.replace("\\\\", os.sep) + ".ogg")) for r in roots)\n'
     '                check("voice %s rus: Russian file (soc_ru_voices)" % pid, ok, p)\n',
     "dv test: rus path + file")
edit(DV,
     '    check("say_221 with voice_language rus is silent", len(list(E["__played"].values())) == 0)\n',
     '    played = list(E["__played"].values())\n'
     '    check("say_221 with voice_language rus plays the Russian recording", played == ["characters_voice\\\\dialogs\\\\bar_bar_barmen_start_221"], played)\n',
     "dv test: say_221 rus")

BQ = "patches/bar_soc_quests/tests/mock_test.py"
edit(BQ,
     '                check("voice %s rus: silent (no Russian recording exists)" % pid, p is None)\n',
     '                ok = p == "characters_voice\\\\dialogs\\\\bar_bar_barmen_start_" + pid and os.path.isfile(os.path.join(os.path.dirname(PATCH), "soc_ru_voices", "gamedata", "sounds", p.replace("\\\\", os.sep) + ".ogg"))\n'
     '                check("voice %s rus: Russian file ships in soc_ru_voices" % pid, ok, p)\n',
     "bar_soc_quests test: rus path + file")

YT = "patches/soc_yan_x16_quests/tests/mock_test.py"
edit(YT,
     '                    check("voice %s%s rus: silent (no Russian recording exists)" % (kind, i), p is None)\n',
     '                    ok = p is not None and p.endswith(base + i) and "\\\\eng\\\\" not in p and os.path.isfile(os.path.join(os.path.dirname(PATCH), "soc_ru_voices", "gamedata", "sounds", p.replace("\\\\", os.sep) + ".ogg"))\n'
     '                    check("voice %s%s rus: Russian file ships in soc_ru_voices" % (kind, i), ok, p)\n',
     "yantar test: rus path + file")
edit(YT,
     '    check("say_s31 with voice_language rus is silent", len(list(E["__played"].values())) == 0)\n',
     '    played = list(E["__played"].values())\n'
     '    check("say_s31 with voice_language rus plays the Russian recording", played == ["characters_voice\\\\dialogs\\\\yantar_general_ucheniy_talk_start_31"], played)\n',
     "yantar test: say_s31 rus")

OT = "patches/cutscenes_pkg_opening/tests/voice_lang_mock_test.py"
edit(OT,
     '        check("no Russian dialog voice (none exists) " + n, not os.path.exists(os.path.join(snd, "characters_voice", "dialogs", n + ".ogg")))\n',
     '        check("Russian dialog voice ships in soc_ru_voices " + n, os.path.exists(os.path.join(os.path.dirname(PATCH), "soc_ru_voices", "gamedata", "sounds", "characters_voice", "dialogs", n + ".ogg")))\n',
     "opening test: Russian dialog voice")

edit(DV,
     'for _, r in ipairs({ patch_root, patch_root .. "/../bar_soc_quests" }) do\n',
     'for _, r in ipairs({ patch_root, patch_root .. "/../bar_soc_quests", patch_root .. "/../soc_ru_voices" }) do\n',
     "dv test: mock file system sees soc_ru_voices")
edit(YT,
     '\tlocal f = io.open(patch_root .. "/gamedata/sounds/" .. string.gsub(name, "\\\\", "/"), "rb")\n'
     '\tif f then f:close() return true end\n'
     '\treturn false end } end\n',
     '\tfor _, r in ipairs({ patch_root, patch_root .. "/../soc_ru_voices" }) do\n'
     '\t\tlocal f = io.open(r .. "/gamedata/sounds/" .. string.gsub(name, "\\\\", "/"), "rb")\n'
     '\t\tif f then f:close() return true end\n'
     '\tend\n'
     '\treturn false end } end\n',
     "yantar test: mock file system sees soc_ru_voices")
edit("patches/cutscenes_pkg_opening/NOTES.md",
     "(no Russian recording of these two exists, so with `rus` they are silent)",
     "(the Russian recordings of these two are at the stock path `sounds\\characters_voice\\dialogs\\` in patch `soc_ru_voices`)",
     "opening notes: Russian dialog voice")

# Lua in-game hooks (they only run in a game, but must say the truth)
edit("patches/soc_dv_x18_quests/tests/soc_dv_hooks.lua",
     '\t\t\t\t\tqa.assert("voice_language rus: phrase " .. id .. " is silent (the Russian SoC has no dialog voice)", p == nil, tostring(p))\n',
     '\t\t\t\t\tqa.assert("voice_language rus: phrase " .. id .. " plays the Russian file", p == "characters_voice\\\\dialogs\\\\bar_bar_barmen_start_" .. id, tostring(p))\n',
     "dv hooks: rus")
edit("patches/bar_soc_quests/tests/bar_soc_hooks.lua",
     '\t\t\t\t\tqa.assert("voice_language rus: phrase " .. id .. " is silent (the Russian SoC has no dialog voice)", p == nil, tostring(p))\n',
     '\t\t\t\t\tqa.assert("voice_language rus: phrase " .. id .. " plays the Russian file", p == "characters_voice\\\\dialogs\\\\bar_bar_barmen_start_" .. id, tostring(p))\n',
     "bar hooks: rus")
edit("patches/soc_yan_x16_quests/tests/soc_yan_hooks.lua",
     '				elseif lang == "rus" then qa.assert("voice_language rus: phrase " .. id .. " is silent", p == nil, tostring(p)) end\n',
     '				elseif lang == "rus" then qa.assert("voice_language rus: phrase " .. id .. " plays the Russian file", p == "characters_voice\\\\dialogs\\\\yantar_general_ucheniy_talk_start_" .. id, tostring(p)) end\n',
     "yantar hooks: rus")

# ------------------------------------------------------------------------------------------------ notes (statements that are no longer true)
edit("patches/soc_dv_x18_quests/NOTES.md",
     "The Russian SoC (CoP-port add-on `shadow_of_chernobyl.addon`) has NO recording of any Barkeep dialog phrase (it has only hello lines `bar_barman_hello_1..5` and scenario lines), so with `rus` the lines are silent, the text is on screen.",
     "The original Russian recordings of the same 10 phrases (FOSTER's upload of the Russian SoC sounds) ship in patch `soc_ru_voices` at the stock path `sounds\\characters_voice\\dialogs\\bar_bar_barmen_start_<id>.ogg`; with `rus` they play from the `rus` slot of the table.",
     "dv notes: Russian voice")
edit("patches/soc_dv_x18_quests/NOTES.md",
     "- No Russian Barkeep voice exists in the sources.",
     "- The Russian Barkeep voice ships in patch `soc_ru_voices` (see its NOTES.md).",
     "dv notes: no Russian line")

print("changed:", len(changed))
for c in changed:
    print("  +", c)
print("skipped (already applied):", len(skipped))
