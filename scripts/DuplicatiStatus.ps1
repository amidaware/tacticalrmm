# This will check Duplicati Backup is running properly over the last 24 hours
################
# Please make sure you have created the 2 files Duplicati_Before.bat and Duplicati_After.bat and saved them in a folder
################ 
# Change the Duplicati backup advanced settings to run the before script and after script you will need their full path
################
# Duplicati_Before.bat should contain the below without the proceeding #:
#
# REM Create Running Status
# EVENTCREATE /T INFORMATION /L APPLICATION /SO Duplicati2 /ID 205 /D "%DUPLICATI__BACKUP_NAME% - Starting Duplicati Backup Job"
################
# Duplicati_After.bat should contain the below without the proceeding #:
#
# REM Create Result Status from Parsed Results
# SET DSTATUS=%DUPLICATI__PARSED_RESULT%
# If %DSTATUS%==Fatal GOTO DSError
# If %DSTATUS%==Error GOTO DSError
# If %DSTATUS%==Unknown GOTO DSWarning
# If %DSTATUS%==Warning GOTO DSWarning
# If %DSTATUS%==Success GOTO DSSuccess
# GOTO END
# :DSError
# EVENTCREATE /T ERROR /L APPLICATION /SO Duplicati2 /ID 202 /D "%DUPLICATI__BACKUP_NAME% - Error running Duplicati Backup Job"
# GOTO END
# :DSWarning
# EVENTCREATE /T WARNING /L APPLICATION /SO Duplicati2 /ID 201 /D "%DUPLICATI__BACKUP_NAME% - Warning running Duplicati Backup Job"
# GOTO END
# :DSSuccess
# EVENTCREATE /T SUCCESS /L APPLICATION /SO Duplicati2 /ID 200 /D "%DUPLICATI__BACKUP_NAME% - Success in running Duplicati Backup Job"
# GOTO END
# :END
# SET DSTATUS=

$ErrorActionPreference= 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)

if (Get-WinEvent -FilterHashtable @{LogName='Application';ID='202';StartTime=$TimeSpan}) 

{
Write-Output "Duplicati Backup Ended with Errors"
Get-WinEvent -FilterHashtable @{LogName='Application';ID='205','201','202';StartTime=$TimeSpan}
exit 1
}


else 

{
Write-Output "Duplicati Backup Is Working Correctly"
Get-WinEvent -FilterHashtable @{LogName='Application';ID='205','200','201'}
exit 0
}


Exit $LASTEXITCODE
