# LIVE Shadow of COOP session: boots a harness slot and KEEPS IT RUNNING (no soak, no timeout) so you can send Lua to it with lua.ps1.
# Full how-to: live\README.md.  Adds files only; run_coop.ps1 / stalker_slot.py are used as they are.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File start_live.ps1 -Map coop_l01_escape [-Mode dedicated|listen] [-Clients 1]
#       [-ExtraDir <stage>\gamedata] [-Save cordon_start] [-Name live] [-Hooks my.lua] [-Cfg k=v]
#   (-Save <name> applies live\saves\<name>.scop into the session's server appdata before boot; -Map is then optional)
#
# What it does: takes ONE game slot (long lease, registered pids), builds the lane addon (qa_build.py --lane: the harness + live_hooks.lua are
# appended to the shipped scripts, seconds), makes own appdata + fsgame per role, applies the save, starts server (dedicated) and N clients,
# waits until every role answers (live_ready.txt) and the players spawned, writes live\state\<Name>.json and EXITS (game keeps running).
# Stop with stop_live.ps1.  Exit codes: 0 ok, 1 failed to boot, 2 BUSY (slot / owner's own game), 3 setup problem.
param(
    [string]$Map = "",
    [ValidateSet("listen", "dedicated")][string]$Mode = "dedicated",
    [int]$Clients = 1,
    [string[]]$ExtraDir = @(),              # patch folders (gamedata\ layout) packed into the test db
    [string]$Save = "",                     # name of a save in live\saves
    [string]$Name = "live",                 # session name (state file); one session per name
    [string]$Owner = "",
    [string[]]$Hooks = @(),                 # more Lua files appended after live_hooks.lua (full paths)
    [string[]]$Cfg = @(),
    [string[]]$DbFile = @(),                # finished release .db files appended to the lane addon like install.ps1 does (qa_build --db-file); use this instead of -ExtraDir for the compressed release db
    [string]$PlayerName = "",               # name of client A (default qaA); the name is stored inside saves
    [string]$ExtraArgs = "-use_all_spawn",
    [int]$Port = 5461,
    [int]$TimeoutSeconds = 600,
    [double]$MinFreeGb = 4,                    # lane builds add ~60 MB; coordinator lowered the floor from 10 to 4 GB on 2026-10-20
    [int]$SpawnGrace = 120,                 # -Save only: accept a world that is loaded and answering although a client never became a player (see below)
    [int]$SlotWait = 1800,
    [int]$BusyWait = 600,
    [int]$LeaseHours = 12,
    [int]$ForceLane = -1,                   # use qalane<N>.addon whatever slot index the lease gives (a dead xrEngine can keep a lane file locked until reboot)
    [string]$Game = "C:\X-Ray Multiplayer Extension\game"
)
$ErrorActionPreference = "Continue"
$Cfg = @($Cfg | ForEach-Object { $_ -split "," } | Where-Object { $_ })   # -File passes "a=1,b=2" as one string
$here = $PSScriptRoot
$tools = Split-Path $here -Parent
$slotPy = Join-Path $tools "stalker_slot.py"
$py = (Get-Command python -ErrorAction Stop).Source
$stateDir = Join-Path $here "state"
New-Item -ItemType Directory -Force $stateDir | Out-Null
$stateFile = Join-Path $stateDir "$Name.json"
# atomic lock: only the run that created the state file may ever delete it (a failed second start must not remove a running session's file)
try { $lockFs = [IO.File]::Open($stateFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read); $lockFs.Close() }
catch { Write-Host "A live session named '$Name' already exists or is booting ($stateFile). Run stop_live.ps1 -Name $Name first, or use -Name <other>."; exit 3 }
[IO.File]::WriteAllText($stateFile, '{"booting":true}')
if ($Owner -eq "") { $Owner = ("live" + $Name) }
$Owner = $Owner -replace "[^A-Za-z0-9]", ""
$stamp = Get-Date -Format "yyMMdd_HHmmss"
$tag = "lv$Owner$stamp"
$T0 = Get-Date
function Say($m) { Write-Host ("[{0:HH:mm:ss} +{1,5:N1}s] {2}" -f (Get-Date), ((Get-Date) - $T0).TotalSeconds, $m) }

# ---- save + map
$saveMeta = $null
$savePath = ""
if ($Save -ne "") {
    $savePath = Join-Path $here "saves\$Save.scop"
    $metaPath = Join-Path $here "saves\$Save.json"
    if (-not (Test-Path $savePath) -or -not (Test-Path $metaPath)) { Say "NO SAVE: $savePath (or its .json). Saves: $((Get-ChildItem (Join-Path $here 'saves') -Filter *.scop -ErrorAction SilentlyContinue | ForEach-Object { $_.BaseName }) -join ', ')"; Remove-Item $stateFile -Force -ErrorAction SilentlyContinue; exit 3 }
    $saveMeta = Get-Content $metaPath -Raw | ConvertFrom-Json
    if ($Map -eq "") { $Map = $saveMeta.level }
    elseif ($Map -ne $saveMeta.level) { Say "save '$Save' was made on $($saveMeta.level) but -Map is $Map. The server loads savedgames\<addon>\<map>.scop, so the map must match."; Remove-Item $stateFile -Force -ErrorAction SilentlyContinue; exit 3 }
}
if ($Map -eq "") { Say "need -Map or -Save"; Remove-Item $stateFile -Force -ErrorAction SilentlyContinue; exit 3 }

# ---- disk
$freeGb = (Get-PSDrive -Name C).Free / 1GB
if ($freeGb -lt $MinFreeGb) { Say ("LOW DISK: {0:N1} GB free on C:, need {1} GB. Not launching." -f $freeGb, $MinFreeGb); Remove-Item $stateFile -Force -ErrorAction SilentlyContinue; exit 3 }
if ($freeGb -lt 10 -and $freeGb -ge $MinFreeGb) { Say ("WARNING: only {0:N1} GB free on C: (house rule: keep 10 GB). A session costs tens of MB; -MinFreeGb 10 makes this a hard stop." -f $freeGb) }

# ---- slot (long lease, no ownerpid: the lease lives while a registered game pid lives, see stalker_slot.py _live)
$ttl = $LeaseHours * 3600
$r = & $py -I $slotPy acquire --owner $Owner --ttl $ttl --wait $SlotWait 2>&1
Say "SLOT: $r"
if ($LASTEXITCODE -ne 0) { Say "BUSY: no free game slot. Not launching."; Remove-Item $stateFile -Force -ErrorAction SilentlyContinue; exit 2 }
$slotIdx = -1
if ("$r" -match "SLOTS (\d+)") { $slotIdx = [int]$Matches[1]; $Port = $Port + 10 * $slotIdx }
if ($ForceLane -ge 0) { $Port = $Port + 10 * ($ForceLane - [math]::Max($slotIdx, 0)); $slotIdx = $ForceLane; Say "lane forced to $ForceLane" }
$started = @(); $cleanup = @(); $exit = 3; $ok = $false
try {
    $waited = 0
    while ($true) {
        $st = (& $py -I $slotPy strays) -join ""
        if ($st -match "STRAYS none") { break }
        if ($waited -ge $BusyWait) { Say "BUSY: the owner's own xrEngine/launcher is running ($st). Not launching."; $exit = 2; throw "busy" }
        Start-Sleep 5; $waited += 5
    }
    # xrEngine count guard: other agents are testing on this PC
    $waited = 0
    while (@(Get-Process xrEngine -ErrorAction SilentlyContinue).Count -gt 6) {
        if ($waited -ge $BusyWait) { Say "more than 6 xrEngine.exe running; not launching."; $exit = 2; throw "busy" }
        if ($waited % 30 -eq 0) { Say "waiting: more than 6 xrEngine.exe running" }
        Start-Sleep 5; $waited += 5
    }
    if ($slotIdx -lt 0 -or $slotIdx -gt 5) { Say "slot index $slotIdx has no lane copy"; throw "slot" }

    # ---- 1. lane addon with harness + live hooks
    $Addon = "qalane$slotIdx.addon"
    $lua = (Join-Path $tools "lua\qa_harness.lua") + "," + (Join-Path $here "live_hooks.lua")
    if ($Hooks.Count -gt 0) { $lua = $lua + "," + ($Hooks -join ",") }
    $spec = @("scripts/xr_conditions.dscript=$lua", "scripts/game_cl.script=$lua", "scripts/bind_stalker.script=$lua")
    $bargs = @("-I", (Join-Path $tools "qa_build.py"), "--out", $Addon, "--owner", $Owner, "--game", $Game, "--min-free-gb", "$MinFreeGb", "--lane", "$slotIdx")
    foreach ($s in $spec) { $bargs += @("--append", $s) }
    foreach ($d in $ExtraDir) { $bargs += @("--extra-dir", $d) }
    foreach ($d in $DbFile) { $bargs += @("--db-file", $d) }
    $out = & $py @bargs 2>&1
    $out | ForEach-Object { Say "  build: $_" }
    if (-not (($out -join " ") -match "BUILD_OK")) { Say "BUILD FAILED"; throw "build" }

    # ---- 2. profiles
    $bin = Join-Path $Game "bin"
    $reloadLines = @(); foreach ($d in $ExtraDir) { $reloadLines += "reload_dir=" + (Join-Path $d "scripts") }
    function New-Profile($role, $fsSrc, $appMarker, $pname) {
        $app = Join-Path $Game "_appdata_qa_${tag}_$role"
        $fs = Join-Path $Game "fsgame_qa_${tag}_$role.ltx"
        New-Item -ItemType Directory -Force (Join-Path $app "logs") | Out-Null
        New-Item -ItemType Directory -Force (Join-Path $app "screenshots") | Out-Null
        $fsText = (Get-Content (Join-Path $Game $fsSrc) -Raw).Replace($appMarker, "_appdata_qa_${tag}_$role\")
        $fsText | Set-Content -NoNewline -Encoding ascii $fs
        $u = @(Get-Content (Join-Path $Game "_appdata_\user.ltx") | Where-Object { $_ -notmatch "^(vid_mode|vid_window_mode|rs_always_active|snd_volume_eff|snd_volume_music|rs_stats|r_fps|rs_vsync|g_god|sv_rename_mode) " })
        $u += "vid_mode 800x600", "vid_window_mode st_opt_windowed", "rs_always_active on", "snd_volume_eff 0.", "snd_volume_music 0.", "rs_stats off", "sv_rename_mode on"
        $u | Set-Content -Encoding ascii (Join-Path $app "user.ltx")
        $cfgLines = @("role=$role", "scenario=live", "clients=$Clients", "mode=$Mode", "result_tag=$tag", "player=$pname") + $reloadLines + $(if ($Save -ne "") { @("live_save=1") } else { @() }) + $Cfg
        $cfgLines | Set-Content -Encoding ascii (Join-Path $app "logs\qa_role.txt")
        $script:cleanup += $app; $script:cleanup += $fs
        & $py -I $slotPy register-file --owner $Owner --path $app | Out-Null
        & $py -I $slotPy register-file --owner $Owner --path $fs | Out-Null
        return [pscustomobject]@{ Role = $role; Name = $pname; App = $app; Fs = $fs; Logs = (Join-Path $app "logs"); Shots = (Join-Path $app "screenshots"); Pid = 0; XLog = (Join-Path $app "logs\xray_$env:USERNAME.log") }
    }
    $names = @("qaA", "qaB", "qaC", "qaD")
    if ($PlayerName -ne "") { $names[0] = $PlayerName }
    $cl = @()
    for ($i = 0; $i -lt $Clients; $i++) { $cl += (New-Profile ([string][char](65 + $i)) "fsgame.ltx" "_appdata_\" $names[$i]) }
    $srv = $null
    if ($Mode -eq "dedicated") { $srv = New-Profile "S" "fsgame_s.ltx" "_appdata_server\" "server" }
    $roles = @(); foreach ($c in (@($srv) + @($cl))) { if ($c) { $roles += $c } }

    # ---- 3. save into the server's appdata (dedicated: S, listen: A)
    if ($savePath -ne "") {
        $holder = if ($srv) { $srv } else { $cl[0] }
        $sd = Join-Path $holder.App "savedgames\qalane$slotIdx"
        New-Item -ItemType Directory -Force $sd | Out-Null
        Copy-Item $savePath (Join-Path $sd "$Map.scop") -Force
        Say "save '$Save' applied: $sd\$Map.scop ($((Get-Item $savePath).Length) bytes, made with stage '$($saveMeta.stage)')"
    }

    function Get-Text($path) { if (Test-Path $path) { try { Get-Content $path -Raw -ErrorAction Stop } catch { "" } } else { "" } }
    function Alive($c) { return [bool](Get-Process -Id $c.Pid -ErrorAction SilentlyContinue) }
    function Crashed($c) {
        $t = Get-Text $c.XLog
        if ($t -match "FATAL ERROR") { return ("CRASH: " + ([regex]::Match($t, "\[error\]Arguments\s*:\s*(.*)")).Groups[1].Value) }
        if ($c.Pid -ne 0 -and -not (Alive $c)) { return "EXITED" }
        return $null
    }
    function Spawned($c) { return ((Get-Text (Join-Path $c.Logs "qa_events.log")) -match "SPAWNED section") }
    function Start-Game($c, $startArg, $exeRel = "xrEngine.exe", $pre = "") {
        $a = "$pre-noprefetch -nointro -fsltx ..\$(Split-Path $c.Fs -Leaf) -addon=$Addon $ExtraArgs -start $startArg"
        $p = Start-Process (Join-Path $bin $exeRel) -ArgumentList $a -WorkingDirectory $bin -PassThru
        $c.Pid = $p.Id
        $script:started += $p.Id
        & $py -I $slotPy register-pid --owner $Owner --pid $p.Id | Out-Null
        Say "started $($c.Role) ($($c.Name)) pid $($p.Id)"
    }

    # ---- 4. launch (same command lines as run_coop.ps1)
    $lan = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notmatch "^(127\.|169\.254\.)" -and $_.PrefixOrigin -ne "WellKnown" } | Sort-Object { if ($_.PrefixOrigin -eq "Dhcp") { 0 } else { 1 } } | ForEach-Object { $_.IPAddress })
    $joinHost = $lan | Select-Object -First 1
    $A = $cl[0]
    $server = "server($Map/coop/hname=qa$Owner/maxplayers=4/public=0/minplayers=1/portsv=$Port)"
    $failure = $null
    $t0 = Get-Date
    $warn = $null; $readyAt = $null
    if ($Mode -eq "listen") {
        Start-Game $A "$server client(localhost/name=$($A.Name))"
        for ($k = 1; $k -lt $cl.Count; $k++) {
            while (-not (Spawned $A) -and (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSeconds)) {
                $f = Crashed $A; if ($f) { $failure = "client A $f"; break }
                Start-Sleep 2
            }
            if ($failure -or -not (Spawned $A)) { if (-not $failure) { $failure = "client A never spawned" }; break }
            Start-Game $cl[$k] "client($joinHost/name=$($cl[$k].Name)/port=$Port)"
        }
    } else {
        Start-Game $srv "$server client(localhost)" "dedicated\xrEngine.exe" "-i "
        while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSeconds) {
            $f = Crashed $srv; if ($f) { $failure = "dedicated server $f"; break }
            if ((Get-Text $srv.XLog) -match "Connection finished") { break }
            Start-Sleep 2
        }
        if (-not $failure) {
            Say "dedicated server up"
            for ($k = 0; $k -lt $cl.Count; $k++) { Start-Game $cl[$k] "client($joinHost/name=$($cl[$k].Name)/port=$Port)"; Start-Sleep 5 }
        }
    }
    if (-not $failure) {
        while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSeconds) {
            foreach ($c in $roles) { $f = Crashed $c; if ($f) { $failure = "role $($c.Role) $f" } }
            if ($failure) { break }
            $notSp = @($cl | Where-Object { -not (Spawned $_) }).Count
            $notReady = @($roles | Where-Object { -not (Test-Path (Join-Path $_.Logs "live_ready.txt")) }).Count
            if ($notSp -eq 0 -and $notReady -eq 0) { break }
            # a loaded save whose level has no respawn point for NEW players (X18, ...): the world is loaded and every role answers, only the client stays a spectator.
            # Accept after -SpawnGrace seconds: server queries work, the client camera does not.
            if ($notReady -eq 0 -and $null -eq $readyAt) { $readyAt = Get-Date }
            if ($Save -ne "" -and $notReady -eq 0 -and $notSp -gt 0 -and ((Get-Date) - $readyAt).TotalSeconds -gt $SpawnGrace) {
                $warn = "client(s) $((@($cl | Where-Object { -not (Spawned $_) } | ForEach-Object { $_.Role })) -join ',') did not spawn as a player within $SpawnGrace s (no respawn point for new players on this level?); the world is loaded, server queries work"
                break
            }
            Start-Sleep 1
        }
        if ($warn) { Say "WARNING: $warn" }
        elseif (-not $failure -and (@($cl | Where-Object { -not (Spawned $_) }).Count -gt 0 -or @($roles | Where-Object { -not (Test-Path (Join-Path $_.Logs "live_ready.txt")) }).Count -gt 0)) { $failure = "timeout: not every role spawned/ready" }
    }
    $state = [ordered]@{
        name = $Name; owner = $Owner; tag = $tag; extra_dirs = @($ExtraDir); slot = $slotIdx; port = $Port; map = $Map; mode = $Mode; addon = $Addon; save = $Save
        save_stage = if ($saveMeta) { "$($saveMeta.stage)" } else { "" }
        started = (Get-Date).ToString("s"); game = $Game; pids = $started
        roles = @($roles | ForEach-Object { [ordered]@{ role = $_.Role; name = $_.Name; pid = $_.Pid; app = $_.App; fs = $_.Fs; logs = $_.Logs; shots = $_.Shots } })
    }
    ($state | ConvertTo-Json -Depth 5) | Set-Content -Encoding ascii $stateFile
    if ($failure) { Say "FAILURE: $failure"; $exit = 1; throw "boot" }
    $ok = $true
    $exit = 0
    Say ("LIVE READY in {0:N0} s: map {1}, mode {2}, roles {3}, slot {4}, port {5}. Send Lua: lua.ps1 -Role {6} ""<lua>"" ; stop: stop_live.ps1 -Name {7}" -f ((Get-Date) - $t0).TotalSeconds, $Map, $Mode, (($roles | ForEach-Object { $_.Role }) -join ","), $slotIdx, $Port, $(if ($srv) { "S" } else { "A" }), $Name)
} catch {
    if ($exit -eq 3) { Say "SETUP ERROR: $_" }
} finally {
    if (-not $ok) {
        foreach ($p in $started) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
        if ($started.Count -gt 0) { Start-Sleep 3 }
        # keep the failed run's logs for diagnosis
        if ($roles.Count -gt 0) {
            $dst = Join-Path $here "logs\failed_$tag"
            New-Item -ItemType Directory -Force $dst | Out-Null
            foreach ($rl in $roles) { $d = Join-Path $dst $rl.Role; New-Item -ItemType Directory -Force $d | Out-Null; Copy-Item (Join-Path $rl.Logs "*") $d -Force -ErrorAction SilentlyContinue }
            Say "logs of the failed boot: $dst"
        }
        Remove-Item $stateFile -Force -ErrorAction SilentlyContinue   # only this run created it (CreateNew lock above)
        for ($try = 0; $try -lt 15; $try++) {
            foreach ($x in $cleanup) { Remove-Item $x -Recurse -Force -ErrorAction SilentlyContinue }
            if (-not ($cleanup | Where-Object { Test-Path $_ })) { break }
            Start-Sleep 2
        }
        & $py -I $slotPy release --owner $Owner | Out-Null
    }
}
exit $exit
