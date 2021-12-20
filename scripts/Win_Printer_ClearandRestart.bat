@echo off

sc stop spooler

ping 127.0.0.1 -n 6 > nul

del C:\Windows\System32\spool\printers\* /Q /F /S

sc start spooler
