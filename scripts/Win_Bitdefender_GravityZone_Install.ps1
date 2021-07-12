<#
.Synopsis
    Installs BitDefender Gravity Zone
.DESCRIPTION
    Find the BitDefender URL and EXE on your GravityZone page
    Network > Packages > Select Name You Want > Send Download Links > Select Installation Links > Appropriate Link
    $exe is 'setupdownloader[randomstring].exe' part of the link selected above. DO NOT CHANGE OR DOWNLOARD WILL FAIL
    $url is the Installation Link in the GravityZone

    TacticalRMM: Need to add Custom Fields to the Client or Site and invoke them in the Script Arguments. Name the url "bdurl" and the exe "bdexe" in the client custom field
    SuperOps.ai: Add url and exe run time variables 
.NOTES
    General notes
    v1.0 initial release by https://github.com/jhtechIL/
#>

param(
    $url,
    $exe
)
  
$destination = 'C:\Temp'

#Check if software is installed. If folder is present, terminate script
$64bit = if ([System.IntPtr]::Size -eq 8) { $true } else { $false }
$RegKeys = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\')
if ($true -eq $64bit) { $RegKeys += 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\' }
$Apps = @($RegKeys | Get-ChildItem | Get-ItemProperty | Where-Object { $_.DisplayName -like "*BitDefender*" })
if ($Apps.Count -gt 0) {
    Write-Host "Already Exists"
    [Environment]::Exit(0)
}

#Check for Temp folder. If Temp doesnt exist, create it
[System.IO.Directory]::CreateDirectory("$destination")

$webClient = New-Object System.Net.WebClient
$file = "$($destination)$($exe)"
$webClient.DownloadFile($url, $file)
Start-Process -FilePath $file -ArgumentList '/quietinstall /skipeula ' -Wait

#Delete Temp
Remove-Item -recurse $destination