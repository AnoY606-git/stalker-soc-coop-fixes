param([string[]]$Levels)
$game = "C:\X-Ray Multiplayer Extension\game"
$log = "$game\_appdata_server\logs\xray_$env:USERNAME.log"
foreach ($lvl in $Levels) {
    $a = "-i -fsltx ..\fsgame_s.ltx -addon=coop.addon -use_all_spawn -start server($lvl/coop/hname=boottest/maxplayers=1/public=0/minplayers=1/difficulty=gd_veteran/portsv=5450) client(localhost)"
    Remove-Item $log -ErrorAction SilentlyContinue
    $p = Start-Process "$game\bin\dedicated\xrEngine.exe" -ArgumentList $a -WorkingDirectory "$game\bin" -PassThru
    $result = "TIMEOUT"
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 1
        $t = Get-Content $log -Raw -ErrorAction SilentlyContinue
        if ($t -match "FATAL ERROR") { $result = "CRASH: " + (([regex]::Match($t, "\[error\]Arguments\s*:\s*(.*)")).Groups[1].Value); break }
        if ($t -match "Connection finished") { Start-Sleep -Seconds 15; $t = Get-Content $log -Raw; if ($t -match "FATAL ERROR") { $result = "CRASH(late): " + (([regex]::Match($t, "\[error\]Arguments\s*:\s*(.*)")).Groups[1].Value) } else { $result = "OK" }; break }
        if ($p.HasExited) { $result = "EXITED code $($p.ExitCode)"; break }
    }
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 2 }
    $patch = if ((Get-Content $log -Raw) -match "coop.addon \((\d+) databases\)") { $matches[1] } else { "?" }
    "{0,-30} dbs={1}  {2}" -f $lvl, $patch, $result
}
