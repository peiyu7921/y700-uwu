@echo off
chcp 65001 >nul
title elden uwuAOSP - WSL build
cd /d "%~dp0"

echo ============================================================
echo  elden / TB322FC  -  uwuAOSP 17  build (WSL2 Ubuntu-24.04)
echo ============================================================
echo.
echo  Release notes:
echo    - Keep this window open. Closing it kills the build.
echo    - Log: /root/build-YYYYMMDD-HHMMSS.log (inside WSL)
echo    - Artifacts: /root/aosp/out/target/product/elden/
echo.
echo  Starting... (soong analysis takes several minutes, be patient)
echo.

wsl.exe -d Ubuntu-24.04 -u root bash /mnt/d/projects/y700-uwu/scripts/wsl-build.sh
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [OK] Build finished. Artifacts are under /root/aosp/out/target/product/elden/
) else (
    echo [FAILED] exit code %RC%
    echo Check the newest /root/build-*.log inside WSL for details.
)
echo.
pause
