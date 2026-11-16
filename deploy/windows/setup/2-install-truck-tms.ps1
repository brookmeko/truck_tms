# Truck TMS installer, step 2 of 2: build Truck TMS, start it, create the site, add desktop icons.
# Run as the normal user (not as administrator), after step 1 and a restart.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $PSScriptRoot
. (Join-Path $here 'scripts\common.ps1')
$fd = Join-Path $Root 'frappe_docker'

Write-Host '== Truck TMS - Step 2: install Truck TMS ==' -ForegroundColor Cyan
if (Test-Path (Join-Path $fd 'compose.custom.yaml')) {
	throw "Truck TMS is already installed in $Root. Use the desktop icons, or scripts\update.ps1 to update."
}

# Git was installed in step 1: make sure this window can find it
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not installed. Run step 1 again.' }
Wait-Docker

# ----- questions -------------------------------------------------------------
Write-Host "`nA few questions (press Enter to accept the value in brackets):"
$repo = Read-Host 'GitHub repository [brookmeko/truck_tms]'
if (-not $repo) { $repo = 'brookmeko/truck_tms' }
$branch = Read-Host 'Branch [version-16]'
if (-not $branch) { $branch = 'version-16' }
$sec = Read-Host 'GitHub token, read-only (typing is hidden)' -AsSecureString
$token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
if (-not $token) { throw 'A GitHub token is needed to download the private truck_tms repository.' }
do {
	$p1 = Read-Host 'Choose the Administrator password for Truck TMS (at least 8 characters)' -AsSecureString
	$p2 = Read-Host 'Type it again' -AsSecureString
	$admin = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p1))
	$again = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p2))
	if ($admin -ne $again) { Write-Warning 'The two passwords are different. Try again.' }
	elseif ($admin.Length -lt 8) { Write-Warning 'Use at least 8 characters.' }
} until ($admin -eq $again -and $admin.Length -ge 8)
$dbPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })

# ----- 1. get frappe_docker --------------------------------------------------
Write-Host "`n[1/6] Downloading frappe_docker..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $Root | Out-Null
if (-not (Test-Path $fd)) {
	git clone -c core.autocrlf=false --depth 1 https://github.com/frappe/frappe_docker $fd
	Assert-Ok 'Downloading frappe_docker'
}
Write-TextFile (Join-Path $Root 'install.json') (@{ repo = $repo; branch = $branch; installed = (Get-Date -Format s) } | ConvertTo-Json)

# ----- 2. build the image ----------------------------------------------------
Write-Host "`n[2/6] Building Truck TMS (ERPNext + HRMS + truck_tms). This takes 20-60 minutes..." -ForegroundColor Cyan
$apps = Join-Path $fd 'apps.json'
Write-TextFile $apps (@"
[
  { "url": "https://github.com/frappe/erpnext", "branch": "version-16" },
  { "url": "https://github.com/frappe/hrms", "branch": "version-16" },
  { "url": "https://$token@github.com/$repo", "branch": "$branch" }
]
"@)
Push-Location $fd
try {
	docker build --no-cache --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe --build-arg=FRAPPE_BRANCH=version-16 --secret "id=apps_json,src=$apps" --tag=truck-tms:1.0.0 --file=images/layered/Containerfile .
	Assert-Ok 'Building the image'
} finally {
	Remove-Item -Force $apps -ErrorAction SilentlyContinue   # the token is not kept on disk
	Pop-Location
}

# ----- 3. settings + compose file --------------------------------------------
Write-Host "`n[3/6] Writing the settings..." -ForegroundColor Cyan
$settings = [ordered]@{
	CUSTOM_IMAGE = 'truck-tms'
	CUSTOM_TAG = '1.0.0'
	PULL_POLICY = 'missing'
	DB_PASSWORD = $dbPassword
	HTTP_PUBLISH_PORT = '127.0.0.1:8080'   # this computer only
	FRAPPE_SITE_NAME_HEADER = $Site
}
$lines = Get-Content (Join-Path $fd 'example.env')
foreach ($key in $settings.Keys) {
	$found = $false
	$lines = $lines | ForEach-Object { if ($_ -match "^#?\s*$key=") { $found = $true; "$key=$($settings[$key])" } else { $_ } }
	if (-not $found) { $lines += "$key=$($settings[$key])" }
}
Write-TextFile (Join-Path $fd 'custom.env') (($lines -join "`n") + "`n")
Push-Location $fd
try {
	docker compose --env-file custom.env -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml config --output compose.custom.yaml
	Assert-Ok 'Writing the compose file'
} finally { Pop-Location }

# ----- 4. start --------------------------------------------------------------
Write-Host "`n[4/6] Starting the containers..." -ForegroundColor Cyan
Tms up -d
Assert-Ok 'Starting the containers'
Write-Host 'Waiting for the database...'
$until = (Get-Date).AddMinutes(5)
do {
	Start-Sleep -Seconds 5
	$db = Get-ContainerValue 'truck-tms-db-1' '{{.State.Health.Status}}'
	$conf = Get-ContainerValue 'truck-tms-configurator-1' '{{.State.Status}}'
} until (($db -eq 'healthy' -and $conf -eq 'exited') -or (Get-Date) -gt $until)
if ($db -ne 'healthy') { throw 'The database did not start. Run:  docker compose -p truck-tms logs db' }
$ErrorActionPreference = 'Continue'
$published = "$(docker port truck-tms-frontend-1 2>$null)"
$ErrorActionPreference = 'Stop'
if ($published -and $published -notmatch '127\.0\.0\.1:8080') {
	Write-Warning "Truck TMS is published as '$published', which other computers may reach. Ask for help before using it."
}

# ----- 5. create the site ----------------------------------------------------
Write-Host "`n[5/6] Creating the Truck TMS site (5-10 minutes)..." -ForegroundColor Cyan
Tms exec -T backend bench new-site $Site --mariadb-user-host-login-scope=% --db-root-password $dbPassword --admin-password $admin --install-app erpnext --install-app hrms --install-app truck_tms
Assert-Ok 'Creating the site'
Tms exec -T backend bench --site $Site enable-scheduler
Assert-Ok 'Turning on the scheduler'
Tms exec -T backend bench --site $Site migrate
Assert-Ok 'Migrate'

# ----- 6. icons + start at sign-in --------------------------------------------
Write-Host "`n[6/6] Adding desktop icons..." -ForegroundColor Cyan
$scripts = Join-Path $Root 'scripts'
New-Item -ItemType Directory -Force -Path $scripts | Out-Null
Copy-Item -Force (Join-Path $here 'scripts\*.ps1') $scripts
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
function New-Shortcut([string]$Name, [string]$Script, [string]$Icon) {
	$lnk = $shell.CreateShortcut((Join-Path $desktop "$Name.lnk"))
	$lnk.TargetPath = 'powershell.exe'
	$lnk.Arguments = "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$scripts\$Script`""
	$lnk.WorkingDirectory = $scripts
	$lnk.IconLocation = $Icon
	$lnk.Save()
}
Write-TextFile (Join-Path $desktop 'Truck TMS.url') "[InternetShortcut]`r`nURL=$Url`r`n"
New-Shortcut 'Start Truck TMS' 'start.ps1' 'shell32.dll,137'
New-Shortcut 'Stop Truck TMS' 'stop.ps1' 'shell32.dll,131'
New-Shortcut 'Backup Truck TMS' 'backup.ps1' 'shell32.dll,7'
New-Shortcut 'Finish Truck TMS Setup' 'finish-setup.ps1' 'shell32.dll,144'
try {
	$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scripts\start.ps1`" -Quiet"
	$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
	Register-ScheduledTask -TaskName 'Truck TMS Autostart' -Action $action -Trigger $trigger -Force | Out-Null
	Write-Host 'Truck TMS will start by itself when you sign in to Windows.'
} catch {
	Write-Warning 'Could not set up automatic start; use the Start Truck TMS icon after each restart.'
}

Write-Host "`nTruck TMS is installed." -ForegroundColor Green
Write-Host "Open: $Url   (only on this computer)"
Write-Host 'Log in as Administrator with the password you chose, then complete the setup wizard:'
Write-Host '  Country Ethiopia, Time Zone Africa/Addis_Ababa, Currency ETB, year 2026-07-08 to 2027-07-07.'
Write-Host 'When the wizard is done, double-click "Finish Truck TMS Setup" on the desktop (once).' -ForegroundColor Yellow
Start-Process $Url
