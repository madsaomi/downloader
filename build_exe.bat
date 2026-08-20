@echo off
title UniDownloader - Build Portable Desktop EXE
color 0a

echo ========================================================
echo         UniDownloader - Building Portable Desktop .EXE
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run start.bat first.
    pause
    exit /b 1
)

.venv\Scripts\pip.exe install pyinstaller pywebview

if exist "%USERPROFILE%\.deno\bin\deno.exe" (
    if not exist "bin\deno.exe" (
        echo [*] Copying deno.exe to bin/ ...
        copy /y "%USERPROFILE%\.deno\bin\deno.exe" "bin\deno.exe" >nul
    )
)

:: Закрываем предыдущие процессы UniDownloader если запущены
taskkill /f /im UniDownloader.exe >nul 2>&1

echo [*] Compiling Native Window UniDownloader.exe (this takes ~1-2 minutes)...
.venv\Scripts\pyinstaller.exe --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --name "UniDownloader" ^
    --add-data "static;static" ^
    --add-data "bin;bin" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops.asyncio" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols.http.h11_impl" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "uvicorn.protocols.websockets.websockets_impl" ^
    --hidden-import "uvicorn.lifespan.on" ^
    --hidden-import "h11" ^
    --hidden-import "yt_dlp" ^
    --hidden-import "yt_dlp.extractor" ^
    --hidden-import "webview" ^
    --hidden-import "webview.platforms.winforms" ^
    --hidden-import "clr_loader" ^
    --hidden-import "pythonnet" ^
    launcher.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  SUCCESS! Native Window App created in dist\UniDownloader.exe
    echo ========================================================
    echo.
) else (
    echo [ERROR] Build failed.
)

pause
