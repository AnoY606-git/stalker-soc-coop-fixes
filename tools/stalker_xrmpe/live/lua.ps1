# Send Lua to a running live session and print the result.   (see live\README.md)
#   lua.ps1 [-Role S|A|B] [-Name live] [-Timeout 30] "<lua chunk>"        e.g.  lua.ps1 "live.state()"
#   lua.ps1 [-Role A] -File my.lua
# The chunk runs inside the game on that role (S = dedicated server with alife, A/B = clients).  Default role: S if the session has one, else A.
# Output: printed lines and return values. Exit code 0 = OK, 1 = Lua error, 2 = timeout (the game did not answer), 3 = no session.
# A "SHOT:<name>" result (live.shot) is followed by copying the new engine screenshot to live\shots\<name>.jpg|png.
param(
    [Parameter(Position = 0)][string]$Code = "",
    [string]$File = "",
    [string]$Role = "",
    [string]$Name = "live",
    [double]$Timeout = 30,
    [switch]$Quiet
)
$here = $PSScriptRoot
$stateFile = Join-Path $here "state\$Name.json"
if (-not (Test-Path $stateFile)) { Write-Host "no live session '$Name' (run start_live.ps1)"; exit 3 }
$st = Get-Content $stateFile -Raw | ConvertFrom-Json
if (-not $st.roles) { Write-Host "session '$Name' is still booting (start_live.ps1 has not finished)"; exit 3 }
if ($Role -eq "") { $Role = if (@($st.roles | Where-Object { $_.role -eq "S" }).Count -gt 0) { "S" } else { "A" } }
$r = @($st.roles | Where-Object { $_.role -eq $Role.ToUpper() })[0]
if (-not $r) { Write-Host "role '$Role' not in this session (roles: $((@($st.roles | ForEach-Object { $_.role })) -join ','))"; exit 3 }
if (-not (Get-Process -Id $r.pid -ErrorAction SilentlyContinue)) { Write-Host "role $($r.role) (pid $($r.pid)) is not running (crashed?). Logs: $($r.logs)"; exit 3 }
if ($File -ne "") { $Code = [IO.File]::ReadAllText((Resolve-Path $File)) }
if ($Code -eq "") { Write-Host "no Lua given"; exit 3 }
$logs = $r.logs
$seq = 0
Get-ChildItem $logs -Filter "live_cmd_*.lua" -ErrorAction SilentlyContinue | ForEach-Object { if ($_.BaseName -match "live_cmd_(\d+)$") { $n = [int]$Matches[1]; if ($n -gt $seq) { $seq = $n } } }
$n = $seq + 1
$sw = [Diagnostics.Stopwatch]::StartNew()
$t0 = Get-Date
$tmp = Join-Path $logs "live_cmd_$n.tmp"
[IO.File]::WriteAllText($tmp, $Code, (New-Object Text.UTF8Encoding($false)))
Move-Item $tmp (Join-Path $logs "live_cmd_$n.lua") -Force
$resf = Join-Path $logs "live_res_$n.txt"
$text = $null
while ($sw.Elapsed.TotalSeconds -lt $Timeout) {
    if (Test-Path $resf) {
        try { $t = [IO.File]::ReadAllText($resf) } catch { $t = "" }
        if ($t -match "--END--") { $text = $t; break }
    }
    Start-Sleep -Milliseconds 40
}
if ($null -eq $text) {
    Write-Host ("TIMEOUT after {0:N1} s: role {1} did not answer command {2}. Is the game frozen or loading a level? (commands are queued, the answer may still come)" -f $sw.Elapsed.TotalSeconds, $r.role, $n)
    exit 2
}
$lines = $text -split "`r?`n"
$hdr = $lines[0]
$body = @($lines | Select-Object -Skip 1 | Where-Object { $_ -ne "--END--" })
while ($body.Count -gt 0 -and $body[-1] -eq "") { $body = @($body | Select-Object -First ($body.Count - 1)) }
$body | ForEach-Object { Write-Host $_ }
$shot = $body | Where-Object { $_ -match "^SHOT:(.+)$" } | Select-Object -First 1
if ($shot -and $shot -match "^SHOT:(.+)$") {
    $sname = $Matches[1]
    $end = (Get-Date).AddSeconds(10)
    $f = $null
    while ((Get-Date) -lt $end -and -not $f) {
        $f = Get-ChildItem $r.shots -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $t0.AddSeconds(-1) } | Sort-Object LastWriteTime | Select-Object -Last 1
        if (-not $f) { Start-Sleep -Milliseconds 200 }
    }
    if ($f) {
        Start-Sleep -Milliseconds 400
        $dst = Join-Path $here "shots"; New-Item -ItemType Directory -Force $dst | Out-Null
        $out = Join-Path $dst ($sname + $f.Extension)
        Copy-Item $f.FullName $out -Force
        Write-Host "screenshot saved: $out"
    } else { Write-Host "screenshot file did not appear in $($r.shots) within 10 s" }
}
if (-not $Quiet) { Write-Host ("({0}, role {1}, {2:N2} s round trip, in-game {3})" -f $hdr.Split(" ")[0], $r.role, $sw.Elapsed.TotalSeconds, ($hdr -replace "^\S+ ", "") + " ms") }
if ($hdr.StartsWith("OK")) { exit 0 } else { exit 1 }
