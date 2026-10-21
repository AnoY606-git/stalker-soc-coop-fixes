# TEST ONLY: after the hook logged "OPEN talk_ready" in THIS run's client A log, press key 1 into THIS run's client A window only (pid from run.log).
param([string]$ResultDir, [string]$Tag, [string]$At = "3,9,15,21", [string]$Marker = "OPEN talk_ready", [string]$Keys = "31:02")
$inj = Join-Path $PSScriptRoot "inject.ps1"
$runlog = Join-Path $ResultDir "run.log"
$pid_ = $null
for ($i = 0; $i -lt 3000 -and -not $pid_; $i++) {
    if (Test-Path $runlog) {
        $m = Select-String -Path $runlog -Pattern "started client A \(qaA\) pid (\d+)" | Select-Object -First 1
        if ($m) { $pid_ = [int]$m.Matches[0].Groups[1].Value }
    }
    if (-not $pid_) { Start-Sleep -Seconds 2 }
}
"client pid $pid_"
$ev = $null
$t0 = $null
for ($i = 0; $i -lt 3000 -and -not $t0; $i++) {
    $d = Get-ChildItem "C:\X-Ray Multiplayer Extension\game" -Directory -Filter "_appdata_qa_${Tag}*_A" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($d) {
        $f = Join-Path $d.FullName "logs\qa_events.log"
        if (Test-Path $f) {
            $c = $null
            try { $c = [IO.File]::ReadAllText($f) } catch {}
            if ($c -and $c.Contains($Marker)) { $t0 = Get-Date }
        }
    }
    if (-not $t0) { Start-Sleep -Milliseconds 500 }
}
"marker seen $t0"
foreach ($s in ($At -split ",")) {
    $s = [int]$s
    $wait = ($t0.AddSeconds($s) - (Get-Date)).TotalMilliseconds
    if ($wait -gt 0) { Start-Sleep -Milliseconds ([int]$wait) }
    & $inj -ProcId $pid_ -Keys $Keys -Ms 120
    "pressed at +$s"
}
