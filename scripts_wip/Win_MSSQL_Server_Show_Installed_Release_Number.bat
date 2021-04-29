echo OFF
cls

:: Check for MS SQL Server Versions

set CURRENT_VERSION=nul
echo.
FOR /F "tokens=3 skip=2" %%i IN ('REG QUERY "HKLM\SOFTWARE\Microsoft\MSSQLServer\MSSQLServer\CurrentVersion" /v CurrentVersion 2^>nul') DO set CURRENT_VERSION=%%i

if defined CURRENT_VERSION (
	:: MS SQL Server 2019 Versions
	if %CURRENT_VERSION% equ 15.0.2000.5 set SQL_NAME=Microsoft SQL Server 2019
	:: MS SQL Server 2017 Versions
	if %CURRENT_VERSION% equ 14.0.1000.169 set SQL_NAME=Microsoft SQL Server 2017
	:: MS SQL Server 2016 Versions
	if %CURRENT_VERSION% equ 13.0.5026.0 set SQL_NAME=Microsoft SQL Server 2016 SP2
	if %CURRENT_VERSION% equ 13.0.4001.0 set SQL_NAME=Microsoft SQL Server 2016 SP1
	if %CURRENT_VERSION% equ 13.0.1601.5 set SQL_NAME=Microsoft SQL Server 2016
	:: MS SQL Server 2014 Versions
	if %CURRENT_VERSION% equ 12.0.6024.1 set SQL_NAME=Microsoft SQL Server 2014 SP3
	if %CURRENT_VERSION% equ 12.0.5000.0 set SQL_NAME=Microsoft SQL Server 2014 SP2
	if %CURRENT_VERSION% equ 12.0.4100.1 set SQL_NAME=Microsoft SQL Server 2014 SP1
	if %CURRENT_VERSION% equ 12.0.2000.8 set SQL_NAME=Microsoft SQL Server 2014
	:: MS SQL Server 2012 Versions
	if %CURRENT_VERSION% equ 11.0.7001.0 set SQL_NAME=Microsoft SQL Server 2012 SP4
	if %CURRENT_VERSION% equ 11.0.6020.0 set SQL_NAME=Microsoft SQL Server 2012 SP3
	if %CURRENT_VERSION% equ 11.0.5058.0 set SQL_NAME=Microsoft SQL Server 2012 SP2
	if %CURRENT_VERSION% equ 11.0.3000.0 set SQL_NAME=Microsoft SQL Server 2012 SP1
	if %CURRENT_VERSION% equ 11.0.2100.60 set SQL_NAME=Microsoft SQL Server 2012
	:: MS SQL Server 2008 R2 Versions
	if %CURRENT_VERSION% equ 10.50.6000.34 set SQL_NAME=Microsoft SQL Server 2008 R2 SP3
	if %CURRENT_VERSION% equ 10.50.4000.0 set SQL_NAME=Microsoft SQL Server 2008 R2 SP2
	if %CURRENT_VERSION% equ 10.50.2500.0 set SQL_NAME=Microsoft SQL Server 2008 R2 SP1
	if %CURRENT_VERSION% equ 10.50.1600.1 set SQL_NAME=Microsoft SQL Server 2008 R2
	:: MS SQL Server 2008 Versions
	if %CURRENT_VERSION% equ 10.0.6000.29 set SQL_NAME=Microsoft SQL Server 2008 SP4
	if %CURRENT_VERSION% equ 10.0.5000.0 set SQL_NAME=Microsoft SQL Server 2008 SP3
	if %CURRENT_VERSION% equ 10.0.4000.0 set SQL_NAME=Microsoft SQL Server 2008 SP2
	if %CURRENT_VERSION% equ 10.0.2531.0 set SQL_NAME=Microsoft SQL Server 2008 SP1
	if %CURRENT_VERSION% equ 10.0.1600.22 set SQL_NAME=Microsoft SQL Server 2008
)

if %CURRENT_VERSION% equ nul (
	echo No Microsoft SQL Server found/installed!
) else (
	echo Installed Microsoft SQL Server Release:
	echo %SQL_NAME% [%CURRENT_VERSION%]
)

:: Check for MS SQL Server Express Versions

set CURRENT_VERSION=nul
echo.
FOR /F "tokens=3 skip=2" %%i IN ('REG QUERY "HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\SQLEXPRESS\MSSQLServer\CurrentVersion" /v CurrentVersion 2^>nul') DO set CURRENT_VERSION=%%i

if defined CURRENT_VERSION (
	:: MS SQL Server 2017 Express Versions
	if %CURRENT_VERSION% equ 14.0.1000.169 set SQL_NAME=Microsoft SQL Server 2017 Express
	:: MS SQL Server 2016 Express Versions
	if %CURRENT_VERSION% equ 13.0.5026.0 set SQL_NAME=Microsoft SQL Server 2016 Express SP2
	if %CURRENT_VERSION% equ 13.0.4001.0 set SQL_NAME=Microsoft SQL Server 2016 Express SP1
	if %CURRENT_VERSION% equ 13.0.1601.5 set SQL_NAME=Microsoft SQL Server 2016 Express
	:: MS SQL Server 2014 Express Versions
	if %CURRENT_VERSION% equ 12.0.6024.1 set SQL_NAME=Microsoft SQL Server 2014 Express SP3
	if %CURRENT_VERSION% equ 12.0.5000.0 set SQL_NAME=Microsoft SQL Server 2014 Express SP2
	if %CURRENT_VERSION% equ 12.0.4100.1 set SQL_NAME=Microsoft SQL Server 2014 Express SP1
	if %CURRENT_VERSION% equ 12.0.2000.8 set SQL_NAME=Microsoft SQL Server 2014 Express
	:: MS SQL Server 2012 Express Versions
	if %CURRENT_VERSION% equ 11.0.7001.0 set SQL_NAME=Microsoft SQL Server 2012 Express SP4
	if %CURRENT_VERSION% equ 11.0.6020.0 set SQL_NAME=Microsoft SQL Server 2012 Express SP3
	if %CURRENT_VERSION% equ 11.0.5058.0 set SQL_NAME=Microsoft SQL Server 2012 Express SP2
	if %CURRENT_VERSION% equ 11.0.3000.0 set SQL_NAME=Microsoft SQL Server 2012 Express SP1
	if %CURRENT_VERSION% equ 11.0.2100.60 set SQL_NAME=Microsoft SQL Server 2012 Express
	:: MS SQL Server 2008 R2 Express Versions
	if %CURRENT_VERSION% equ 10.50.6000.34 set SQL_NAME=Microsoft SQL Server 2008 R2 Express SP3
	if %CURRENT_VERSION% equ 10.50.4000.0 set SQL_NAME=Microsoft SQL Server 2008 R2 Express SP2
	if %CURRENT_VERSION% equ 10.50.2500.0 set SQL_NAME=Microsoft SQL Server 2008 R2 Express SP1
	if %CURRENT_VERSION% equ 10.50.1600.1 set SQL_NAME=Microsoft SQL Server 2008 R2 Express
	:: MS SQL Server 2008 Express Versions
	if %CURRENT_VERSION% equ 10.0.6000.29 set SQL_NAME=Microsoft SQL Server 2008 Express SP4
	if %CURRENT_VERSION% equ 10.0.5000.0 set SQL_NAME=Microsoft SQL Server 2008 Express SP3
	if %CURRENT_VERSION% equ 10.0.4000.0 set SQL_NAME=Microsoft SQL Server 2008 Express SP2
	if %CURRENT_VERSION% equ 10.0.2531.0 set SQL_NAME=Microsoft SQL Server 2008 Express SP1
	if %CURRENT_VERSION% equ 10.0.1600.22 set SQL_NAME=Microsoft SQL Server 2008 Express
)

if %CURRENT_VERSION% equ nul (
	echo No Microsoft SQL Server Express found/installed!
) else (
	echo Installed Microsoft SQL Server Express Release:
	echo %SQL_NAME% [%CURRENT_VERSION%]
)
echo.