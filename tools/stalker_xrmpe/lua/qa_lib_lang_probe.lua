--@qa_lib
-- TEST ONLY: proves tools\stalker_xrmpe\qa_lang.ps1 (registry InstallLang switch, always restored).  Asserts that the engine mounted the
-- language given with  -Cfg lang=rus|eng  (default rus) and writes the translated string to qa_events.log.
--   powershell -NoProfile -ExecutionPolicy Bypass -File qa_lang.ps1 -Lang rus -Owner botlang -Expect 1 `
--     -RunCoopArgs "-Map coop_l01_escape -Owner botlang -Mode listen -Clients 1 -Cfg lang=rus -Hooks C:\...\lua\qa_lib_lang_probe.lua -SoakSeconds 20 -CompareTimeout 5 -ResultDir C:\...\res"
local L = qa_lib

qa.once("qa_lib_lang_probe", function(t, lo)
	if _G.__qa_lang_probe then return end
	_G.__qa_lang_probe = true
	local want = qa.cfg.lang or "rus"
	local lang, s = L.language()
	local bytes = {}
	for i = 1, math.min(#tostring(s), 12) do bytes[#bytes + 1] = string.format("%02X", string.byte(s, i)) end
	L.ev("LANG probe: language()=" .. tostring(lang) .. " string bytes " .. table.concat(bytes, " "))
	qa.assert("QL language() reports the mounted language", lang == want, "want " .. want .. ", got " .. tostring(lang))
end)
