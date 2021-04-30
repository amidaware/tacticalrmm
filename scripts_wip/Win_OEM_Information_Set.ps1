Invoke-WebRequest -Uri 'http://<fqdn>/Downloads/Assets/CompanyLogo.bmp' -OutFile 'C:\windows\system32\CompanyLogo.bmp'

# New-Item ?Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\" ?Name "OEMInformation"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OEMInformation" -Name "Logo" -Value "C:\windows\system32\CompanyLogo.bmp"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OEMInformation" -Name "Manufacturer" -Value "Company name"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OEMInformation" -Name "SupportAppURL" -Value "http://<fqdn>"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OEMInformation" -Name "SupportURL" -Value "http://<fqdn>"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OEMInformation" -Name "SupportHours" -Value "ma - vr | 08:00 - 17:00"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\OEMInformation" -Name "SupportPhone" -Value "<phone number>"