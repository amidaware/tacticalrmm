rundll32 printui.dll,PrintUIEntry /ga /n \\CAC-FILE-02\CAC-LAF-TXROOM
rundll32 printui.dll,PrintUIEntry /ga /n \\CAC-FILE-02\CAC-WLF-PTR-01
TIMEOUT 10
net stop spooler
TIMEOUT 10
net start spooler
exit /B