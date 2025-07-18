@echo off
timeout /t 10 /nobreak >nul

REM Open first URL and wait for it to fully load
start https://www.example1.com

REM Wait longer for first browser to fully load
timeout /t 8 /nobreak >nul

REM Now open second URL
start https://www.example2.com

REM Wait for second browser to load
timeout /t 3 /nobreak >nul

REM Auto-arrange windows (first window left, second window right)
powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{LWIN}+{LEFT}'); Start-Sleep -Milliseconds 1000; [System.Windows.Forms.SendKeys]::SendWait('{LWIN}+{RIGHT}');"
