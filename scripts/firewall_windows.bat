@echo off
chcp 65001 >nul
title Mobile Pickup - Firewall

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Administrator permission required. Reopening ...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

netsh advfirewall firewall delete rule name="MobilePickup" >nul 2>&1
netsh advfirewall firewall add rule name="MobilePickup" dir=in action=allow protocol=TCP localport=8000-8010,8443-8452 remoteip=localsubnet profile=private,domain
if errorlevel 1 (
  echo Private/Domain profiles failed. Trying all profiles ...
  netsh advfirewall firewall add rule name="MobilePickup" dir=in action=allow protocol=TCP localport=8000-8010,8443-8452 remoteip=localsubnet profile=any
)

if not errorlevel 1 (
  echo.
  echo Allowed TCP 8000-8010 and 8443-8452 from the local subnet.
  echo If the phone still cannot connect, check that the Wi-Fi network is set to Private.
) else (
  echo.
  echo Failed. Run this file as Administrator.
)
pause
