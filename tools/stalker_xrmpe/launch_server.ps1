# Boots one xrMPE dedicated server + local client, waits for the result, kills it, prints a summary.
# Always launch the engine through this script (PowerShell), never from bash: bash eats the "\f" in
# "..\fsgame_s.ltx" and the engine pops a "Cannot open file ..sgame_s.ltx" box on the owner's screen.
#
# Usage (from any shell):
#   powershell -NoProfile -ExecutionPolicy Bypass -File launch_server.ps1 -Addon cs_coop_dev.addon -Map marsh [-SoakSeconds 30] [-TimeoutSeconds 240] [-ExtraArgs "-use_all_spawn"] [-LogCopy C:\path\run.log]
#   -Listen: ONE process that is server + a real local player (bin\xrEngine.exe, not the dedicated exe), for tests that
#            need a spawned player. It never touches the owner's _appdata_: it runs with its own fsgame_csboot.ltx and
#            _appdata_csboot\ (created here; user.ltx copied from the owner's with: windowed 800x600, sound muted,
#            rs_always_active on so it keeps running unfocused). Delete fsgame_csboot.ltx and _appdata_csboot when done.
#   Game slot (2026-10-18): the script takes the shared slot lock (stalker_slot.py) before launching and releases it after,
#   so concurrent agents queue instead of colliding. -Owner <lane> names you (default ls-<pid>), -SlotWait <s> (default 900)
#   how long to queue, -NoSlot to skip, -BusyWait <s> to keep polling while the OWNER's own game is running (default 0 = BUSY now).
#   Exit 2 = BUSY (slot held or owner playing), 3 = no addon.
param(
    [Parameter(Mandatory = $true)][string]$Addon,
    [Parameter(Mandatory = $true)][string]$Map,
    [int]$SoakSeconds = 30,
    [int]$TimeoutSeconds = 240,
    [string]$ExtraArgs = "",
    [string]$LogCopy = "",
    [string]$Game = "C:\X-Ray Multiplayer Extension\game",
    [switch]$Listen,
    [string]$Owner = "",
    [int]$SlotWait = 900,
    [switch]$NoSlot,
    [int]$BusyWait = 0,
    [switch]$KeepSlot,      # you hold the slot yourself (you built a test addon copy inside your lease): do not release it at the end
    [switch]$DeleteAddon    # delete -Addon (a test copy) before releasing the slot
)

if (-not (Test-Path (Join-Path $Game "addons\$Addon"))) { "NO ADDON: $Game\addons\$Addon"; exit 3 }

$slotPy = Join-Path $PSScriptRoot "stalker_slot.py"
if ($Owner -eq "") { $Owner = "ls-$PID" }
$haveSlot = $false
$slot = 0   # slot index: slot 0 keeps the historic names/port, slots 1 and 2 get their own appdata, fsgame copy and port
if (-not $NoSlot) {
    $ttl = $TimeoutSeconds + $SoakSeconds + 180
    $opArgs = if ($KeepSlot) { @() } else { @("--ownerpid", "$PID") }   # a caller that keeps the slot already registered its own pid
    $r = & python -I $slotPy acquire --owner $Owner --ttl $ttl --wait $SlotWait @opArgs 2>&1
    "SLOT: $r"
    if ($LASTEXITCODE -ne 0) { "BUSY: game slot held by another agent ($r). Not launching."; exit 2 }
    $haveSlot = $true
    if ("$r" -match "SLOTS (\d+)") { $slot = [int]$Matches[1] }
}
function Release-Slot {
    if ($DeleteAddon -and $Addon -notin @("coop.addon", "xrmpe_callofpripyat.addon", "xrmpe_new_year_event.addon")) {
        for ($t = 0; $t -lt 15; $t++) { Remove-Item (Join-Path $Game "addons\$Addon") -Force -ErrorAction SilentlyContinue; if (-not (Test-Path (Join-Path $Game "addons\$Addon"))) { break }; Start-Sleep 2 }
    }
    if ($haveSlot -and -not $KeepSlot) { & python -I $slotPy release --owner $Owner | Out-Null } }

# Max 3 test addon copies at once (one per slot): refuse if 3 OTHER test addons exist (disk/RAM overload crashed the owner's PC on 2026-10-18).
$shipped = @("coop.addon", "xrmpe_callofpripyat.addon", "xrmpe_new_year_event.addon")
$others = @(Get-ChildItem (Join-Path $Game "addons") -Filter *.addon | Where-Object { $shipped -notcontains $_.Name -and $_.Name -ne $Addon } | ForEach-Object { $_.Name })
if ($others.Count -ge 3) { Release-Slot; "REFUSED: other test addon(s) exist: $($others -join ', '). At most 3 test addon copies may exist at a time; wait for its owner or run: python -I stalker_slot.py cleanup (only works with no live lease)."; exit 4 }

# Don't touch the owner's own game session (any xrEngine/launcher that is not registered to a slot lease).
$waited = 0
while ($true) {
    $st = (& python -I $slotPy strays) -join ""
    if ($st -match "STRAYS none") { break }
    if ($waited -ge $BusyWait) {
        Release-Slot
        "BUSY: xrEngine or the launcher is already running ($st). Not launching; wait and retry later."
        exit 2
    }
    Start-Sleep 5; $waited += 5
}
try {

$port = 5450 + 10 * $slot   # per-slot server port: 5450 / 5460 / 5470
if ($Listen) {
    $sfx = if ($slot -gt 0) { "_s$slot" } else { "" }
    $app = Join-Path $Game "_appdata_csboot$sfx"
    New-Item -ItemType Directory -Force (Join-Path $app "logs") | Out-Null
    $fs = Join-Path $Game "fsgame_csboot$sfx.ltx"
    if (-not (Test-Path $fs)) {
        (Get-Content (Join-Path $Game "fsgame.ltx") -Raw).Replace("_appdata_\", "_appdata_csboot$sfx\") | Set-Content -NoNewline -Encoding ascii $fs
    }
    $ul = Join-Path $app "user.ltx"
    if (-not (Test-Path $ul)) {
        $u = @(Get-Content (Join-Path $Game "_appdata_\user.ltx") | Where-Object { $_ -notmatch "^(vid_mode|vid_window_mode|rs_always_active|snd_volume_eff|snd_volume_music|rs_stats) " })
        $u += "vid_mode 800x600", "vid_window_mode st_opt_windowed", "rs_always_active on", "snd_volume_eff 0.", "snd_volume_music 0.", "rs_stats off"
        $u | Set-Content -Encoding ascii $ul
    }
    $log = Join-Path $app "logs\xray_$env:USERNAME.log"
    Remove-Item $log -ErrorAction SilentlyContinue
    $argLine = "-noprefetch -nointro -fsltx ..\fsgame_csboot$sfx.ltx -addon=$Addon $ExtraArgs -start server($Map/coop/hname=dev/maxplayers=4/public=0/minplayers=1/portsv=$port) client(localhost/name=csbot)"
    $exe = Join-Path $Game "bin\xrEngine.exe"
} else {
    $sfx = if ($slot -gt 0) { "_s$slot" } else { "" }
    $fsn = "fsgame_s$sfx.ltx"
    if ($slot -gt 0 -and -not (Test-Path (Join-Path $Game $fsn))) {
        (Get-Content (Join-Path $Game "fsgame_s.ltx") -Raw).Replace("_appdata_server\", "_appdata_server$sfx\") | Set-Content -NoNewline -Encoding ascii (Join-Path $Game $fsn)
    }
    New-Item -ItemType Directory -Force (Join-Path $Game "_appdata_server$sfx\logs") | Out-Null
    $log = Join-Path $Game "_appdata_server$sfx\logs\xray_$env:USERNAME.log"
    Remove-Item $log -ErrorAction SilentlyContinue
    $argLine = "-i -noprefetch -fsltx ..\$fsn -addon=$Addon $ExtraArgs -start server($Map/coop/hname=dev/maxplayers=4/public=0/minplayers=1/portsv=$port) client(localhost)"
    $exe = Join-Path $Game "bin\dedicated\xrEngine.exe"
}
$p = Start-Process $exe -ArgumentList $argLine -WorkingDirectory (Join-Path $Game "bin") -PassThru
if ($haveSlot) { & python -I $slotPy register-pid --owner $Owner --pid $p.Id | Out-Null }

$result = "TIMEOUT"; $connectedAt = $null; $lastLen = 0; $stall = 0
for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
    Start-Sleep 1
    $t = Get-Content $log -Raw -ErrorAction SilentlyContinue
    if ($t -match "FATAL ERROR") { $result = "CRASH"; break }
    if ($p.HasExited) { $result = "EXITED code $($p.ExitCode)"; break }
    if ($t -match "Connection finished" -and $null -eq $connectedAt) { $connectedAt = $i }
    if ($null -ne $connectedAt -and $i -ge $connectedAt + $SoakSeconds) { $result = "OK"; break }
    # No log at all after 20 s usually means an engine error box is open: stop instead of leaving it on screen.
    $len = if ($t) { $t.Length } else { 0 }
    if ($len -eq $lastLen) { $stall++ } else { $stall = 0; $lastLen = $len }
    if ($len -eq 0 -and $i -ge 20) { $result = "NO LOG (error dialog?)"; break }
}
Start-Sleep 2
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Start-Sleep 2 }

if ($LogCopy -ne "" -and (Test-Path $log)) { Copy-Item $log $LogCopy -Force }
"RESULT: $result after $i s (map $Map, addon $Addon, slot $slot, port $port, log $log)"
if (Test-Path $log) {
    Select-String -Path $log -Pattern "FATAL ERROR|\[error\]Description|\[error\]Arguments|Connection finished|New game is successfully created" | Select-Object -First 12 | ForEach-Object { "  " + $_.Line }
}
} finally {
    Release-Slot
}
