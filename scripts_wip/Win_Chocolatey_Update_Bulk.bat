
    ECHO Enter number of clients you're running against as a parameter if you are running against multiple clients. 
    ECHO A random sleep time will be introduced to minimize the chance of being temporarily blacklisted
    ECHO See https://docs.chocolatey.org/en-us/community-repository/community-packages-disclaimer#rate-limiting


IF %1.==. GOTO No1
IF %2.==. GOTO No2

    
GOTO End1

:No1
rem No parameters
  ECHO Running No1: No parameters provided
  cup -y all
GOTO End1

:No2
rem One parameter provided
  ECHO Running No2: One Parameter provided
  
@echo off & setlocal EnableDelayedExpansion

for /L %%a in (1) do (
        call:rand 1 %2
        echo !RAND_NUM!
)
:rand
SET /A RAND_NUM=%RANDOM% * (%2 - %1 + 1) / 32768 + %1
echo RAND_NUM is !RAND_NUM!
Set /A SleepTime=!RAND_NUM! * 60
echo SleepTime is %SleepTime%

timeout /t %SleepTime% /nobreak
ECHO finished waiting
cup -y all

GOTO End1

:End1

rem We've reached the end