Write-Host "Clearing FireFox caches"
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\cache\*" -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\cache\*.*" -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\cache2\entries\*.*" -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\thumbnails\*" -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\cookies.sqlite" -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\webappsstore.sqlite" -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path "C:\Users\*\AppData\Local\Mozilla\Firefox\Profiles\*.default\chromeappsstore.sqlite" -Recurse -Force -EA SilentlyContinue -Verbose
Write-Host "FireFox cache is cleared"
