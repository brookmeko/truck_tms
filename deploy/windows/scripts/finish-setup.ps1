# Run once after the setup wizard: creates the Truck TMS accounts, cost centers and default lists
# (they need the company the wizard creates).
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
Wait-Docker
Write-Host 'Finishing the Truck TMS setup...'
Tms exec -T backend bench --site $Site migrate
Assert-Ok 'Finishing the setup'
Write-Host 'Done. Next: open Transport Settings and choose the bank account.' -ForegroundColor Green
Read-Host 'Press Enter to close'
