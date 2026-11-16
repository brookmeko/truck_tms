# Start Truck TMS and open it in the browser. -Quiet = no browser (used at Windows sign-in).
param([switch]$Quiet)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
Wait-Docker -Minutes 10
Tms up -d
Assert-Ok 'Starting Truck TMS'
if (-not $Quiet) {
	Write-Host 'Truck TMS is starting. The page can take a minute the first time.'
	Start-Sleep -Seconds 5
	Start-Process $Url
}
