## Measures the speed of the download, can only be ran on a PC running Windows 10 or a server running Server 2016+, plan is to add uploading also
## Majority of this script has been copied/butchered from https://www.ramblingtechie.co.uk/2020/07/13/internet-speed-test-in-powershell/
# MINIMUM ACCEPTED THRESHOLD IN mbps 
$mindownloadspeed = 20
$minuploadspeed = 4

# File to download you can find download links for other files here https://speedtest.flonix.net
$downloadurl = "https://files.xlawgaming.com/10mb.bin"
#$UploadURL = "http://ipv4.download.thinkbroadband.com/10MB.zip"

# SIZE OF SPECIFIED FILE IN MB (adjust this to match the size of your file in MB as above)
$size = 10
# Name of Downloaded file
$localfile = "SpeedTest.bin"

# WEB CLIENT VARIABLES
$webclient = New-Object System.Net.WebClient

#RUN DOWNLOAD & CALCULATE DOWNLOAD SPEED
$downloadstart_time = Get-Date
$webclient.DownloadFile($downloadurl, $localfile)
$downloadtimetaken = $((Get-Date).Subtract($downloadstart_time).Seconds)
$downloadspeed = ($size / $downloadtimetaken)*8
Write-Output "Time taken: $downloadtimetaken second(s) | Download Speed: $downloadspeed mbps"

#RUN UPLOAD & CALCULATE UPLOAD SPEED
#$uploadstart_time = Get-Date
#$webclient.UploadFile($UploadURL, $localfile) > $null;
#$uploadtimetaken = $((Get-Date).Subtract($uploadstart_time).Seconds)
#$uploadspeed = ($size / $uploadtimetaken) * 8
#Write-Output "Time taken: $uploadtimetaken second(s) | Upload Speed: $uploadspeed mbps"

#DELETE TEST DOWNLOAD FILE
Remove-Item -path $localfile

#SEND ALERTS IF BELOW MINIMUM THRESHOLD 
if ($downloadspeed -ge $mindownloadspeed) 
{ 
Write-Output "Speed is acceptable. Current download speed at is $downloadspeed mbps which is above the threshold of $mindownloadspeed mbps" 
exit 0
}

else 
{ 
Write-Output "Current download speed at is $downloadspeed mbps which is below the minimum threshold of $mindownloadspeed mbps" 
exit 1
}

Exit $LASTEXITCODE
