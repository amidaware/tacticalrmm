@echo off

sc stop spooler

timeout /t 5 /nobreak > NUL

del C:\Windows\System32\spool\printers\* /Q /F /S

sc start spooler