REM Print Spooler reset script. Will stop spooler, fix permissions on print folders, clear all files in print queues, and restart spooler service.

REM Stop Print Spooler 
net stop "Spooler"

REM Kill service if its not stopping 
tasklist | find /i "spoolsv.exe" && taskkill /im spoolsv.exe /F && net stop "Spooler"

REM Set Permissions on spool folders
icacls %systemroot%\System32\spool\PRINTERS /grant system:f /inheritance:e
icacls %systemroot%\System32\spool\SERVERS /grant system:f /inheritance:e

REM Clear files in print queue
del /F /Q %systemroot%\System32\spool\PRINTERS\*.*
del /F /Q %systemroot%\System32\spool\SERVERS\*.*

REM Start Print Spooler again
net start "Spooler"