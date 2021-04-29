Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Format-Table PSChildName, DisplayName, Publisher, DisplayVersion, Version, UninstallString

Get-ItemProperty HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Format-Table PSChildName, DisplayName, Publisher, DisplayVersion, Version, UninstallString