# Per-user installation; no elevation. Explicit destination and optional data path.
param([string]$Destination = "$env:LOCALAPPDATA\Programs\IA Local", [string]$DataDirectory = "", [switch]$DesktopShortcut)
$ErrorActionPreference = "Stop"
if (!(Split-Path -IsAbsolute $Destination)) { throw "Choose an absolute application directory." }
$exe = Join-Path $Destination "IA-Local.exe"
if (Test-Path $exe) { throw "An installation exists; choose another directory." }
if ($DataDirectory -and (!(Split-Path -IsAbsolute $DataDirectory) -or $DataDirectory.Contains('"'))) { throw "Choose an absolute data directory without quotes." }
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "IA-Local.exe") -Destination $exe
$shell = New-Object -ComObject WScript.Shell
$locations = @([Environment]::GetFolderPath("Programs"))
if ($DesktopShortcut) { $locations += [Environment]::GetFolderPath("Desktop") }
foreach ($location in $locations) {
    $path = Join-Path $location "IA Local.lnk"
    if (Test-Path $path) { throw "Shortcut exists; it was preserved: $path" }
    $shortcut = $shell.CreateShortcut($path); $shortcut.TargetPath = $exe
    if ($DataDirectory) { $shortcut.Arguments = '--data "' + $DataDirectory + '"' }
    $shortcut.IconLocation = "$exe,0"; $shortcut.WorkingDirectory = $Destination; $shortcut.Save()
}
Write-Output "Installed: $exe. Engines and models are linked separately from the panel."
