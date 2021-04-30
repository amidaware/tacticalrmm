taskkill /F /IM "chrome.exe">nul 2>&1 
set ChromeDataDir=C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data\Default 
set ChromeCache=%ChromeDataDir%\Cache>nul 2>&1   
del /q /s /f "%ChromeCache%\*.*">nul 2>&1     
del /q /f "%ChromeDataDir%\*Cookies*.*">nul 2>&1     
del /q /f "%ChromeDataDir%\*History*.*">nul 2>&1

set ChromeDataDir=C:\Users\%USERNAME%\Local Settings\Application Data\Google\Chrome\User Data\Default 
set ChromeCache=%ChromeDataDir%\Cache>nul 2>&1 
del /q /s /f "%ChromeCache%\*.*">nul 2>&1    
del /q /f "%ChromeDataDir%\*Cookies*.*">nul 2>&1     
del /q /f "%ChromeDataDir%\*History*.*">nul 2>&1     