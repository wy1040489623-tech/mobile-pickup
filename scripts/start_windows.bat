@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title Mobile Pickup

rem Prefer "python" on PATH, then the py launcher. Skip interpreters without ssl:
rem a Python built without _ssl can create a venv but pip cannot reach the index.
set "PY="
python -c "import sys, ssl; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY (
  py -3 -c "import sys, ssl; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  echo Python 3.8 or newer with the ssl module was not found.
  echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH".
  pause
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import ssl" >nul 2>&1 || (
    echo Existing .venv is broken ^(no ssl^). Recreating ...
    rmdir /S /Q .venv
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo First run: creating .venv ...
  %PY% -m venv .venv
  if errorlevel 1 goto :install_fail
  ".venv\Scripts\python.exe" -c "import ssl" || (
    echo The selected Python has no ssl module. Install Python from python.org.
    goto :install_fail
  )
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo Default index failed. Retrying with the Tsinghua mirror ...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  )
  if errorlevel 1 goto :install_fail
  echo ok> ".venv\.deps-ok"
)

rem Replace a running instance if this package started it.
if exist pickup.pid (
  set /p OLDPID=<pickup.pid
  if defined OLDPID taskkill /PID %OLDPID% /F >nul 2>&1
)

set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -u "scripts\pickup_server.py" %* >> pickup.log 2>&1
if errorlevel 1 (
  echo.
  echo Startup failed. Last lines of pickup.log:
  powershell -NoProfile -Command "Get-Content pickup.log -Tail 25"
  pause
)
exit /b 0

:install_fail
echo.
echo Dependency install failed. Check the network, then run:
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
echo Or use the mirror:
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pause
exit /b 1
