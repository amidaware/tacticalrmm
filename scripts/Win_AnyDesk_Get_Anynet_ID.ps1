$Paths = @($Env:APPDATA, $Env:ProgramData, $Env:ALLUSERSPROFILE)

foreach ($Path in $Paths) {
    If (Test-Path $Path\AnyDesk) {
        $GoodPath = $Path
    }
}

$SystemFile = get-childitem -Path $GoodPath -Filter "system.conf" -Recurse -ErrorAction SilentlyContinue

$ConfigPath = $SystemFile.FullName

$ResultsIdSearch = Select-String -Path $ConfigPath -Pattern ad.anynet.id

$Result = @($ResultsIdSearch -split '=')

$Result[1]
