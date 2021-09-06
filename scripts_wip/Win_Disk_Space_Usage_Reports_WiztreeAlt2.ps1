# extract WizTree
Expand-Archive C:\temp\wiztree_3_26_portable.zip -DestinationPath C:\temp\wiztree

# run wiztree.exe against provided drive/path
# generates diskusage.csv file and uploads to asset, deletes local file after upload

# If 32-bit
if ([System.IntPtr]::Size -eq 4) {
    C:\temp\wiztree\wiztree.exe "$scanpath" /export="c:\temp\wiztree\diskusage.csv" /admin=1 /exportfolders=1 /exportfiles=0 /sortby=2 | Out-Null
}
else {
    C:\temp\wiztree\wiztree64.exe "$scanpath" /export="c:\temp\wiztree\diskusage.csv" /admin=1 /exportfolders=1 /exportfiles=0 /sortby=2 | Out-Null
}
# This will upload the file to Syncro and attach it to the Asset.
Upload-File -Subdomain "$subdomain" -FilePath "C:\temp\wiztree\diskusage.csv"
# Delete local file after upload
Remove-Item -Path "C:\temp\wiztree\diskusage.csv" -Force