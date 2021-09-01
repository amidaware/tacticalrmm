$runpath = "C:\TechTools\Speedtest\Speedtest.exe"
$zippath = "C:\TechTools\Zip\"
$toolpath = "C:\TechTools\Speedtest\"
$Url = "https://install.speedtest.net/app/cli/ookla-speedtest-1.0.0-win64.zip"
$DownloadZipFile = "C:\TechTools\Zip\" + $(Split-Path -Path $Url -Leaf)
$ExtractPath = "C:\TechTools\Speedtest\"


#Check for speedtest cli executable, if missing it will check for and create folders required,
#download speedtest cli zip file from $URL and extract into correct folder
IF(!(test-path $runpath))
{
    #Check for SpeedTest folder, if missing, create
    If(!(test-path $toolpath))
    {
      New-Item -ItemType Directory -Force -Path $toolpath
    }

    #Check for zip folder, if missing, create
    If(!(test-path $zippath))
    {
      New-Item -ItemType Directory -Force -Path $zippath
    }
    
    #Download and extract zip from the URL in $URL
    Invoke-WebRequest -Uri $Url -OutFile $DownloadZipFile
    $ExtractShell = New-Object -ComObject Shell.Application 
    $ExtractFiles = $ExtractShell.Namespace($DownloadZipFile).Items() 
    $ExtractShell.NameSpace($ExtractPath).CopyHere($ExtractFiles) 

}

& $runpath