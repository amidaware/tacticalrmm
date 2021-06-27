# GET SMBv2 SERVER STATUS
Get-SmbServerConfiguration | Select EnableSMB2Protocol

# GET SMB Session versions
Get-SmbSession | Select-Object -Property ClientComputerName,ClientUserName,Dialect,NumOpens


#Install SMB1
Get-WindowsOptionalFeature –Online –FeatureName SMB1Protocol
