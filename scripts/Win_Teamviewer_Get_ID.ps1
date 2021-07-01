# Retrieve Teamviewer ID from TRMM agent. This tests versions 6+ known Registry Paths.

$TeamViewerVersionsNums = @('6', '7', '8', '9', '')
$RegPaths = @('HKLM:\SOFTWARE\TeamViewer', 'HKLM:\SOFTWARE\Wow6432Node\TeamViewer')
$Paths = @(foreach ($TeamViewerVersionsNum in $TeamViewerVersionsNums) {
        foreach ($RegPath in $RegPaths) {
            $RegPath + $TeamViewerVersionsNum
        }
    })

foreach ($Path in $Paths) {
    If (Test-Path $Path) {
        $GoodPath = $Path
    }
}

foreach ($FullPath in $GoodPath) {
    If ($null -ne (Get-Item -Path $FullPath).GetValue('ClientID')) {
        $TeamViewerID = (Get-Item -Path $FullPath).GetValue('ClientID')
        $ErrorActionPreference = 'silentlycontinue'

    }

  

}   
Write-Output $TeamViewerID


Exit $LASTEXITCODE