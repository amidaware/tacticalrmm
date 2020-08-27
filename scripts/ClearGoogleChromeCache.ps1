Write-Host “Exporting the list of users to c:\users.csv”
# List the users in c:\users and export to csv file for calling later
dir C:\Users | select Name | Export-Csv -Path C:\users.csv -NoTypeInformation
$list=Test-Path C:\users.csv
# Clear Google Chrome
Write-Host “Clearing Google caches”
Import-CSV -Path C:\users.csv -Header Name | foreach {
Remove-Item -path “C:\Users\$($_.Name)\AppData\Local\Google\Chrome\User Data\Default\Cache\*” -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path “C:\Users\$($_.Name)\AppData\Local\Google\Chrome\User Data\Default\Cache2\entries\*” -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path “C:\Users\$($_.Name)\AppData\Local\Google\Chrome\User Data\Default\Cookies” -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path “C:\Users\$($_.Name)\AppData\Local\Google\Chrome\User Data\Default\Media Cache” -Recurse -Force -EA SilentlyContinue -Verbose
Remove-Item -path “C:\Users\$($_.Name)\AppData\Local\Google\Chrome\User Data\Default\Cookies-Journal” -Recurse -Force -EA SilentlyContinue -Verbose
}
Remove-Item -path c:\users.csv
Write-Host “Google Chrome cache is cleared”