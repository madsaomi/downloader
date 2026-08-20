@echo off
setlocal enabledelayedexpansion
title UniDownloader - Media Downloader
color 0b

echo ========================================================
echo             UniDownloader - Media Downloader
echo ========================================================
echo.

cd /d "%~dp0"

:: 0. Проверяем наличие исходного кода приложения. Если запущен только 1 файл start.bat — скачиваем код с GitHub!
if not exist "backend\app.py" (
    echo [*] Fayly prilozheniya ne naydeny.
    echo [*] Zagruzka aktualnoy versii UniDownloader s GitHub (madsaomi/downloader)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $zip = Join-Path $env:TEMP 'unidownloader_repo.zip'; $dest = (Get-Location).Path; try { (New-Object System.Net.WebClient).DownloadFile('https://github.com/madsaomi/downloader/archive/refs/heads/main.zip', $zip); $tmp = Join-Path $env:TEMP 'unidownloader_tmp'; Expand-Archive -Path $zip -DestinationPath $tmp -Force; $root = Get-ChildItem -Path $tmp | Select-Object -First 1; Copy-Item -Path \"$($root.FullName)\*\" -Destination $dest -Recurse -Force; Remove-Item $zip -Force -ErrorAction SilentlyContinue; Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue; } catch { Write-Host '[!] Oshibka skachivaniya repo s GitHub. Ubedites chto repozitoriy Public.'; }"
)

:: 1. Проверяем готовое виртуальное окружение
if exist ".venv\Scripts\python.exe" (
    goto :START_APP
)

:: 2. Проверяем наличие установленного Python в системе
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Python nayden. Sozdaem virtualnoe okruzhenie...
    python -m venv .venv
    goto :INSTALL_DEPS
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Python launcher nayden. Sozdaem virtualnoe okruzhenie...
    py -m venv .venv
    goto :INSTALL_DEPS
)

:: 3. Если Python не установлен - скачиваем и устанавливаем автоматически
echo.
echo [!] Python ne nayden na etom kompyutere!
echo [*] Avtomaticheskaya zagruzka oficialnogo Python 3.12...
echo [*] Pozhaluysta, podozhdite 1-2 minuty...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $installer = Join-Path $env:TEMP 'python_setup_312.exe'; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe', $installer); Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1' -Wait; Remove-Item $installer -Force -ErrorAction SilentlyContinue"

set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Ne udalos avtomaticheski ustanovit Python.
    echo Pozhaluysta, skachayte Python s https://www.python.org (otmet'te Add to PATH).
    pause
    exit /b 1
)

python -m venv .venv

:INSTALL_DEPS
echo [*] Ustanovka zavisimostey (yt-dlp, fastapi, ffmpeg)...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt

:: 4. Проверяем наличие Deno (нужен для решения YouTube JS-challenge и разблокировки HD-форматов)
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"
where deno >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Ustanovka Deno (dlya YouTube HD/4K formatov)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://deno.land/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.deno\bin;%PATH%"
)

:START_APP
:: Убеждаемся что Deno доступен в PATH
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"
echo.
echo [*] Zapusk UniDownloader na http://localhost:8000 ...
echo [*] Otkryvaem brauzer...
start "" "http://localhost:8000"

.venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-dir static

pause
