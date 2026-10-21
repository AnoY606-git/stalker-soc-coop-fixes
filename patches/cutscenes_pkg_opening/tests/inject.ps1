param([int]$ProcId, [string]$Keys = "", [int]$Ms = 1500, [switch]$Click, [int]$X = 400, [int]$Y = 300)
# TEST ONLY: post key / mouse messages straight to one game window (no focus needed). Keys: comma list of vk:scan, e.g. 57:11 (W), A2:1D (left ctrl)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class Inj {
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
}
"@
$p = Get-Process -Id $ProcId -ErrorAction Stop
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { Write-Host "no window handle for $ProcId"; exit 2 }
$ks = @()
foreach ($k in ($Keys -split ",")) { if ($k) { $a = $k -split ":"; $ks += ,@([Convert]::ToInt32($a[0], 16), [Convert]::ToInt32($a[1], 16)) } }
$end = (Get-Date).AddMilliseconds($Ms)
$first = $true
$lp = [IntPtr](($Y -shl 16) -bor $X)
if ($Click) { [void][Inj]::PostMessage($h, 0x200, [IntPtr]0, $lp); Start-Sleep -Milliseconds 150; [void][Inj]::PostMessage($h, 0x200, [IntPtr]0, $lp); Start-Sleep -Milliseconds 150; [void][Inj]::PostMessage($h, 0x201, [IntPtr]1, $lp) }
while ((Get-Date) -lt $end) {
  foreach ($k in $ks) {
    $l = 1 -bor ($k[1] -shl 16)
    if (-not $first) { $l = $l -bor 0x40000000 }
    [void][Inj]::PostMessage($h, 0x100, [IntPtr]$k[0], [IntPtr]$l)
  }
  $first = $false
  Start-Sleep -Milliseconds 40
}
foreach ($k in $ks) {
  $l = 1 -bor ($k[1] -shl 16) -bor 0x40000000 -bor 0x80000000
  [void][Inj]::PostMessage($h, 0x101, [IntPtr]$k[0], [IntPtr]([int]$l))
}
if ($Click) { [void][Inj]::PostMessage($h, 0x202, [IntPtr]0, $lp) }
Write-Host "injected into $ProcId ($($p.MainWindowTitle))"
