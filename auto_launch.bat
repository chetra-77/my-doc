@echo off
timeout /t 10 /nobreak >nul

REM Open first URL
start "" https://www.example1.com

REM Wait for first browser to fully load
timeout /t 8 /nobreak >nul

REM Press Ctrl+Shift+N to force new window, then navigate to second URL
powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^+n'); Start-Sleep -Milliseconds 2000; [System.Windows.Forms.SendKeys]::SendWait('^l'); Start-Sleep -Milliseconds 500; [System.Windows.Forms.SendKeys]::SendWait('https://www.example2.com'); [System.Windows.Forms.SendKeys]::SendWait('{ENTER}');"

REM Wait a moment for second window to load
timeout /t 5 /nobreak >nul

REM Now arrange windows - Win+Left for first window
powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{TAB}'); Start-Sleep -Milliseconds 500; [System.Windows.Forms.SendKeys]::SendWait('{LWIN}+{LEFT}'); Start-Sleep -Milliseconds 1000;"

REM Win+Right for second window
powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{TAB}'); Start-Sleep -Milliseconds 500; [System.Windows.Forms.SendKeys]::SendWait('{LWIN}+{RIGHT}');"
