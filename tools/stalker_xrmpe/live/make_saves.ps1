# Rebuilds the ready-made saves in live\saves (one live session per save, run one after the other):
#   make_saves.ps1 [-Only cordon_start,bar_arrival,agroprom,x18_entrance,sarcophagus] [-ExtraDir <gamedata folder>] [-Owner lcsave]
# cordon_start : fresh Cordon start, saved once the opening scenes (intro + Sidorovich) are played
# the others   : session started from cordon_start (-Save), party vote from Cordon (live.travel), saved right after the arrival
# sarcophagus  : travel too (guide flag SAR); the harness cannot start the Sarcophagus with a save, so it is reached by the vote as well
# Every save records the stage (ExtraDir) it was made with in live\saves\<name>.json.  The saves only load with the same stage (all.spawn).
param(
    [string[]]$Only = @("cordon_start", "bar_arrival", "agroprom", "x18_entrance", "sarcophagus"),
    [string[]]$ExtraDir = @(),
    [string]$Owner = "lcsave"
)
$here = $PSScriptRoot
$Only = @($Only | ForEach-Object { $_ -split "," })          # -File passes "a,b" as one string
$ExtraDir = @($ExtraDir | ForEach-Object { $_ -split ";" } | Where-Object { $_ })
if ($ExtraDir.Count -eq 0) { $ExtraDir = @((Join-Path $here "stages\release_v1.3_lite\gamedata")) }
$plan = @{
    cordon_start = @{ from = ""; dest = ""; note = "Cordon after the opening movie and Sidorovich's intro (coop_scenes intro + sidor_intro played); player in the bunker" }
    bar_arrival  = @{ from = "cordon_start"; dest = "bar"; note = "Bar right after the party vote from Cordon (alife online)" }
    agroprom     = @{ from = "cordon_start"; dest = "agr"; note = "Agroprom right after the party vote from Cordon" }
    x18_entrance = @{ from = "cordon_start"; dest = "x18"; note = "X18 (coop_l04_x18) right after the party vote from Cordon: the arrival point is the entrance" }
    sarcophagus  = @{ from = "cordon_start"; dest = "sar"; note = "Sarcophagus right after the party vote from Cordon (Monolith, door and decoder state as on arrival)" }
}
$lua = Join-Path $here "lua.ps1"
foreach ($name in $Only) {
    $p = $plan[$name]
    if (-not $p) { Write-Host "unknown save '$name'"; continue }
    Write-Host "=== $name"
    $sargs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $here "start_live.ps1"), "-Owner", $Owner, "-Name", $Owner, "-ExtraDir") + $ExtraDir
    if ($p.from -ne "") { $sargs += @("-Save", $p.from) } else { $sargs += @("-Map", "coop_l01_escape") }
    & powershell @sargs
    if ($LASTEXITCODE -ne 0) { Write-Host "start_live failed ($LASTEXITCODE) for $name"; continue }
    try {
        if ($p.dest -ne "") {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Owner -Timeout 300 "live.travel('$($p.dest)')"
            Start-Sleep 8
        } else {
            Start-Sleep 5
        }
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "save_live.ps1") -As $name -Name $Owner -Note $p.note
    } finally {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "stop_live.ps1") -Name $Owner
    }
}
