# Shared helpers for the Truck TMS scripts (one-computer install).
$Root = 'C:\TruckTMS'
$Compose = Join-Path $Root 'frappe_docker\compose.custom.yaml'
$Site = 'tms.local'
$Url = 'http://localhost:8080/desk'

function Tms {
	# docker compose for the Truck TMS project, e.g.  Tms ps   Tms up -d
	docker compose -p truck-tms -f $Compose @args
}

function Assert-Ok([string]$What) {
	if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE)." }
}

function Test-Docker {
	# Windows PowerShell 5.1 turns redirected stderr into errors, so relax that here
	$ErrorActionPreference = 'Continue'
	docker info *> $null
	return ($LASTEXITCODE -eq 0)
}

function Get-ContainerValue([string]$Name, [string]$Format) {
	$ErrorActionPreference = 'Continue'
	$value = docker inspect -f $Format $Name 2>$null
	if ($LASTEXITCODE -ne 0) { return '' }
	return "$value".Trim()
}

function Wait-Docker([int]$Minutes = 5) {
	if (Test-Docker) { return }
	if ($LASTEXITCODE -eq 0) { return }
	$exe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
	if (Test-Path $exe) { Start-Process $exe }
	Write-Host 'Waiting for Docker Desktop to start...'
	$until = (Get-Date).AddMinutes($Minutes)
	while ((Get-Date) -lt $until) {
		Start-Sleep -Seconds 5
		if (Test-Docker) { return }
	}
	throw 'Docker Desktop is not running. Open it, accept the terms, wait until it says Engine running, then try again.'
}

function Write-TextFile([string]$Path, [string]$Text) {
	# UTF-8 without BOM: docker and Frappe cannot read files with a BOM
	[IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}
