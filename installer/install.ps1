# Shadow of COOP fix patch installer.
# Writes zzz_soc_coop_fixes.db into coop.addon byte-for-byte the same way on every PC, so host and clients get the same
# addon checksum. (Dragging the file in with 7-Zip stores your user id and the file date, which makes every player's
# coop.addon different and the server reports "Different Versions".)
#
# Usage: install.bat (same folder as zzz_soc_coop_fixes.db). Optional: install.bat -Addon "D:\...\coop.addon"
#        install.bat -Uninstall
param(
    [string]$Addon = "",
    [string]$Db = "",
    [switch]$Uninstall
)
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PatchName = "zzz_soc_coop_fixes.db"
$BaseNames = @("gamedata.db0", "gamedata.db1", "icon.webp", "metadata.json")
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

# Accepts the coop.addon file itself, its addons folder, the game folder or the install folder (even a nested
# "X-Ray Multiplayer Extension\X-Ray Multiplayer Extension"); returns the coop.addon file path or $null.
function Resolve-AddonPath([string]$p) {
    if (-not $p) { return $null }
    $p = $p.Trim().Trim('"').Trim()
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    if (Test-Path -LiteralPath $p -PathType Leaf) { return (Resolve-Path -LiteralPath $p).Path }
    foreach ($rel in @("coop.addon", "addons\coop.addon", "game\addons\coop.addon",
                       "X-Ray Multiplayer Extension\game\addons\coop.addon")) {
        $c = Join-Path $p $rel
        if (Test-Path -LiteralPath $c -PathType Leaf) { return (Resolve-Path -LiteralPath $c).Path }
    }
    return $null
}

function Find-Addon {
    $roots = @($Here, (Join-Path $Here ".."))
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        if ($d.DriveType -ne 'Fixed' -or -not $d.IsReady) { continue }
        foreach ($sub in @("", "Games\", "Program Files\", "Program Files (x86)\")) {
            $roots += ($d.RootDirectory.FullName + $sub + "X-Ray Multiplayer Extension")
        }
    }
    foreach ($r in $roots) { $f = Resolve-AddonPath $r; if ($f) { return $f } }
    Write-Host "coop.addon not found automatically. / coop.addon не найден автоматически."
    Write-Host "You can paste the coop.addon file or its folder. / Можно вставить путь к файлу coop.addon или к его папке."
    $p = Read-Host "Path / Путь"
    $f = Resolve-AddonPath $p
    if (-not $f) { throw "coop.addon not found at: $p / coop.addon не найден по пути: $p" }
    return $f
}

function Read-Octal([byte[]]$h, [int]$off, [int]$len) {
    $s = [System.Text.Encoding]::ASCII.GetString($h, $off, $len).Trim([char]0, ' ')
    if ($s -eq "") { return [long]0 }
    return [Convert]::ToInt64($s, 8)
}

function Write-Field([byte[]]$h, [int]$off, [string]$s) {
    $b = [System.Text.Encoding]::ASCII.GetBytes($s)
    [Array]::Copy($b, 0, $h, $off, $b.Length)
}

if ($Addon -eq "") { $Addon = Find-Addon }
else {
    $f = Resolve-AddonPath $Addon
    if (-not $f) { throw "coop.addon not found at: $Addon / coop.addon не найден по пути: $Addon" }
    $Addon = $f
}
if (-not $Uninstall) {
    if ($Db -eq "") { $Db = Join-Path $Here $PatchName }
    if (-not (Test-Path -LiteralPath $Db)) { throw "$PatchName not found next to install.bat / не найден рядом с install.bat" }
}
Write-Host "coop.addon: $Addon"

try {
    $fs = [System.IO.File]::Open($Addon, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
    Write-Host "Cannot open coop.addon for writing. Close the game AND the xrMPE launcher, then run install.bat again." -ForegroundColor Red
    Write-Host "Не удалось открыть coop.addon для записи. Закройте игру И лаунчер xrMPE, затем снова запустите install.bat." -ForegroundColor Red
    Write-Host "If it still fails, right-click install.bat > Run as administrator. / Если не помогает: ПКМ по install.bat > Запуск от имени администратора."
    throw
}
try {
    # Walk the tar headers. Keep the add-on's own entries; cut everything from the first extra entry on.
    $pos = [long]0
    $cut = [long]-1
    $h = New-Object byte[] 512
    while ($pos + 512 -le $fs.Length) {
        $fs.Position = $pos
        [void]$fs.Read($h, 0, 512)
        $allZero = $true
        foreach ($x in $h) { if ($x -ne 0) { $allZero = $false; break } }
        if ($allZero) { if ($cut -lt 0) { $cut = $pos }; break }
        $nameEnd = [Array]::IndexOf($h, [byte]0)
        if ($nameEnd -lt 0 -or $nameEnd -gt 100) { $nameEnd = 100 }
        $name = [System.Text.Encoding]::ASCII.GetString($h, 0, $nameEnd)
        $size = Read-Octal $h 124 12
        if ($BaseNames -contains $name) {
            if ($cut -ge 0) { throw "coop.addon has '$name' after an extra file; restore your coop.addon backup or re-download the add-on." }
        } elseif ($cut -lt 0) {
            $cut = $pos
            Write-Host "Removing old entry / Удаляю старый файл: $name"
        } else {
            Write-Host "Removing old entry / Удаляю старый файл: $name"
        }
        $pos += 512 + [long]([Math]::Ceiling($size / 512.0) * 512)
    }
    if ($cut -lt 0) { $cut = $pos }
    $seen = @()
    $fs.Position = 0
    $p2 = [long]0
    while ($p2 -lt $cut) {
        $fs.Position = $p2; [void]$fs.Read($h, 0, 512)
        $nameEnd = [Array]::IndexOf($h, [byte]0); if ($nameEnd -lt 0 -or $nameEnd -gt 100) { $nameEnd = 100 }
        $seen += [System.Text.Encoding]::ASCII.GetString($h, 0, $nameEnd)
        $p2 += 512 + [long]([Math]::Ceiling((Read-Octal $h 124 12) / 512.0) * 512)
    }
    foreach ($b in $BaseNames) { if ($seen -notcontains $b) { throw "This does not look like the Shadow of COOP coop.addon (missing $b)." } }

    if (-not $Uninstall) {
        # The engine is 32-bit: every byte of the tar must stay below 4 GiB. Refuse BEFORE touching coop.addon.
        $dbLen = (Get-Item -LiteralPath $Db).Length
        $finalSize = $cut + 512 + [long]([Math]::Ceiling($dbLen / 512.0) * 512) + 1024
        $finalSize = [long]([Math]::Ceiling($finalSize / 10240.0) * 10240)
        $limit4g = [long]4294967296
        if ($finalSize -gt $limit4g) {
            $over = [Math]::Round(($finalSize - $limit4g) / 1MB, 1)
            Write-Host ""
            Write-Host "NOT INSTALLED: with this patch coop.addon would be $finalSize bytes, $over MB over the 4 GiB limit of the 32-bit game engine (the game would not load levels). coop.addon was not changed."
            Write-Host "Your coop.addon is probably bigger than the original (other mods or test files inside). Restore the original coop.addon from the mod download and run the installer again."
            Write-Host "НЕ УСТАНОВЛЕНО: с этим патчем coop.addon стал бы $finalSize байт, это на $over МБ больше предела 4 ГиБ для 32-битного движка (игра не загрузит уровни). coop.addon не изменён."
            Write-Host "Скорее всего ваш coop.addon больше оригинального (внутри другие моды или тестовые файлы). Восстановите оригинальный coop.addon из архива мода и запустите установщик снова."
            throw "coop.addon would exceed 4 GiB / coop.addon превысил бы 4 ГиБ"
        }
    }
    $fs.SetLength($cut)
    $fs.Position = $cut
    if (-not $Uninstall) {
        $data = [System.IO.File]::ReadAllBytes($Db)
        $hdr = New-Object byte[] 512
        Write-Field $hdr 0 $PatchName
        Write-Field $hdr 100 "0000644`0"                                   # mode
        Write-Field $hdr 108 "0000000`0"                                   # uid
        Write-Field $hdr 116 "0000000`0"                                   # gid
        Write-Field $hdr 124 ([Convert]::ToString([long]$data.Length, 8).PadLeft(11, '0') + "`0")
        Write-Field $hdr 136 "00000000000`0"                               # mtime 0: same on every PC
        Write-Field $hdr 156 "0"                                           # regular file
        for ($i = 148; $i -lt 156; $i++) { $hdr[$i] = 32 }
        $sum = 0; foreach ($x in $hdr) { $sum += $x }
        Write-Field $hdr 148 ([Convert]::ToString($sum, 8).PadLeft(6, '0') + "`0 ")
        $fs.Write($hdr, 0, 512)
        $fs.Write($data, 0, $data.Length)
        $pad = (512 - ($data.Length % 512)) % 512
        if ($pad -gt 0) { $fs.Write((New-Object byte[] $pad), 0, $pad) }
    }
    # End of archive: two zero blocks, then pad to a whole 10240-byte record.
    $end = $fs.Position + 1024
    $end = [long]([Math]::Ceiling($end / 10240.0) * 10240)
    $zeros = New-Object byte[] ($end - $fs.Position)
    $fs.Write($zeros, 0, $zeros.Length)
    $fs.SetLength($end)
} finally {
    $fs.Close()
}

$sha = (Get-FileHash -LiteralPath $Addon -Algorithm SHA256).Hash.Substring(0, 12)
if ($Uninstall) { Write-Host "Patch removed. / Патч удалён." }
else { Write-Host "Installed. / Установлено." }
Write-Host "Addon fingerprint (must be the same for every player) / Отпечаток (должен совпадать у всех): $sha"
