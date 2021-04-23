@echo off
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j

if "%version%" == "6.1" (
  rem Windows 7
  netsh interface ip set address "Local Area Connection" dhcp 
  netsh interface ip set dns "Local Area Connection" dhcp
)
if "%version%" == "10.0" (
  rem Windows 10
  netsh interface ip set address Ethernet dhcp
  netsh interface ip set dns Ethernet dhcp
)