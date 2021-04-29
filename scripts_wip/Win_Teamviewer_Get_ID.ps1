# Retrieve Teamviewer ID from TRMM agent

$clientId = Get-ItemProperty HKLM:\SOFTWARE\Wow6432Node\TeamViewer -Name ClientID -ErrorAction SilentlyContinue

If (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Wow6432Node\TeamViewer' -Name ClientID -ErrorAction SilentlyContinue) {
    
    Write-Output $clientid.Clientid
    exit 0

}
Else {

    Write-Output 'Teamviewer is not installed.'
    exit 1
} 

Exit $LASTEXITCODE