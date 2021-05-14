# Needs to be parameterized: $icofile, $URL, $ShortcutPath
# Need to change paths and test/create if don't exist


wget "https://www.example.com/logos/example.ico" -outfile "c:\agent\example.ico"

$WshShell = New-Object -comObject WScript.Shell
$path = "C:\Users\All Users\desktop\example.url"
$targetpath = "https://example.com/"
$iconlocation = "c:\agent\example.ico"
$iconfile = "IconFile=" + $iconlocation
$Shortcut = $WshShell.CreateShortcut($path)
$Shortcut.TargetPath = $targetpath
$Shortcut.Save()
Add-Content $path "HotKey=0"
Add-Content $path "$iconfile"
Add-Content $path "IconIndex=0"

