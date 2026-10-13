@echo off
setlocal
cd /d "%~dp0"
title Build TestPathManager.exe

echo ==========================================
echo   TestPath Manager - Windows EXE Builder
 echo ==========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set "PY=py"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed or cannot be found on PATH.
        pause
        exit /b 1
    )
    set "PY=python"
)

%PY% -c "import tkinter; import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller. Internet access may be required.
    %PY% -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo [INFO] Building GUI app without console...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name TestPathManager main.py
if errorlevel 1 (
    echo [ERROR] EXE build failed.
    pause
    exit /b 1
)

if not exist "dist\data" mkdir "dist\data"
if not exist "dist\data\paths.txt" copy /y "data\paths.txt" "dist\data\paths.txt" >nul
if not exist "dist\data\accounts.txt" copy /y "data\accounts.txt" "dist\data\accounts.txt" >nul

echo.
echo [OK] EXE: dist\TestPathManager.exe
echo [OK] TXT: dist\data\paths.txt and dist\data\accounts.txt
echo.
echo NOTE: Keep the data folder next to the EXE.
echo NOTE: Build on Windows for a Windows .exe.
pause
endlocal
