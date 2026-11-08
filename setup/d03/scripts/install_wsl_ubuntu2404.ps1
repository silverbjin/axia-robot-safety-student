#Requires -Version 5.1
<#
Install WSL2 + Ubuntu 24.04 only. Does not alter other distros or install ROS.
Run in elevated Windows PowerShell (NOT Ubuntu). Re-run after reboot if prompted.
#>
[CmdletBinding()]
param([switch]$SkipWSLUpdate)
$ErrorActionPreference = 'Stop'
function Stop-Setup([string]$why) { Write-Host "[BLOCKED] $why" -ForegroundColor Red; exit 2 }
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core' -and $env:OS -ne 'Windows_NT') { Stop-Setup 'Windows PowerShell is required.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Stop-Setup 'Open PowerShell as Administrator.' }
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
if ($build -lt 19041) { Stop-Setup "Windows build $build is too old for the one-command WSL install (requires >=19041)." }
Write-Host "[CHECK] $($os.Caption) build=$build" -ForegroundColor Cyan
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
if (-not $cpu.VirtualizationFirmwareEnabled) { Write-Warning 'Hardware virtualization may not be enabled. Check BIOS/UEFI if WSL2 fails.' }
Write-Host '[STEP 1] Checking WSL...' -ForegroundColor Cyan
$null = & wsl.exe --status 2>&1
if ($LASTEXITCODE -ne 0) { Write-Warning 'WSL may be missing or reboot is required.' }
Write-Host '[STEP 2] Installing/updating WSL (no other distro removed)...' -ForegroundColor Cyan
& wsl.exe --install --no-distribution
if ($LASTEXITCODE -ne 0) { Write-Warning 'WSL feature enable returned nonzero. A reboot may be required; do not delete existing distros.' }
if (-not $SkipWSLUpdate) {
    & wsl.exe --update
    if ($LASTEXITCODE -ne 0) { Write-Warning 'WSL update failed; verify network/Windows Update and retry.' }
}
& wsl.exe --set-default-version 2
if ($LASTEXITCODE -ne 0) { Write-Warning 'Could not set WSL2 as default before reboot.' }
$known = (& wsl.exe --list --quiet 2>$null) -join "`n"
if ($known -match 'Ubuntu-24\.04') {
    Write-Host '[SKIP] Ubuntu-24.04 already registered. Existing data preserved.' -ForegroundColor Yellow
} else {
    Write-Host '[STEP 3] Installing Ubuntu-24.04...' -ForegroundColor Cyan
    & wsl.exe --install -d Ubuntu-24.04
    if ($LASTEXITCODE -ne 0) { Write-Warning 'If installation requested a restart, reboot Windows and rerun this script.' }
}
Write-Host '[STEP 4] Verify version and initialize Linux user:' -ForegroundColor Cyan
& wsl.exe --list --verbose
Write-Host 'If prompted: RESTART Windows; launch Ubuntu-24.04 and create your Linux username/password.' -ForegroundColor Yellow
Write-Host 'Then run scripts/install_ubuntu2404_jazzy_harmonic.sh INSIDE Ubuntu (not PowerShell).'