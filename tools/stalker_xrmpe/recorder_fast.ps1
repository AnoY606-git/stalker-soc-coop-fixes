# Full rs_stats panel every 3 s for up to 10 minutes.
Add-Type -AssemblyName System.Drawing
$out = Join-Path $PSScriptRoot "recfast"
New-Item -ItemType Directory -Force $out | Out-Null
$n = 0
while ($n -lt 200) {
    if (-not (Get-Process xrEngine -EA SilentlyContinue | Where-Object { $_.Path -notlike '*dedicated*' })) { break }
    $bmp = New-Object Drawing.Bitmap 720, 900
    $g = [Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen(0, 0, 0, 0, (New-Object Drawing.Size 720, 900))
    $bmp.Save(("{0}\{1:D3}_{2}.png" -f $out, $n, (Get-Date -Format HHmmss)), [Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    $n++
    Start-Sleep -Seconds 3
}
