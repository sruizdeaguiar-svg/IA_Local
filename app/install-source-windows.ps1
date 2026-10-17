param([string]$Destination = "$env:LOCALAPPDATA\Programs\IA Local", [string]$DataDirectory = "$env:LOCALAPPDATA\IA-Local")
$ErrorActionPreference = "Stop"
# Requires a user-installed Python 3.12+. No execution-policy changes or elevation.
python (Join-Path $PSScriptRoot "app\install_portable_source.py") --destination $Destination --data $DataDirectory --desktop
if ($LASTEXITCODE -ne 0) { throw "Installation failed. Review the Python output." }
