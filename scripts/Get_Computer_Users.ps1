# This script return the list of all users and checks
# if they are enabled or disabled

get-localuser | Select name,Enabled > $env:TEMP\users.txt
Get-Content $env:TEMP\users.txt | foreach {Write-Output $_}