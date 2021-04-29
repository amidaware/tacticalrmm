# Create reg keys
$volumeCaches = Get-ChildItem "HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
foreach($key in $volumeCaches)
{
New-ItemProperty -Path "$($key.PSPath)" -Name StateFlags0099 -Value 2 -Type DWORD -Force | Out-Null
}

# Run Disk Cleanup 
Start-Process -Wait "$env:SystemRoot\System32\cleanmgr.exe" -ArgumentList "/sagerun:99"

# Delete the keys
$volumeCaches = Get-ChildItem "HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
foreach($key in $volumeCaches)
{
Remove-ItemProperty -Path "$($key.PSPath)" -Name StateFlags0099 -Force | Out-Null
}