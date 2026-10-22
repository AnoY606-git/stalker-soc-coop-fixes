# Ends a live session: kills ONLY its own game pids, keeps its logs in live\logs\<tag>, deletes its appdata/fsgame copies, releases the slot.
#   stop_live.ps1 [-Name live] [-NoLogs]
param([string]$Name = "live", [switch]$NoLogs)
$here = $PSScriptRoot
$tools = Split-Path $here -Parent
$stateFile = Join-Path $here "state\$Name.json"
if (-not (Test-Path $stateFile)) { Write-Host "no live session '$Name'"; exit 3 }
$st = Get-Content $stateFile -Raw | ConvertFrom-Json
$py = (Get-Command python -ErrorAction Stop).Source
foreach ($p in @($st.pids)) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
Start-Sleep 3
if (-not $NoLogs) {
    $dst = Join-Path $here ("logs\" + $st.tag)
    foreach ($r in $st.roles) {
        $d = Join-Path $dst $r.role; New-Item -ItemType Directory -Force $d | Out-Null
        Get-ChildItem $r.logs -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch "\.mdmp$" } | Copy-Item -Destination $d -Force -ErrorAction SilentlyContinue
    }
    Write-Host "logs kept in $dst"
}
for ($try = 0; $try -lt 15; $try++) {
    foreach ($r in $st.roles) { Remove-Item $r.app -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item $r.fs -Force -ErrorAction SilentlyContinue }
    if (-not (@($st.roles) | Where-Object { [IO.Directory]::Exists($_.app) -or [IO.File]::Exists($_.fs) })) { break }
    Start-Sleep 2
}
& $py -I (Join-Path $tools "stalker_slot.py") release --owner $st.owner | Out-Null
Remove-Item $stateFile -Force
Write-Host "live session '$Name' stopped, slot $($st.slot) released"
