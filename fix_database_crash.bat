@echo off
title StockWatch Database Repair Toolkit
echo ===================================================
echo   StockWatch Database Repair and Port Toolkit
echo ===================================================
echo.
echo Please choose a repair option:
echo.
echo [1] Quick Fix (Free port 3306 and clear lock files)
echo [2] Deep Repair (Complete database reset and re-import database.sql)
echo [3] Exit
echo.
set /p opt="Enter your choice (1, 2, or 3): "

if "%opt%"=="1" goto QUICK
if "%opt%"=="2" goto DEEP
if "%opt%"=="3" goto EXIT
goto EXIT

:QUICK
echo.
echo ===================================================
echo Running Quick Fix...
echo ===================================================
echo.
echo 1. Force closing any stuck MySQL database processes...
taskkill /F /IM mysqld.exe >nul 2>&1
net stop MySQL80 >nul 2>&1
echo Port 3306 is now free!
echo.
echo 2. Deleting stale lock files...
if exist "C:\xampp\mysql\data\mysql.pid" (
    del /f /q "C:\xampp\mysql\data\mysql.pid"
    echo Stale lock files removed.
)
echo.
echo Quick Fix Complete! You can now start XAMPP MySQL.
echo ===================================================
pause
exit

:DEEP
echo.
echo ===================================================
echo WARNING: Running Deep Repair...
echo ===================================================
echo This will reset your database files to a clean state 
echo and import "database.sql" to restore all tables and data.
echo.
echo Please make sure XAMPP Control Panel is CLOSED before proceeding.
echo.
set /p confirm="Do you want to continue? (Y/N): "
if /i "%confirm%" neq "y" goto EXIT
echo.

echo 1. Force closing any active database processes...
taskkill /F /IM mysqld.exe >nul 2>&1
net stop MySQL80 >nul 2>&1
echo Port 3306 is now free.
echo.

echo 2. Wiping and restoring clean database files from backup...
if exist "C:\xampp\mysql\backup" (
    :: Remove all current files
    del /f /s /q "C:\xampp\mysql\data\*" >nul 2>&1
    for /d %%p in ("C:\xampp\mysql\data\*") do rmdir "%%p" /s /q >nul 2>&1
    
    :: Copy clean backup files
    xcopy /e /i /y "C:\xampp\mysql\backup\*" "C:\xampp\mysql\data\" >nul 2>&1
    echo Files restored from backup!
) else (
    echo Error: Backup folder not found! Deep repair aborted.
    pause
    exit
)
echo.

echo 3. Starting MariaDB in background to import database.sql...
start /b "MariaDBTemp" "C:\xampp\mysql\bin\mysqld.exe" --defaults-file="C:\xampp\mysql\bin\my.ini" --standalone >nul 2>&1
echo Waiting 5 seconds for database server to boot...
timeout /t 5 >nul

echo 4. Creating database and importing database.sql...
"C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS inventory_monitoring_system;" >nul 2>&1
if exist "database\database.sql" (
    "C:\xampp\mysql\bin\mysql.exe" -u root inventory_monitoring_system < "database\database.sql"
    echo Schema and sample records imported successfully!
) else (
    echo Warning: database\database.sql not found! Tables were not imported.
)
echo.

echo 5. Stopping background server...
taskkill /F /IM mysqld.exe >nul 2>&1
echo.
echo ===================================================
echo DEEP REPAIR COMPLETE! 
echo You can now open XAMPP and click START next to MySQL.
echo ===================================================
pause
exit

:EXIT
exit
