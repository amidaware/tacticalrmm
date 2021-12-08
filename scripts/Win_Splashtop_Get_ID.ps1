# Retrieve Splashtop SUUID from device registry.

if (!$ErrorCount -eq 0) {
    exit 1
}


$key = 'HKLM:\SOFTWARE\WOW6432Node\Splashtop Inc.\Splashtop Remote Server'
(Get-ItemProperty -Path $key -Name SUUID).SUUID
Write-Output $key.SUUID