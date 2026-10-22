# Timed demo of the live console (the transcript in README.md was made with this):  demo.ps1 [-Owner lcdemo]
# 1. start Cordon live  2. five commands  3. stop  4. start with the Bar save and query the Bar population.  Writes live\demo_transcript.txt.
param([string]$Owner = "lcdemo")
$here = $PSScriptRoot
$lua = Join-Path $here "lua.ps1"
$tr = Join-Path $here "demo_transcript.txt"
"" | Set-Content $tr
$global:T0 = Get-Date
function Log($m) { $l = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $m; Write-Host $l; Add-Content $tr $l }
function Run($role, $code) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    Log "lua.ps1 -Role $role `"$code`""
    $o = & powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Owner -Role $role -Quiet $code 2>&1
    foreach ($l in @($o | Select-Object -First 12)) { Log "    $l" }
    Log ("    => {0:N2} s wall clock (incl. starting powershell)" -f $sw.Elapsed.TotalSeconds)
}
$ex = (Join-Path $here "stages\release_v1.3_lite\gamedata")
$t = Get-Date
Log "start_live.ps1 -Map coop_l01_escape (Cordon)"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "start_live.ps1") -Map coop_l01_escape -Owner $Owner -Name $Owner -ExtraDir $ex | ForEach-Object { Log "    $_" }
Log ("Cordon live ready after {0:N0} s (slot wait and lane build included)" -f ((Get-Date) - $t).TotalSeconds)
$d0 = Get-Date
Run "S" "live.count(live.find('esc_campfire', 1)[1].pos, 25, 'stalker')"
Run "S" "live.near(live.find('esc_campfire', 1)[1].pos, 25, 'stalker')"
Run "S" "live.peace()"
Run "S" "bid = live.spawn('sim_default_bandit_1')"
Start-Sleep 2
Run "S" "live.kill(bid, 0.02, nil, 'fire_wound')"
# the Sidorovich intro scene (fresh start) teleports players back into the bunker until it is over: wait for it
$w0 = Get-Date
do { $st = (& powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Owner -Role S -Quiet "coop_scenes.status()" 2>&1 | Select-Object -First 1); Start-Sleep 3 } until ("$st" -match "active=nil" -or ((Get-Date) - $w0).TotalSeconds -gt 150)
Log ("intro scene state: {0} (waited {1:N0} s)" -f $st, ((Get-Date) - $w0).TotalSeconds)
Run "S" "live.tp(-206, -19.6, -130)"
Run "A" "live.shot('demo_cordon_fire')"
Run "S" "live.inv()"
Run "S" "coop_scenes.status()"
Run "S" "live.reload('coop_scenes', [[$(Join-Path $here 'demo\status_patch.lua')]])"
Run "S" "coop_scenes.status()"
Log ("5 commands (count, spawn+kill, tp+shot, inv, reload) done in {0:N0} s after READY" -f ((Get-Date) - $d0).TotalSeconds)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "stop_live.ps1") -Name $Owner | ForEach-Object { Log "    $_" }
$t = Get-Date
Log "start_live.ps1 -Save bar_arrival"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "start_live.ps1") -Save bar_arrival -Owner $Owner -Name $Owner -ExtraDir $ex | ForEach-Object { Log "    $_" }
Log ("Bar live ready after {0:N0} s" -f ((Get-Date) - $t).TotalSeconds)
Run "S" "live.state()"
Run "S" "live.count('me', 60, 'stalker')"
Run "S" "live.near('me', 40, 'stalker')"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "stop_live.ps1") -Name $Owner | ForEach-Object { Log "    $_" }
