# Stop Truck TMS (data is kept).
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
Wait-Docker
Tms stop
Assert-Ok 'Stopping Truck TMS'
Write-Host 'Truck TMS is stopped.' -ForegroundColor Green
