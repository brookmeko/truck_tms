#Requires -RunAsAdministrator
# Truck TMS installer, step 1 of 2: turn on WSL2, install Docker Desktop and Git, keep the PC awake.
$ErrorActionPreference = 'Stop'
Write-Host '== Truck TMS - Step 1: prepare Windows ==' -ForegroundColor Cyan

$os = Get-CimInstance Win32_OperatingSystem
if ([int]$os.BuildNumber -lt 19045) {
	throw "Windows 10 22H2 (build 19045) or Windows 11 is needed; this PC has build $($os.BuildNumber). Run Windows Update first."
}
$cs = Get-CimInstance Win32_ComputerSystem
$ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB)
Write-Host "Windows build $($os.BuildNumber), $ramGB GB RAM"
if ($ramGB -lt 8) { Write-Warning "8 GB RAM is the minimum; with $ramGB GB the system will be slow." }

$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
if (-not $cpu.VirtualizationFirmwareEnabled -and -not $cs.HypervisorPresent) {
	throw 'Virtualization is turned off in the BIOS. Restart into the BIOS, turn on Intel VT-x or AMD SVM, then run this again.'
}
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
	throw 'winget is missing. Install "App Installer" from the Microsoft Store, then run this again.'
}

Write-Host "`n[1/4] Turning on WSL2..." -ForegroundColor Cyan
wsl --install --no-distribution
wsl --update

Write-Host "`n[2/4] Limiting Linux memory so Windows stays usable..." -ForegroundColor Cyan
$wslcfg = Join-Path $env:USERPROFILE '.wslconfig'
if (Test-Path $wslcfg) {
	Write-Host "Keeping your existing $wslcfg"
} else {
	if ($ramGB -ge 16) { $mem = 10 } elseif ($ramGB -ge 12) { $mem = 7 } else { $mem = 5 }
	[IO.File]::WriteAllText($wslcfg, "[wsl2]`r`nmemory=${mem}GB`r`nswap=4GB`r`n")
	Write-Host "Linux may use up to $mem GB"
}

Write-Host "`n[3/4] Installing Docker Desktop and Git (10-20 minutes)..." -ForegroundColor Cyan
winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements

Write-Host "`n[4/4] Keeping the PC awake when plugged in..." -ForegroundColor Cyan
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

Write-Host "`nStep 1 is done." -ForegroundColor Green
Write-Host 'After the restart: open Docker Desktop from the Start menu, accept the terms, skip sign-in,'
Write-Host 'wait until it shows "Engine running", then run 2-Install-Truck-TMS.bat'
$answer = Read-Host 'Restart the computer now? (Y/N)'
if ($answer -match '^[Yy]') { Restart-Computer }
