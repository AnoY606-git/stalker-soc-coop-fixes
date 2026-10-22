# Shadow of COOP cutscene pack installer.
# Puts the original S.T.A.L.K.E.R. SoC movies (X18 / Radar / Yantar dreams, Monolith join dream) and the movie sound tracks where the game
# loads them: into <xrMPE>\game\patches\ as X-Ray archives (zz_soc_cutscenes*.db). The pack is NOT part of coop.addon and does not change
# the add-on fingerprint, so it never causes "Different Versions"; each player installs it for himself.
#
# Usage: install_cutscenes.bat (same folder as the zz_soc_cutscenes*.db files)
#   install_cutscenes.bat -Voice rus|eng|auto   language of the movie sound (auto = your coop_settings.ltx voice_language, else the launcher language)
#   install_cutscenes.bat -Loose                unpack the files into <xrMPE>\game\gamedata\ instead of copying archives to patches\
#                                               (use it if the launcher ever removes the unknown files from patches\)
#   install_cutscenes.bat -Uninstall            remove everything this installer put there
#   install_cutscenes.bat -Game "D:\...\X-Ray Multiplayer Extension"   if the folder is not found automatically
param(
    [string]$Game = "",
    [ValidateSet("auto", "rus", "eng")][string]$Voice = "auto",
    [switch]$Loose,
    [switch]$Uninstall,
    [string]$Source = ""
)
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($Source -eq "") { $Source = $Here }

$MoviesDb = "zz_soc_cutscenes.db"
$VoiceDb = @{ rus = "zz_soc_cutscenes_voice_rus.db"; eng = "zz_soc_cutscenes_voice_eng.db" }
$Movies = @("dream_rats", "dream_sarcofag", "dream_doctor", "dream_doctor_2")
$Tracks = @("intro_stalker") + $Movies
# optional Full HD movies (SoC Enhanced Edition Cutscenes by neatodev, Nexus mod 1098), installed when the file is next to this script
$HdDb = "zz_soc_cutscenes_hd.db"
$HdMovies = @("intro_stalker", "dream_rats", "dream_sarcofag", "dream_doctor", "dream_doctor_2", "final_blind", "final_gold", "final_to_monolith", "final_apocal", "final_immortal", "final_peace")

# every file the pack puts under gamedata\ (used by -Loose and by -Uninstall)
function Get-OwnFiles {
    $l = @()
    foreach ($m in $Movies) { $l += "textures\intro\$m.ogm" }
    foreach ($t in $Tracks) { foreach ($s in @("", "_l", "_r")) { $l += "sounds\characters_voice\scenario\video\$t$s.ogg" } }
    $l += "sounds\characters_voice\scenario\osoznanie\teleport_osoznanie.ogg"
    foreach ($m in $HdMovies) { $l += "textures\intro_hd\$m.ogm" }
    return $l
}

function Test-GameDir([string]$d) {
    return (Test-Path -LiteralPath (Join-Path $d "fsgame.ltx")) -and (Test-Path -LiteralPath (Join-Path $d "addons") -PathType Container)
}

# Accepts the game folder, the install folder (even a nested "X-Ray Multiplayer Extension\X-Ray Multiplayer Extension"), the addons
# folder or the coop.addon file; returns the "game" folder or $null.
function Resolve-GamePath([string]$p) {
    if (-not $p) { return $null }
    $p = $p.Trim().Trim('"').Trim()
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    $it = Get-Item -LiteralPath $p
    if (-not $it.PSIsContainer) { $p = $it.DirectoryName }
    $cands = @($p, (Split-Path -Parent $p), (Join-Path $p "game"), (Join-Path $p "X-Ray Multiplayer Extension\game"))
    foreach ($c in $cands) {
        if ($c -and (Test-Path -LiteralPath $c -PathType Container) -and (Test-GameDir $c)) { return (Resolve-Path -LiteralPath $c).Path }
    }
    return $null
}

function Find-Game {
    $roots = @($Here, (Join-Path $Here ".."))
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        if ($d.DriveType -ne 'Fixed' -or -not $d.IsReady) { continue }
        foreach ($sub in @("", "Games\", "Program Files\", "Program Files (x86)\")) {
            $roots += ($d.RootDirectory.FullName + $sub + "X-Ray Multiplayer Extension")
        }
    }
    foreach ($r in $roots) { $g = Resolve-GamePath $r; if ($g) { return $g } }
    Write-Host "The xrMPE folder was not found automatically. / Папка xrMPE не найдена автоматически."
    Write-Host "Paste the path of the 'X-Ray Multiplayer Extension' folder (or its 'game' folder, or coop.addon). / Вставьте путь к папке 'X-Ray Multiplayer Extension' (или к её папке 'game', или к coop.addon)."
    $p = Read-Host "Path / Путь"
    $g = Resolve-GamePath $p
    if (-not $g) { throw "xrMPE game folder not found at: $p / папка игры xrMPE не найдена по пути: $p" }
    return $g
}

# voice language: coop_settings.ltx [client] voice_language, else the launcher language (config.json), else the Windows language
function Get-AutoVoice([string]$game) {
    try {
        $ltx = Join-Path $game "_appdata_\coop_settings.ltx"
        if (Test-Path -LiteralPath $ltx) {
            $in = $false
            foreach ($line in [System.IO.File]::ReadAllLines($ltx)) {
                $t = $line.Trim()
                if ($t -match '^\[(.+)\]') { $in = ($Matches[1].Trim().ToLower() -eq "client"); continue }
                if ($in -and $t -match '^voice_language\s*=\s*(\w+)') {
                    $v = $Matches[1].ToLower()
                    if ($v -eq "rus" -or $v -eq "eng") { return $v }
                }
            }
        }
    } catch {}
    try {
        $cfg = Join-Path (Split-Path -Parent $game) "config.json"
        if (Test-Path -LiteralPath $cfg) {
            $j = Get-Content -LiteralPath $cfg -Raw | ConvertFrom-Json
            if ($j.language) { if ($j.language.ToString().ToLower().StartsWith("ru")) { return "rus" } else { return "eng" } }
        }
    } catch {}
    try { if ((Get-Culture).TwoLetterISOLanguageName -eq "ru") { return "rus" } } catch {}
    return "eng"
}

# Reads the file list of a db made by tools\pack.py (raw entries) and writes every file below $dest.
function Expand-Db([string]$db, [string]$dest) {
    $fs = [System.IO.File]::Open($db, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        $br = New-Object System.IO.BinaryReader($fs)
        $idx = $null
        $pos = [long]0
        while ($pos + 8 -le $fs.Length) {
            $fs.Position = $pos
            $cid = $br.ReadUInt32(); $csz = $br.ReadUInt32()
            if (($cid -band 0x7fffffff) -eq 1) {
                if ($cid -band 0x80000000) { throw "$db has a compressed index (not made by this pack) / в $db сжатый индекс" }
                $idx = $br.ReadBytes([int]$csz)
                break
            }
            $pos += 8 + [long]$csz
        }
        if ($null -eq $idx) { throw "$db has no file index / в $db нет индекса файлов" }
        $count = 0
        $i = 0
        while ($i + 18 -le $idx.Length) {
            $bs = [int][BitConverter]::ToUInt16($idx, $i)
            $rs = [long][BitConverter]::ToUInt32($idx, $i + 2)
            $cs = [long][BitConverter]::ToUInt32($idx, $i + 6)
            $name = [System.Text.Encoding]::ASCII.GetString($idx, $i + 14, $bs - 16)
            $ptr = [long][BitConverter]::ToUInt32($idx, $i + $bs - 2)
            $i += $bs + 2
            if ($name.EndsWith("\")) { continue }
            if ($rs -ne $cs) { throw "$db entry $name is compressed / запись $name сжата" }
            $target = Join-Path $dest $name
            $dir = Split-Path -Parent $target
            if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            $part = $target + ".part"
            $out = [System.IO.File]::Open($part, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            try {
                $fs.Position = $ptr
                $left = $cs
                $buf = New-Object byte[] 4194304
                while ($left -gt 0) {
                    $n = $fs.Read($buf, 0, [int][Math]::Min([long]$buf.Length, $left))
                    if ($n -le 0) { throw "$db is truncated / $db обрезан" }
                    $out.Write($buf, 0, $n)
                    $left -= $n
                }
            } finally { $out.Close() }
            Move-Item -LiteralPath $part -Destination $target -Force
            $count++
        }
        return $count
    } finally { $fs.Close() }
}

function Remove-EmptyDirs([string]$root) {
    if (-not (Test-Path -LiteralPath $root)) { return }
    foreach ($d in (Get-ChildItem -LiteralPath $root -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending)) {
        if (-not (Get-ChildItem -LiteralPath $d.FullName -Force)) { Remove-Item -LiteralPath $d.FullName -Force }
    }
    if (-not (Get-ChildItem -LiteralPath $root -Force)) { Remove-Item -LiteralPath $root -Force }
}

function Remove-Pack([string]$game) {
    $removed = 0
    $pat = Join-Path $game "patches"
    foreach ($n in @($MoviesDb, $VoiceDb.rus, $VoiceDb.eng, $HdDb)) {
        $f = Join-Path $pat $n
        if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force; $removed++; Write-Host "Removed / Удалено: patches\$n" }
    }
    $gd = Join-Path $game "gamedata"
    foreach ($rel in (Get-OwnFiles)) {
        $f = Join-Path $gd $rel
        if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force; $removed++; Write-Host "Removed / Удалено: gamedata\$rel" }
    }
    if (Test-Path -LiteralPath $gd) { Remove-EmptyDirs $gd }
    return $removed
}

# ---------------------------------------------------------------------------------------------------------------------------------
if ($Game -eq "") { $Game = Find-Game }
else {
    $g = Resolve-GamePath $Game
    if (-not $g) { throw "xrMPE game folder not found at: $Game / папка игры xrMPE не найдена по пути: $Game" }
    $Game = $g
}
Write-Host "xrMPE game folder / папка игры: $Game"

try {
    if ($Uninstall) {
        $n = Remove-Pack $Game
        if ($n -eq 0) { Write-Host "Nothing to remove. / Нечего удалять." } else { Write-Host "Cutscene pack removed. / Пакет роликов удалён." }
        return
    }

    $v = $Voice
    if ($v -eq "auto") { $v = Get-AutoVoice $Game }
    $mdb = Join-Path $Source $MoviesDb
    $vdb = Join-Path $Source $VoiceDb[$v]
    foreach ($f in @($mdb, $vdb)) {
        if (-not (Test-Path -LiteralPath $f)) { throw "$(Split-Path -Leaf $f) not found next to install_cutscenes.bat / не найден рядом с install_cutscenes.bat" }
    }
    $hdb = Join-Path $Source $HdDb
    $files = @($mdb, $vdb)
    if (Test-Path -LiteralPath $hdb) { $files += $hdb; Write-Host "Full HD movies found, installing them too. / Найдены ролики Full HD, устанавливаю их тоже." }
    $label = @{ rus = "Russian / русский"; eng = "English / английский" }[$v]
    Write-Host "Movie sound / озвучка роликов: $label   (change with -Voice rus or -Voice eng / сменить: -Voice rus или -Voice eng)"

    $patches = Join-Path $Game "patches"
    $useLoose = [bool]$Loose
    if (-not $useLoose) {
        $ok = $false
        try { $ok = ([System.IO.File]::ReadAllText((Join-Path $Game "fsgame.ltx")) -match '(?m)^\s*\$arch_dir_patches\$\s*=.*patches\\') } catch {}
        if (-not $ok) {
            Write-Host "fsgame.ltx has no patches\ archive folder, using -Loose mode. / В fsgame.ltx нет папки архивов patches\, использую режим -Loose." -ForegroundColor Yellow
            $useLoose = $true
        }
    }

    # start clean so that an old language or the other mode never stays behind
    [void](Remove-Pack $Game)

    if ($useLoose) {
        $gd = Join-Path $Game "gamedata"
        $c1 = Expand-Db $mdb $gd
        $c2 = Expand-Db $vdb $gd
        if (Test-Path -LiteralPath $hdb) { $c2 += Expand-Db $hdb $gd }
        Write-Host "Installed $($c1 + $c2) files into gamedata\ (loose mode). / Установлено файлов в gamedata\: $($c1 + $c2) (режим -Loose)."
    } else {
        if (-not (Test-Path -LiteralPath $patches)) { New-Item -ItemType Directory -Force -Path $patches | Out-Null }
        foreach ($f in $files) {
            $name = Split-Path -Leaf $f
            $dst = Join-Path $patches $name
            Copy-Item -LiteralPath $f -Destination ($dst + ".part") -Force
            Move-Item -LiteralPath ($dst + ".part") -Destination $dst -Force
            $a = (Get-Item -LiteralPath $f).Length; $b = (Get-Item -LiteralPath $dst).Length
            if ($a -ne $b) { throw "Copy of $name is incomplete / копия $name неполная" }
            Write-Host ("Installed / Установлено: patches\{0} ({1:N1} MB)" -f $name, ($b / 1MB))
        }
    }
    Write-Host ""
    Write-Host "Done. Start a new game: the original intro movie and the dream movies now play with their sound. Every player who wants to see the movies installs this pack."
    Write-Host "Готово. Начните новую игру: оригинальный вступительный ролик и ролики-сны теперь показываются со звуком. Пакет ставит каждый игрок, который хочет видеть ролики."
} catch {
    Write-Host ""
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Close the game AND the xrMPE launcher, then run install_cutscenes.bat again. If it still fails, right-click it > Run as administrator." -ForegroundColor Red
    Write-Host "Ошибка. Закройте игру И лаунчер xrMPE и запустите install_cutscenes.bat снова. Если не помогает: ПКМ > Запуск от имени администратора." -ForegroundColor Red
    exit 1
}
