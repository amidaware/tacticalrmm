$dir = "c:\temp"
mkdir $dir
$webClient = New-Object System.Net.WebClient
$url = "https://go.microsoft.com/fwlink/?LinkID=799445"
$file = "$($dir)\Win10Upgrade.exe"
$webClient.DownloadFile($url,$file)
Start-Process -FilePath $file -ArgumentList "/quietinstall /skipeula /auto upgrade /copylogs $dir" -verb runas