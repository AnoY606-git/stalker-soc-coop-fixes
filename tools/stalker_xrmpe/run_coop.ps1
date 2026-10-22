# Hands-free TWO-CLIENT co-op test for Shadow of COOP on xrMPE 0.9.  See "run_coop how-to" in automatedqa.md (STALKER part).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_coop.ps1 -Map coop_l01_escape -Owner mylane `
#       [-Hooks C:\path\my_hooks.lua[,more.lua]] [-Scenario flag_sync] [-SoakSeconds 60] [-ExpectMismatch] [-Mode listen|dedicated]
#
# Up to 6 runs may be in parallel (one slot each); the slot index picks the server port (5461 + 10 * slot).
# What it does (all inside one game slot, see stalker_slot.py):
#   1. builds a uniquely named TEST addon = copy of coop.addon + test db (qa_harness.lua + your -Hooks appended to the shipped
#      scripts\xr_conditions.dscript and scripts\game_cl.script; -Addon <existing test addon> skips the build and uses it as is),
#   2. starts client 1 = listen server + local player "qaA" and client 2 = joined client "qaB" (windowed 800x600, muted, own
#      fsgame copy, own _appdata_qa_* folder: own user.ltx, logs, screenshots; the owner's _appdata_ is never touched),
#   3. both bots spawn hands-free; each client writes qa_state.log (shared-state snapshots) and qa_assert.log into its own logs,
#   4. run_coop polls qa_compare.py until shared state is equal (or the timeout), takes an engine screenshot on each client,
#   5. copies every log + screenshot into -ResultDir, kills ONLY the pids it started, deletes the test addon, fsgame copies and
#      appdata folders, releases the slot.  Prints "RESULT: PASS|FAIL ..." and exits 0 / 1 (2 = BUSY, 3 = setup problem).
# -ExpectMismatch inverts the compare (for a mutation twin: the run PASSES only if the comparer reports a shared-state mismatch).
param(
    [Parameter(Mandatory = $true)][string]$Map,
    [string]$Owner = "",
    [string]$Addon = "",                    # existing test addon in <Game>\addons (must contain qa_harness.lua); "" = build one
    [string[]]$Hooks = @(),                 # extra Lua files appended after the harness (assertion hooks), full paths
    [string]$Scenario = "shared_equal",     # shared_equal | flag_sync | mutate_flag_b | <your own, read via qa.cfg.scenario>
    [string[]]$Cfg = @(),                   # extra "key=value" lines for qa.cfg (both clients)
    [int]$Clients = 2,
    [ValidateSet("listen", "dedicated")][string]$Mode = "dedicated",   # dedicated = server + N real clients (works); listen: 2nd client collapses into the first (same-PC digest)
    [int]$SoakSeconds = 40,                 # how long to keep both players alive after both spawned
    [int]$CompareTimeout = 90,              # poll window for "shared state equal"
    [int]$TimeoutSeconds = 420,             # whole-run cap for boot + spawn
    [string]$ExtraArgs = "-use_all_spawn",
    [int]$Port = 5461,
    [string[]]$JoinHosts = @(),   # source/target IP per joining client (the server dedupes clients by IP: see how-to)
    [string]$ResultDir = "",
    [switch]$ExpectMismatch,
    [switch]$KeepAddon,
    [double]$MinFreeGb = 6,                  # qa_build refuses to build below this much free disk (lane builds only add about 60 MB; lower it when other agents fill the disk)
    [switch]$NoLane,                        # do not use the permanent lane copy (addons\qalane<slot>.addon); build a throwaway 4.2 GB copy instead
    [int]$SlotWait = 1800,
    [int]$BusyWait = 600,
    [string]$Game = "C:\X-Ray Multiplayer Extension\game",
    [string[]]$InplaceDir = @(),            # folders (gamedata\ layout) whose files overwrite same-named UNCOMPRESSED entries of the addon copy in place (qa_build --inplace-dir; keeps the addon under 4 GB)
    [string[]]$DbFile = @(),                # finished .db files (the real release db) appended to the test addon like install.ps1 does (qa_build --db-file)
    [string[]]$ExtraDir = @(),              # folders that map to gamedata\ (patch files) packed into the test db via qa_build --extra-dir
    [string[]]$AppendSpec = @(),            # advanced: raw qa_build.py --append specs (replaces the default harness targets)
    [string]$Save = ""                      # opt-in: start from live\saves\<name>.scop (see live\README.md); adds live\live_hooks.lua + cfg live_save=1. Default "" = unchanged behaviour.
)
$ErrorActionPreference = "Continue"
if ($JoinHosts.Count -eq 0) {
    # The server treats two clients from the SAME IP as one player (the 2nd gets the 1st's identity), so joiners connect through this PC's LAN IP.
    $lan = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notmatch "^(127\.|169\.254\.)" -and $_.PrefixOrigin -ne "WellKnown" } | Sort-Object { if ($_.PrefixOrigin -eq "Dhcp") { 0 } else { 1 } } | ForEach-Object { $_.IPAddress })
    $JoinHosts = @($lan | Select-Object -First 1) * 3
}
$here = $PSScriptRoot
$slotPy = Join-Path $here "stalker_slot.py"
if ($Owner -eq "") { $Owner = "rc$PID" }
$Owner = $Owner -replace "[^A-Za-z0-9]", ""
$stamp = Get-Date -Format "yyMMdd_HHmmss"
$tag = "$Owner$stamp"
if ($ResultDir -eq "") { $ResultDir = Join-Path $here "results\$tag" }
New-Item -ItemType Directory -Force $ResultDir | Out-Null
$py = (Get-Command python -ErrorAction Stop).Source
function Say($m) { $l = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $m; Write-Host $l; Add-Content -Path (Join-Path $ResultDir "run.log") -Value $l }

# ---- 0. slot + owner check
$ttl = $TimeoutSeconds + $SoakSeconds + $CompareTimeout + 600
$r = & $py -I $slotPy acquire --owner $Owner --ttl $ttl --wait $SlotWait --ownerpid $PID 2>&1
Say "SLOT: $r"
if ($LASTEXITCODE -ne 0) { Say "BUSY: game slot held by another agent. Not launching."; exit 2 }
$haveSlot = $true
if ("$r" -match "SLOTS (\d+)") { $Port = $Port + 10 * [int]$Matches[1] }   # per-slot server port: 5461 / 5471 / 5481
$started = @()          # pids we started
$builtAddon = ""
$cleanup = @()          # files/folders to delete
$exit = 3
try {
    $waited = 0
    while ($true) {
        $st = (& $py -I $slotPy strays) -join ""
        if ($st -match "STRAYS none") { break }
        if ($waited -ge $BusyWait) { Say "BUSY: the owner's own xrEngine/launcher is running ($st). Not launching."; $exit = 2; throw "busy" }
        Start-Sleep 5; $waited += 5
    }

    # ---- 1. test addon
    if ($Addon -eq "") {
        $Addon = "qa_$tag.addon"
        $spec = $AppendSpec
        if ($spec.Count -eq 0) {
            $lua = (Join-Path $here "lua\qa_harness.lua")
            if ($Save -ne "") { $lh = (Join-Path $here "live\live_hooks.lua"); if ($Hooks -notcontains $lh) { $lua = $lua + "," + $lh } }   # -Save: live hooks first (save-mode respawn)
            if ($Hooks.Count -gt 0) { $lua = $lua + "," + ($Hooks -join ",") }
            $spec = @("scripts/xr_conditions.dscript=$lua", "scripts/game_cl.script=$lua", "scripts/bind_stalker.script=$lua")
        }
        $bargs = @("-I", (Join-Path $here "qa_build.py"), "--out", $Addon, "--owner", $Owner, "--game", $Game, "--min-free-gb", "$MinFreeGb")
        foreach ($s in $spec) { $bargs += @("--append", $s) }
        foreach ($d in $ExtraDir) { $bargs += @("--extra-dir", $d) }
        foreach ($d in $DbFile) { $bargs += @("--db-file", $d) }
        foreach ($d in $InplaceDir) { $bargs += @("--inplace-dir", $d) }
        # Lane mode (default for slots 0 to 5; needs about 24 GB for the 6 copies): a PERMANENT copy of coop.addon per lane (addons\qalane<slot>.addon, owner
        # approved 2026-10-19) is reused; qa_build only cuts the file back to coop.addon's tar data and appends the new test db
        # (seconds instead of a 4.2 GB copy). The lane copy is re-made automatically when coop.addon changes. -NoLane = old way.
        # (FastPatch via game\patches or a loose gamedata folder was tried and does NOT work: the addon is mounted last.)
        $slotIdx = -1
        if ("$r" -match "SLOTS (\d+)") { $slotIdx = [int]$Matches[1] }
        $builtAddon = Join-Path $Game "addons\$Addon"
        if (-not $NoLane -and $slotIdx -ge 0 -and $slotIdx -lt 6) {
            $Addon = "qalane$slotIdx.addon"
            $bargs[3] = $Addon
            $bargs += @("--lane", "$slotIdx")
            Say "lane mode: $Addon (only the test db is replaced)"
            $out = & $py @bargs 2>&1
            $out | ForEach-Object { Say "  build: $_" }
            if (-not (($out -join " ") -match "BUILD_OK")) { Say "BUILD FAILED"; throw "build" }
            $builtAddon = ""
        } else {
        Say "building test addon $Addon ..."
        $gw = 0
        while ($true) {
            $g = (& $py -I $slotPy guard --owner $Owner) -join " "
            if ($g -match "GUARD OK") { break }
            if ($gw -ge 900) { Say "GUARD never cleared: $g"; break }
            if ($gw % 60 -eq 0) { Say "waiting for other test addons to be deleted: $g" }
            Start-Sleep 10; $gw += 10
        }
        $out = & $py @bargs 2>&1
        $out | ForEach-Object { Say "  build: $_" }
        if (-not (Test-Path $builtAddon)) { Say "BUILD FAILED"; throw "build" }
        if (-not $KeepAddon) { $cleanup += $builtAddon }
        & $py -I $slotPy register-file --owner $Owner --path $builtAddon | Out-Null
        }
    } elseif (-not (Test-Path (Join-Path $Game "addons\$Addon"))) { Say "NO ADDON: $Addon"; throw "noaddon" }

    # ---- 2. per-client profile
    $bin = Join-Path $Game "bin"
    $cl = @()
    $names = @("qaA", "qaB", "qaC", "qaD")
    function New-Profile($role, $fsSrc, $appMarker, $pname = "") {
        $app = Join-Path $Game "_appdata_qa_${tag}_$role"
        $fs = Join-Path $Game "fsgame_qa_${tag}_$role.ltx"
        New-Item -ItemType Directory -Force (Join-Path $app "logs") | Out-Null
        New-Item -ItemType Directory -Force (Join-Path $app "screenshots") | Out-Null
        $fsText = (Get-Content (Join-Path $Game $fsSrc) -Raw).Replace($appMarker, "_appdata_qa_${tag}_$role\")
        $fsText | Set-Content -NoNewline -Encoding ascii $fs
        $u = @(Get-Content (Join-Path $Game "_appdata_\user.ltx") | Where-Object { $_ -notmatch "^(vid_mode|vid_window_mode|rs_always_active|snd_volume_eff|snd_volume_music|rs_stats|r_fps|rs_vsync|g_god|sv_rename_mode) " })
        $u += "vid_mode 800x600", "vid_window_mode st_opt_windowed", "rs_always_active on", "snd_volume_eff 0.", "snd_volume_music 0.", "rs_stats off", "sv_rename_mode on"
        $u | Set-Content -Encoding ascii (Join-Path $app "user.ltx")
        $cfgLines = @("role=$role", "scenario=$Scenario", "clients=$Clients", "mode=$Mode", "result_tag=$tag", "player=$pname") + $(if ($Save -ne "") { @("live_save=1", "live_keep_snap=1") } else { @() }) + $Cfg
        $cfgLines | Set-Content -Encoding ascii (Join-Path $app "logs\qa_role.txt")
        $script:cleanup += $app
        $script:cleanup += $fs
        & $py -I $slotPy register-file --owner $Owner --path $app | Out-Null
        & $py -I $slotPy register-file --owner $Owner --path $fs | Out-Null
        return [pscustomobject]@{ Role = $role; Name = ""; App = $app; Fs = $fs; Logs = (Join-Path $app "logs"); Shots = (Join-Path $app "screenshots"); Pid = 0; XLog = (Join-Path $app "logs\xray_$env:USERNAME.log") }
    }
    for ($i = 0; $i -lt $Clients; $i++) {
        $c = New-Profile ([string][char](65 + $i)) "fsgame.ltx" "_appdata_\" $names[$i]
        $c.Name = $names[$i]
        $cl += $c
    }
    $srv = $null
    if ($Mode -eq "dedicated") { $srv = New-Profile "S" "fsgame_s.ltx" "_appdata_server\"; $srv.Name = "server" }
    if ($Save -ne "") {
        # opt-in: apply live\saves\<Save>.scop as <app>\savedgames\<addon>\<Map>.scop of the server role (S, or A in listen mode)
        $sv = Join-Path $here "live\saves\$Save.scop"
        $svm = Join-Path $here "live\saves\$Save.json"
        if (-not (Test-Path $sv) -or -not (Test-Path $svm)) { Say "NO SAVE: $sv"; throw "nosave" }
        $svlevel = (Get-Content $svm -Raw | ConvertFrom-Json).level
        if ($svlevel -ne $Map) { Say "save '$Save' is for $svlevel but -Map is $Map"; throw "savemap" }
        $holder = if ($srv) { $srv } else { $cl[0] }
        $sd = Join-Path $holder.App ("savedgames\" + [IO.Path]::GetFileNameWithoutExtension($Addon))
        New-Item -ItemType Directory -Force $sd | Out-Null
        Copy-Item $sv (Join-Path $sd "$Map.scop") -Force
        Say "save '$Save' applied to $sd"
    }

    function Start-Game($c, $startArg, $exeRel = "xrEngine.exe", $pre = "") {
        $a = "$pre-noprefetch -nointro -fsltx ..\$(Split-Path $c.Fs -Leaf) -addon=$Addon $ExtraArgs -start $startArg"
        $p = Start-Process (Join-Path $bin $exeRel) -ArgumentList $a -WorkingDirectory $bin -PassThru
        $c.Pid = $p.Id
        $script:started += $p.Id
        & $py -I $slotPy register-pid --owner $Owner --pid $p.Id | Out-Null
        Say "started client $($c.Role) ($($c.Name)) pid $($p.Id): $startArg"
    }
    function Get-Text($path) { if (Test-Path $path) { try { Get-Content $path -Raw -ErrorAction Stop } catch { "" } } else { "" } }
    function Alive($c) { return [bool](Get-Process -Id $c.Pid -ErrorAction SilentlyContinue) }
    function Crashed($c) {
        $t = Get-Text $c.XLog
        if ($t -match "FATAL ERROR") { return ("CRASH: " + ([regex]::Match($t, "\[error\]Arguments\s*:\s*(.*)")).Groups[1].Value) }
        if ($c.Pid -ne 0 -and -not (Alive $c)) { return "EXITED" }
        return $null
    }
    function Spawned($c) { return ((Get-Text (Join-Path $c.Logs "qa_state.log")) -match '"spawned":true') }
    function Cmd($c, $text) { Add-Content -Path (Join-Path $c.Logs "qa_cmd.txt") -Value $text -Encoding ascii }

    # ---- 3. launch
    $A = $cl[0]
    $server = "server($Map/coop/hname=qa$Owner/maxplayers=4/public=0/minplayers=1/portsv=$Port)"
    $failure = $null
    $t0 = Get-Date
    if ($Mode -eq "listen") {
        Start-Game $A "$server client(localhost/name=$($A.Name))"
        # wait for A (listen server + player) to spawn, then join the others one by one
        for ($k = 1; $k -lt $cl.Count; $k++) {
            while (-not (Spawned $A) -and (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSeconds)) {
                $f = Crashed $A; if ($f) { $failure = "client A $f"; break }
                Start-Sleep 2
            }
            if ($failure -or -not (Spawned $A)) { if (-not $failure) { $failure = "client A never spawned (timeout)" }; break }
            Say "client A spawned after $([int]((Get-Date) - $t0).TotalSeconds) s; joining client $($cl[$k].Role)"
            Start-Game $cl[$k] "client($($JoinHosts[$k - 1])/name=$($cl[$k].Name)/port=$Port)"
        }
    } else {
        # dedicated server (bin\dedicated\xrEngine.exe, no window) + N real clients
        Start-Game $srv "$server client(localhost)" "dedicated\xrEngine.exe" "-i "
        while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSeconds) {
            $f = Crashed $srv; if ($f) { $failure = "dedicated server $f"; break }
            if ((Get-Text $srv.XLog) -match "Connection finished") { break }
            Start-Sleep 2
        }
        if (-not $failure) {
            Say "dedicated server up after $([int]((Get-Date) - $t0).TotalSeconds) s; joining clients"
            for ($k = 0; $k -lt $cl.Count; $k++) { $c = $cl[$k]; Start-Game $c "client($($JoinHosts[$k])/name=$($c.Name)/port=$Port)"; Start-Sleep 5 }
        }
    }
    if (-not $failure) {
        while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSeconds) {
            foreach ($c in (@($cl) + @($srv))) { if ($c) { $f = Crashed $c; if ($f) { $failure = "client $($c.Role) $f" } } }
            if ($failure) { break }
            if (($cl | Where-Object { -not (Spawned $_) }).Count -eq 0) { break }
            Start-Sleep 2
        }
        if (-not $failure -and ($cl | Where-Object { -not (Spawned $_) }).Count -gt 0) { $failure = "not all clients spawned: " + (($cl | Where-Object { -not (Spawned $_) } | ForEach-Object { $_.Role }) -join ",") }
    }

    # ---- 4. soak + compare (poll, never check once)
    $verdict = ""
    if (-not $failure) {
        Say "all $($cl.Count) clients spawned after $([int]((Get-Date) - $t0).TotalSeconds) s; soaking $SoakSeconds s"
        $end = (Get-Date).AddSeconds($SoakSeconds)
        while ((Get-Date) -lt $end) {
            foreach ($c in (@($cl) + @($srv))) { if ($c) { $f = Crashed $c; if ($f) { $failure = "client $($c.Role) $f during soak" } } }
            if ($failure) { break }
            Start-Sleep 2
        }
    }
    if (-not $failure) {
        foreach ($c in $cl) { Cmd $c "screenshot"; Cmd $c "console screenshot qashot_$($c.Role)"; Cmd $c "console screenshot jpg" }
        $cmp = @("-I", (Join-Path $here "qa_compare.py"), "--timeout", $CompareTimeout, "--out", (Join-Path $ResultDir "compare.json"))
        foreach ($c in $cl) { $cmp += @("--log", "$($c.Role)=$(Join-Path $c.Logs 'qa_state.log')") }
        if ($ExpectMismatch) { $cmp += "--expect-mismatch" }
        foreach ($x in $Cfg) { if ($x -match "^require_flag=(.*)$") { $cmp += @("--require-flag", $Matches[1]) } }
        Say "comparing shared state (poll up to $CompareTimeout s) ..."
        $co = & $py @cmp 2>&1
        $co | ForEach-Object { Say "  cmp: $_" }
        $verdict = if ($LASTEXITCODE -eq 0) { "PASS" } else { "FAIL" }
        # assertion hooks written by agents' own Lua (qa.assert -> qa_assert.log on each client)
        $asserts = @()
        foreach ($c in $cl) { $asserts += (Get-Text (Join-Path $c.Logs "qa_assert.log")) -split "`r?`n" | Where-Object { $_ -match "^(PASS|FAIL) " } | ForEach-Object { "$($c.Role): $_" } }
        foreach ($l in $asserts) { Say "  assert $l" }
        if (($asserts | Where-Object { $_ -match ": FAIL " }).Count -gt 0) { $verdict = "FAIL" }
        Start-Sleep 3   # let the screenshot land
    }

    # ---- 5. collect
    if ($failure) {
        foreach ($c in $cl) { if (Spawned $c) { Cmd $c "screenshot"; Cmd $c "console screenshot qashot_$($c.Role)"; Cmd $c "console screenshot jpg" } }
        Start-Sleep 6
    }
    foreach ($c in (@($cl) + @($srv))) {
        if (-not $c) { continue }
        $d = Join-Path $ResultDir "client_$($c.Role)"
        New-Item -ItemType Directory -Force $d | Out-Null
        Copy-Item (Join-Path $c.Logs "*") $d -Force -ErrorAction SilentlyContinue
        if (Test-Path $c.Shots) { New-Item -ItemType Directory -Force (Join-Path $d "screenshots") | Out-Null; Copy-Item (Join-Path $c.Shots "*") (Join-Path $d "screenshots") -Force -ErrorAction SilentlyContinue }
    }
    if ($failure) { $verdict = "FAIL"; Say "FAILURE: $failure" }
    $shots = @(Get-ChildItem -Path $ResultDir -Recurse -Include *.png, *.jpg, *.jpeg -ErrorAction SilentlyContinue).Count
    Say "RESULT: $verdict (map $Map, scenario $Scenario, clients $($cl.Count), screenshots $shots, results in $ResultDir)"
    $exit = if ($verdict -eq "PASS") { 0 } else { 1 }
} catch {
    if ($exit -eq 3) { Say "SETUP ERROR: $_" }
} finally {
    foreach ($p in $started) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    if ($started.Count -gt 0) { Start-Sleep 3 }
    # HARD RULE: the 4.2 GB test addon is deleted BEFORE the slot is released
    for ($try = 0; $try -lt 15; $try++) {
        foreach ($x in $cleanup) { Remove-Item $x -Recurse -Force -ErrorAction SilentlyContinue }
        if (-not ($cleanup | Where-Object { Test-Path $_ })) { break }
        Start-Sleep 2
    }
    if ($builtAddon -ne "" -and (Test-Path $builtAddon) -and -not $KeepAddon) { Say "WARNING: could not delete $builtAddon; run: python -I stalker_slot.py cleanup" }
    if ($haveSlot) { & $py -I $slotPy release --owner $Owner | Out-Null }
}
exit $exit
