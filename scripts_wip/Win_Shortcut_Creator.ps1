

mkdir -Path 'C:\agent' -Force
Invoke-WebRequest "http://www.yourwebsite.com/logos/yourico.ico" -outfile "c:\agent\yourico.ico"
$WshShell = New-Object -comObject WScript.Shell
$path = "C:\Users\All Users\desktop\Shortcut.url"
$targetpath = "https://yourwebsite.com"
$iconlocation = "c:\agent\yourico.ico"
$iconfile = "IconFile=" + $iconlocation
$Shortcut = $WshShell.CreateShortcut($path)
$Shortcut.TargetPath = $targetpath
$Shortcut.Save()
Add-Content $path "HotKey=0"
Add-Content $path "$iconfile"
Add-Content $path "IconIndex=0"

# This will create and agent directory then download the ico file 
# change ico file and location to download
