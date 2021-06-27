# ACTIVE DIRECTORY AD LIST ENABLED USERS DOMAIN 
Get-ADUser -Filter {Enabled -eq $true} | select Name,Enabled | Export-Csv c:\temp\aduserlist.csv
Get-ADUser -Filter {Enabled -eq $true} | select SamAccountName,Name | Export-Csv c:\temp\aduserlist.csv
