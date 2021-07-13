REM turns off the task icon for news and weather icon for windows 10 build 21H1
REM key switches 0 - on  1 - hides  2  - off
REM reg delete HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Feeds /f removes it completely

reg add HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Feeds /v ShellFeedsTaskbarViewMode /t REG_Dword /d 2 /f
