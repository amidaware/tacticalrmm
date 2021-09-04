# save the file and self-host: https://www.microsoft.com/en-us/download/confirmation.aspx?id=54616
# Win 2012 x64 https://download.microsoft.com/download/6/F/5/6F5FF66C-6775-42B0-86C4-47D41F2DA187/W2K12-KB3191565-x64.msu
# Win7 x64 and Svr 2008 R2 x64 https://download.microsoft.com/download/6/F/5/6F5FF66C-6775-42B0-86C4-47D41F2DA187/Win7AndW2K8R2-KB3191566-x64.zip
# Win7 x32 https://download.microsoft.com/download/6/F/5/6F5FF66C-6775-42B0-86C4-47D41F2DA187/Win7-KB3191566-x86.zip
# Win 8.1 x64 and Svr 2012 R2 x64 https://download.microsoft.com/download/6/F/5/6F5FF66C-6775-42B0-86C4-47D41F2DA187/Win8.1AndW2K12R2-KB3191564-x64.msu
# Win 81 x32 https://download.microsoft.com/download/6/F/5/6F5FF66C-6775-42B0-86C4-47D41F2DA187/Win8.1-KB3191564-x86.msu

# See https://github.com/wh1te909/tacticalrmm/blob/develop/scripts_wip/Win_Powershell_Version_Check.ps1 for alert script to warn when this is needed

if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Output "Old Version - Need to Upgrade"
    # Download MSU file - EDIT THIS URL
    # $url = "http://your site.com/Win7AndW2K8R2-KB3191566-x64.msu"
    (new-object System.Net.WebClient).DownloadFile($url, 'C:\temp\filename.msu')

    ## Run upgrade process
    start-process -FilePath "c:\windows\system32\wusa.exe" -ArgumentList "c:\temp\filename.msu /quiet /norestart /log:c:\temp\log.evt"
    Write-Output "Run upgrade process"
}
else {
    Write-Output "Already at 5.0 or Higher"
}