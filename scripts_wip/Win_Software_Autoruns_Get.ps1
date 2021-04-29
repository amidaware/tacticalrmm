###
# Author: Dave Long <dlong@cagedata.com>
# Uses Autoruns from Sysinternals to get all automatically running programs on PCs.
# Also tests autoruns against Virtus Total and shows how many AV programs detect
# each autorun as a virus.
#
# Running assumes acceptance of the Sysinternals and Virus Total licenses.
###

$AutorunsUrl = "https://download.sysinternals.com/files/Autoruns.zip"
$AutorunsOut = Join-Path $env:TEMP "Autoruns.zip"
$Autoruns = Join-Path $env:TEMP "Autoruns"
$OutputFile = Join-Path $Autoruns "autoruns.csv"

Invoke-WebRequest -Uri $AutorunsUrl -OutFile $AutorunsOut

Expand-Archive -Path $AutorunsOut -DestinationPath $Autoruns

Start-Process -Wait -FilePath $Autoruns/autorunsc.exe -NoNewWindow -PassThru -ArgumentList @("-v", "-vt", "-c", "-o $OutputFile")

Import-Csv -Path $OutputFile

Write-Host "Complete Autoruns output stored at $OutputFile"