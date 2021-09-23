if not exist C:\TEMP\ md C:\TEMP\
cd c:\temp\

cd c:\temp
powershell Invoke-WebRequest https://github.com/duplicati/duplicati/releases/download/v2.0.6.100-2.0.6.100_canary_2021-08-11/duplicati-2.0.6.100_canary_2021-08-11-x64.msi -Outfile duplicati.msi
start /wait msiexec /i duplicati.msi /l*v C:\temp\duplicatiinst.txt /qn
REM Kill Duplicati
taskkill /IM "Duplicati*" /F
"C:\Program Files\Duplicati 2\Duplicati.WindowsService.exe" install
sc start Duplicati
del "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Duplicati 2.lnk"
del "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\Duplicati 2.lnk"
del "C:\Users\Public\Desktop\Duplicati 2.lnk"

(
echo REM Create Running Status
echo EVENTCREATE /T INFORMATION /L APPLICATION /SO Duplicati2 /ID 205 /D "%DUPLICATI__BACKUP_NAME% - Starting Duplicati Backup Job"
)>"C:\Program Files\Duplicati 2\Duplicati_Before.bat"

(
echo REM Create Result Status from Parsed Results
echo SET DSTATUS=%DUPLICATI__PARSED_RESULT%
echo If %DSTATUS%==Fatal GOTO DSError
echo If %DSTATUS%==Error GOTO DSError
echo If %DSTATUS%==Unknown GOTO DSWarning
echo If %DSTATUS%==Warning GOTO DSWarning
echo If %DSTATUS%==Success GOTO DSSuccess
echo GOTO END
echo :DSError
echo EVENTCREATE /T ERROR /L APPLICATION /SO Duplicati2 /ID 202 /D "%DUPLICATI__BACKUP_NAME% - Error running Duplicati Backup Job"
echo GOTO END
echo :DSWarning
echo EVENTCREATE /T WARNING /L APPLICATION /SO Duplicati2 /ID 201 /D "%DUPLICATI__BACKUP_NAME% - Warning running Duplicati Backup Job"
echo GOTO END
echo :DSSuccess
echo EVENTCREATE /T SUCCESS /L APPLICATION /SO Duplicati2 /ID 200 /D "%DUPLICATI__BACKUP_NAME% - Success in running Duplicati Backup Job"
echo GOTO END
echo :END
echo SET DSTATUS=
)>"C:\Program Files\Duplicati 2\Duplicati_After.bat"