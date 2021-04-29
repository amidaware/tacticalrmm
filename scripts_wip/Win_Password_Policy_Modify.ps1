secedit /export /cfg c:\secpol.cfg
(gc C:\secpol.cfg).replace("PasswordComplexity = 0", "PasswordComplexity = 1") | Out-File C:\secpol.cfg
(gc C:\secpol.cfg).replace("MaximumPasswordAge = 42", "MaximumPasswordAge = 180") | Out-File C:\secpol.cfg
(gc C:\secpol.cfg).replace("PasswordHistorySize = 0", "PasswordHistorySize = 4") | Out-File C:\secpol.cfg
(gc C:\secpol.cfg).replace("MinimumPasswordLength = 0", "MinimumPasswordLength = 8") | Out-File C:\secpol.cfg
secedit /configure /db C:\windows\security\database\mycustomsecdb.sdb /cfg c:\secpol.cfg /areas SECURITYPOLICY
gpupdate
rm -force c:\secpol.cfg -confirm:$false