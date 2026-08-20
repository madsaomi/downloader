@echo off
title UniDownloader - Build Portable EXE
color 0a

echo ========================================================
echo         UniDownloader - Building Portable .EXE
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run start.bat first.
    pause
    exit /b 1
)

if exist "%USERPROFILE%\.deno\bin\deno.exe" (
    if not exist "bin\deno.exe" (
        echo [*] Copying deno.exe to bin/ ...
        copy /y "%USERPROFILE%\.deno\bin\deno.exe" "bin\deno.exe" >nul
    )
)

echo [*] Compiling UniDownloader.exe (this takes ~1 minute)...
.venv\Scripts\pyinstaller.exe --noconfirm --clean ^
    --onefile ^
    --name "UniDownloader" ^
    --add-data "static;static" ^
    --add-data "bin;bin" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "uvicorn.lifespan.on" ^
    --hidden-import "yt_dlp" ^
    --hidden-import "yt_dlp.extractor" ^
    launcher.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  SUCCESS! Portable version created in dist\UniDownloader.exe
    echo ========================================================
    echo.
) else (
    echo [ERROR] Build failed.
)

pause
