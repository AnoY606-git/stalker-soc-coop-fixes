# Make a ready-made save from the running live session:  save_live.ps1 -As bar_arrival [-Name live] [-Note "text"] [-Timeout 60]
# Asks the server role (S, or A in a listen session) to run game_sv.saveGame, waits for the new savedgames\<addon>\*.scop, copies it to
# live\saves\<As>.scop and writes live\saves\<As>.json (level, the stage the session ran with, date).  start_live.ps1 -Save <As> uses it.
param(
    [Parameter(Mandatory = $true)][string]$As,
    [string]$Name = "live",
    [string]$Note = "",
    [int]$Timeout = 60
)
$here = $PSScriptRoot
$stateFile = Join-Path $here "state\$Name.json"
if (-not (Test-Path $stateFile)) { Write-Host "no live session '$Name'"; exit 3 }
$st = Get-Content $stateFile -Raw | ConvertFrom-Json
$holder = @($st.roles | Where-Object { $_.role -eq "S" })[0]
if (-not $holder) { $holder = @($st.roles | Where-Object { $_.role -eq "A" })[0] }
$sd = Join-Path $holder.app ("savedgames\" + [IO.Path]::GetFileNameWithoutExtension($st.addon))
function Snap { $h = @{}; if (Test-Path $sd) { Get-ChildItem $sd -Filter *.scop | ForEach-Object { $h[$_.Name] = "$($_.LastWriteTimeUtc.Ticks)/$($_.Length)" } }; return $h }
$before = Snap
$lua = Join-Path $here "lua.ps1"
$lvl = (& powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Name -Role $holder.role -Quiet "level.name()" | Select-Object -First 1)
if ($lvl -notmatch "^coop_") { Write-Host "cannot read the level name from the game: $lvl"; exit 1 }
$null = & powershell -NoProfile -ExecutionPolicy Bypass -File $lua -Name $Name -Role $holder.role -Quiet "live.save()"
$sw = [Diagnostics.Stopwatch]::StartNew()
$new = $null
while ($sw.Elapsed.TotalSeconds -lt $Timeout -and -not $new) {
    $now = Snap
    foreach ($k in $now.Keys) { if (-not $before.ContainsKey($k) -or $before[$k] -ne $now[$k]) { $new = $k } }
    if (-not $new) { Start-Sleep -Milliseconds 300 }
}
if (-not $new) { Write-Host "no new .scop appeared in $sd within $Timeout s"; exit 1 }
Start-Sleep -Milliseconds 1500   # let the writer finish
$savesDir = Join-Path $here "saves"; New-Item -ItemType Directory -Force $savesDir | Out-Null
$dst = Join-Path $savesDir "$As.scop"
Copy-Item (Join-Path $sd $new) $dst -Force
$stage = if (@($st.extra_dirs).Count -gt 0) { "coop.addon + -ExtraDir " + (@($st.extra_dirs) -join ";") } else { "coop.addon as installed (no -ExtraDir)" }
$meta = [ordered]@{
    name = $As; level = $lvl; stage = $stage; extra_dirs = @($st.extra_dirs); source_file = $new; bytes = (Get-Item $dst).Length
    made = (Get-Date).ToString("s"); session_map = $st.map; session_save = $st.save; mode = $st.mode; note = $Note
}
($meta | ConvertTo-Json -Depth 4) | Set-Content -Encoding ascii (Join-Path $savesDir "$As.json")
Write-Host ("saved '{0}': level {1}, {2} bytes, stage: {3} ({4:N1} s)" -f $As, $lvl, (Get-Item $dst).Length, $stage, $sw.Elapsed.TotalSeconds)
