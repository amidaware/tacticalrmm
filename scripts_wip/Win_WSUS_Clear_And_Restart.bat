net stop wuauserv
net stop cryptSvc
net stop bits
net stop msiserver
timeout 1
Ren C:\Windows\SoftwareDistribution SoftwareDistribution.old
Ren C:\Windows\System32\catroot2 Catroot2.old
timeout 1
net start wuauserv
net start cryptSvc
net start bits
net start msiserver 