rem Changes the default of 50GB of Outlook data files (PST/OST) storage to 100GB

REG ADD "HKEY_CURRENT_USER\Software\Microsoft\Office\16.0\Outlook\PST" /v WarnLargeFileSize /f /t REG_DWORD /d 95000 
REG ADD "HKEY_CURRENT_USER\Software\Microsoft\Office\16.0\Outlook\PST" /v MaxLargeFileSize /f /t REG_DWORD /d 100000 
