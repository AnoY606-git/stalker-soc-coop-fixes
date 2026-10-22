# Loads each save in a live session and checks level + alife + stalker count near the world player.   verify_saves.ps1 [-Only a,b] [-Owner lcver]
param([string[]]$Only = @(), [string]$Owner = "lcver", [string[]]$ExtraDir = @())
$here = $PSScriptRoot
$Only = @($Only | ForEach-Object { $_ -split "," } | Where-Object { $_ })
if ($Only.Count -eq 0) { $Only = @(Get-ChildItem (Join-Path $here "saves") -Filter *.scop | ForEach-Object { $_.BaseName }) }
$ExtraDir = @($ExtraDir | ForEach-Object { $_ -split ";" } | Where-Object { $_ })
if ($ExtraDir.Count -eq 0) { $ExtraDir = @((Join-Path $here "stages\release_v1.3_lite\gamedata")) }
$lua = Join-Path $here "lua.ps1"
foreach ($name in $Only) {
    $meta = Get-Content (Join-Path $here "saves\$name.json") -Raw | ConvertFrom-Json
    $t = Get-Date
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "start_live.ps1") -Save $name -Owner $Owner -Name $Owner -ExtraDir $ExtraDir | Select-Object -Last 2 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) { Write-Host "VERIFY $name : FAIL (start_live exit $LASTEXITCODE)"; continue }
    $boot = ((Get-Date) - $t).TotalSeconds
    Start-Sleep 10
    $st = (& powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Owner -Role S -Quiet "live.state()" | Select-Object -First 1)
    $n = (& powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Owner -Role S -Quiet "live.count('me', 80, 'stalker')" | Select-Object -First 1)
    $okLevel = ("$st" -match "level=$($meta.level) ") -and ("$st" -match "alife=true")
    Write-Host ("VERIFY {0}: {1} (expected level {2}); stalkers within 80 m of the world player: {3}; {4:N0} s to ready incl. waits`n  {5}" -f $name, $(if ($okLevel) { "PASS" } else { "FAIL" }), $meta.level, $n, $boot, $st)
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "stop_live.ps1") -Name $Owner | Out-Null
}
