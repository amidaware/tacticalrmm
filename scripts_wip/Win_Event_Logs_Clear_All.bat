@echo off 
for /F %%a IN (?wevtutil el?) DO (wevtutil.exe cl %%a >nul 2>&1) 
IF (%adminTest%)==(Access) goto noAdmin 
for /F "tokens=*" %%G in ('wevtutil.exe el') DO (call :do_clear "%%G") 
echo. 
echo Event Logs have been cleared! 
goto theEnd 
:do_clear 
echo clearing %1 
wevtutil.exe cl %1 
goto :eof 
:noAdmin 
echo You must run this script as an Administrator! 
echo. 
:theEnd 
