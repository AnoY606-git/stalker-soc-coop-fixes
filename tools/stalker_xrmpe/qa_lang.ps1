# Run any command with the xrMPE game language switched, and ALWAYS put the registry value back.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File qa_lang.ps1 -Lang rus -Owner botlang -Expect 1 `
#       -RunCoopArgs "-Map coop_l01_escape -Owner botlang -Mode listen -Clients 1 -Hooks C:\x\my.lua -SoakSeconds 60 -ResultDir C:\x\res"
#   (-RunCoopArgs is ONE quoted string handed to run_coop.ps1 unchanged; -Owner inside it should equal this script's -Owner.
#    For another program use  -Exe <path> -ExeArgs "<one string>"  instead.)
#   qa_lang.ps1 -Restore            # repair after a crash of this script (uses the saved original in slot_state\qa_lang_original.txt)
#
# How the language is chosen in xrMPE 0.9 (repeatable_quests\NOTES.md): the registry value
#   HKCU\Software\X-Ray Multiplayer Extension\InstallLang   (eng | rus | ukr)
# mounts game\localization\<lang>.db when the engine initialises its file system (a few seconds after the process starts).
# A configs\localization.ltx inside an addon is ignored.  So the value only has to be switched while the clients START.
#
# What this script does:
#   1. remembers the current value (also in slot_state\qa_lang_original.txt, so -Restore works after a crash),
#   2. sets InstallLang = <Lang>,
#   3. starts the command, and watches the per-run logs  game\_appdata_qa_<Owner>*\logs\xray_*.log  for "Init FileSystem"
#      (the file system is initialised: the language is read) in as many logs as -Expect (default 1; use 2 for dedicated + 1 client),
#   4. restores the value (in a finally block, also when the command fails, after -HoldSeconds at the latest),
#   5. waits for the command to finish and returns its exit code.
# While the value is switched (normally 5 to 40 s) any OTHER game started on this PC would also get that language, so use it when
# no other agent is launching, or keep the window short.  The owner's own _appdata_ is never touched.
param(
    [string]$Lang = "rus",
    [string]$Owner = "",                 # slot owner / -Owner value of the wrapped run_coop (used to find its log folders)
    [int]$Expect = 1,                    # number of game processes that must have initialised their file system before the restore
    [int]$HoldSeconds = 90,              # restore after this long even if the logs were not seen (counted from the switch)
    [int]$QueueSeconds = 3600,           # how long to wait for run_coop to reach its launch before switching
    [string]$ResultDir = "",             # -ResultDir of the wrapped run (parsed from -RunCoopArgs when empty)
    [switch]$Restore,
    [string]$Game = "C:\X-Ray Multiplayer Extension\game",
    [string]$RunCoopArgs = "",
    [string]$Exe = "",
    [string]$ExeArgs = ""
)
$key = "HKCU:\Software\X-Ray Multiplayer Extension"
$name = "InstallLang"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$saved = Join-Path $here "slot_state\qa_lang_original.txt"
function Get-Lang { try { return (Get-ItemProperty -Path $key -Name $name -ErrorAction Stop).$name } catch { return $null } }
function Set-Lang($v) { Set-ItemProperty -Path $key -Name $name -Value $v -ErrorAction Stop }

if ($Restore) {
    if (Test-Path $saved) {
        $orig = (Get-Content $saved -Raw).Trim()
        if ($orig) { Set-Lang $orig; Write-Host "restored InstallLang = $orig"; Remove-Item $saved -Force }
    } else { Write-Host "nothing to restore (no $saved); InstallLang is $(Get-Lang)" }
    exit 0
}
if ($RunCoopArgs -eq "" -and $Exe -eq "") { Write-Host "no command given: use -RunCoopArgs or -Exe/-ExeArgs"; exit 3 }
if ($RunCoopArgs -ne "") {
    $Exe = "powershell"
    $ExeArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $here 'run_coop.ps1')`" $RunCoopArgs"
}
if (-not (Test-Path $key)) { Write-Host "registry key not found: $key"; exit 3 }
$orig = Get-Lang
if (Test-Path $saved) {
    # an earlier run died before restoring: that file holds the TRUE original
    $orig = (Get-Content $saved -Raw).Trim()
    Write-Host "found an unrestored earlier switch, original is $orig"
} else {
    New-Item -ItemType Directory -Force (Split-Path $saved) | Out-Null
    Set-Content -Path $saved -Value $orig -Encoding ascii
}
$exit = 0
$proc = $null
# -ResultDir of the wrapped run_coop (its run.log tells when the game is about to start)
if ($ResultDir -eq "" -and $RunCoopArgs -match '-ResultDir\s+"?([^"\s]+)"?') { $ResultDir = $Matches[1] }
function Read-Shared($path) {
    try {
        $fs = [System.IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::GetEncoding(1251))
        $t = $sr.ReadToEnd(); $sr.Close(); $fs.Close(); return $t
    } catch { return "" }
}
try {
    $proc = Start-Process -FilePath $Exe -ArgumentList $ExeArgs -NoNewWindow -PassThru
    $tq = Get-Date
    if ($ResultDir -ne "") {
        # Queued behind other runs (slot, stray engines) for minutes: keep the registry untouched until run_coop has built the test addon
        # (its log line "BUILD_OK"), which happens right before it launches the game.
        $runlog = Join-Path $ResultDir "run.log"
        while (-not $proc.HasExited -and ((Get-Date) - $tq).TotalSeconds -lt $QueueSeconds) {
            if ((Test-Path $runlog) -and ((Read-Shared $runlog) -match "BUILD_OK")) { break }
            Start-Sleep -Milliseconds 500
        }
        Write-Host ("waited {0:N0} s for the run to reach its launch" -f ((Get-Date) - $tq).TotalSeconds)
    }
    Set-Lang $Lang
    Write-Host "InstallLang: $orig -> $(Get-Lang) (restored automatically)"
    $t0 = Get-Date
    $ready = $false
    while (((Get-Date) - $t0).TotalSeconds -lt $HoldSeconds -and -not $proc.HasExited) {
        if ($Owner -ne "") {
            $n = 0
            foreach ($d in (Get-ChildItem -Path $Game -Directory -Filter "_appdata_qa_$Owner*" -ErrorAction SilentlyContinue)) {
                foreach ($lg in (Get-ChildItem -Path (Join-Path $d.FullName "logs") -Filter "xray_*.log" -ErrorAction SilentlyContinue)) {
                    if ((Read-Shared $lg.FullName) -match "Init FileSystem") { $n++ }
                }
            }
            if ($n -ge $Expect) { $ready = $true; break }
        } else {
            # no owner given: hold a fixed 45 s (the file system initialises within the first seconds)
            if (((Get-Date) - $t0).TotalSeconds -ge 45) { $ready = $true; break }
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host ("language window: {0:N0} s, file system initialised in the run: {1}" -f ((Get-Date) - $t0).TotalSeconds, $ready)
} finally {
    try { Set-Lang $orig; Remove-Item $saved -Force -ErrorAction SilentlyContinue; Write-Host "InstallLang restored to $(Get-Lang)" } catch { Write-Host "RESTORE FAILED: run qa_lang.ps1 -Restore" }
}
if ($proc -ne $null) { $proc.WaitForExit(); $exit = $proc.ExitCode }
exit $exit
