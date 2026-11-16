# Update Truck TMS to the latest code on GitHub: backup, build a new image, restart, migrate.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$fd = Join-Path $Root 'frappe_docker'
$envFile = Join-Path $fd 'custom.env'
$cfg = Get-Content (Join-Path $Root 'install.json') -Raw | ConvertFrom-Json
Wait-Docker

Write-Host '1/4 Backup first' -ForegroundColor Cyan
& "$PSScriptRoot\backup.ps1" -CopyTo ''

$current = (Select-String -Path $envFile -Pattern '^CUSTOM_TAG=(.*)$').Matches[0].Groups[1].Value
$tag = Get-Date -Format 'yyyy.MM.dd-HHmm'
Write-Host "2/4 Building new version $tag (current $current), 20-60 minutes" -ForegroundColor Cyan
$sec = Read-Host 'GitHub token (read-only, hidden)' -AsSecureString
$token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$apps = Join-Path $fd 'apps.json'
Write-TextFile $apps (@"
[
  { "url": "https://github.com/frappe/erpnext", "branch": "version-16" },
  { "url": "https://github.com/frappe/hrms", "branch": "version-16" },
  { "url": "https://$token@github.com/$($cfg.repo)", "branch": "$($cfg.branch)" }
]
"@)
Push-Location $fd
try {
	docker build --no-cache --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe --build-arg=FRAPPE_BRANCH=version-16 --secret "id=apps_json,src=$apps" --tag="truck-tms:$tag" --file=images/layered/Containerfile .
	Assert-Ok 'Building the image'
} finally {
	Remove-Item -Force $apps -ErrorAction SilentlyContinue
	Pop-Location
}

Write-Host '3/4 Switching to the new version' -ForegroundColor Cyan
$text = (Get-Content $envFile -Raw) -replace '(?m)^CUSTOM_TAG=.*$', "CUSTOM_TAG=$tag"
Write-TextFile $envFile $text
Push-Location $fd
try {
	docker compose --env-file custom.env -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml config --output compose.custom.yaml
	Assert-Ok 'Writing the compose file'
} finally { Pop-Location }
Tms up -d
Assert-Ok 'Restarting'

Write-Host '4/4 Updating the database' -ForegroundColor Cyan
Start-Sleep -Seconds 20
Tms exec -T backend bench --site $Site migrate
Assert-Ok 'Migrate'
Write-Host "Updated to $tag. The old image ($current) and the backup are kept in case you need to go back." -ForegroundColor Green
