# Back up the database and files to C:\TruckTMS\backups\<date>, and optionally to another drive.
param([string]$CopyTo = '')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
Wait-Docker
Write-Host 'Making a backup...'
Tms exec -T backend bench --site $Site backup --with-files
Assert-Ok 'Backup'
$dest = Join-Path $Root ('backups\' + (Get-Date -Format 'yyyy-MM-dd_HHmm'))
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Tms cp "backend:/home/frappe/frappe-bench/sites/$Site/private/backups/." $dest
Assert-Ok 'Copying the backup out'
Write-Host "Backup saved in $dest" -ForegroundColor Green
if (-not $CopyTo) {
	$CopyTo = Read-Host 'Also copy to another drive? Type a folder like E:\TruckTMS-Backups, or press Enter to skip'
}
if ($CopyTo) {
	New-Item -ItemType Directory -Force -Path $CopyTo | Out-Null
	Copy-Item -Recurse -Force $dest $CopyTo
	Write-Host "Also copied to $CopyTo" -ForegroundColor Green
}
