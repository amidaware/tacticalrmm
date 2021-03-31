Write-Host "Downloading Duplicati" -ForegroundColor Green
New-Item -ItemType directory -Path c:\InstallFiles\Duplicati
$client1 = new-object System.Net.WebClient
$client1.DownloadFile(“https://go.microsoft.com/fwlink/?LinkId=746572”,“c:\InstallFiles\Duplicati\VC_redist.x64.exe”)
Start-Process -FilePath "c:\InstallFiles\Duplicati\VC_redist.x64.exe” "/install /passive /norestart" -Wait
$client2 = new-object System.Net.WebClient
$client2.DownloadFile(“https://updates.duplicati.com/beta/duplicati-2.0.5.1_beta_2020-01-18.zip”,“c:\InstallFiles\Duplicati\duplicati-2.0.5.1_beta_2020-01-18.zip”)
Write-Host "Extracting Duplicati" -ForegroundColor Green
Expand-Archive -LiteralPath c:\InstallFiles\Duplicati\duplicati-2.0.5.1_beta_2020-01-18.zip -DestinationPath "C:\Program Files\Duplicati 2" -Force
Write-Host "Installing Duplicati as a Service" -ForegroundColor Green
Start-Process -FilePath "C:\Program Files\Duplicati 2\Duplicati.WindowsService.exe" "install" -Wait
Write-Host "Starting Duplicati as a Service" -ForegroundColor Green
Start-Service -Name Duplicati
Write-Host "Removing Duplicati Install Files" -ForegroundColor Green
Remove-Item -Path c:\InstallFiles -Recurse