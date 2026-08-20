@echo off
title UniDownloader - Build Pure Native Desktop App (.EXE)
color 0a

echo ========================================================
echo       UniDownloader - Building Pure Native .EXE
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run start.bat first.
    pause
    exit /b 1
)

.venv\Scripts\pip.exe install pyinstaller customtkinter pillow

if exist "%USERPROFILE%\.deno\bin\deno.exe" (
    if not exist "bin\deno.exe" (
        echo [*] Copying deno.exe to bin/ ...
        copy /y "%USERPROFILE%\.deno\bin\deno.exe" "bin\deno.exe" >nul
    )
)

taskkill /f /im UniDownloader_Native.exe >nul 2>&1

echo [*] Compiling Pure Native UniDownloader_Native.exe (this takes ~1 minute)...
.venv\Scripts\pyinstaller.exe --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --name "UniDownloader_Native" ^
    --collect-all customtkinter ^
    --add-data "bin;bin" ^
    --hidden-import "yt_dlp" ^
    --hidden-import "yt_dlp.extractor" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    native_app.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  SUCCESS! Pure Native App created in dist\UniDownloader_Native.exe
    echo ========================================================
    echo.
) else (
    echo [ERROR] Build failed.
)

pause
