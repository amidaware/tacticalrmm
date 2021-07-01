$Paths = @($Env:APPDATA, $Env:ProgramData, $Env:ALLUSERSPROFILE)

foreach ($Path in $Paths) {
    If (Test-Path $Path\AnyDesk) {
        $GoodPath = $Path
    }
}

$ConfigPath = $GoodPath + "\AnyDesk\system.conf"

$ResultsIdSearch = Select-String -Path $ConfigPath -Pattern ad.anynet.id

$Result = @($ResultsIdSearch -split '=')

$Result[1]
