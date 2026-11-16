TRUCK TMS - INSTALL ON ONE WINDOWS COMPUTER
===========================================

Truck TMS will run on this computer only (http://localhost:8080).
Other computers cannot open it.

You need: Windows 10 22H2 or Windows 11, 8 GB RAM (16 GB better),
60 GB free disk, internet during the install, a Windows administrator
login, and a read-only GitHub token for the truck_tms repository.

STEP 1  (about 20 minutes)
  Right-click  1-Prepare-Windows.bat  ->  Run as administrator.
  It turns on WSL2, installs Docker Desktop and Git, and keeps the PC awake.
  Restart when it asks.

AFTER THE RESTART
  Open Docker Desktop from the Start menu, accept the terms, skip sign-in,
  and wait until it shows "Engine running".

STEP 2  (about 1 hour, mostly waiting)
  Double-click  2-Install-Truck-TMS.bat  (normal, NOT as administrator).
  It asks for the GitHub token and an Administrator password, then builds
  and starts Truck TMS and puts icons on the desktop.

STEP 3  (10 minutes)
  The browser opens Truck TMS. Log in as Administrator and complete the wizard:
    Country Ethiopia, Time Zone Africa/Addis_Ababa, Currency ETB,
    Financial year 2026-07-08 to 2027-07-07.
  Then double-click  "Finish Truck TMS Setup"  on the desktop (once).
  Then open Transport Settings and choose the bank account.

DESKTOP ICONS
  Truck TMS          open the system in the browser
  Start Truck TMS    start it (also happens by itself when you sign in to Windows)
  Stop Truck TMS     stop it (data is kept)
  Backup Truck TMS   save a backup to C:\TruckTMS\backups (and to a USB drive if you want)

UPDATE TO NEW CODE FROM GITHUB
  In PowerShell:  powershell -ExecutionPolicy Bypass -File C:\TruckTMS\scripts\update.ps1

Everything is installed in C:\TruckTMS. Do not delete that folder.
