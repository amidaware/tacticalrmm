# bradhawkins https://discord.com/channels/736478043522072608/744281869499105290/890570620469915698

$idlecode = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace PInvoke.Win32 {

    public static class UserInput {

        [DllImport("user32.dll", SetLastError=false)]
        private static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

        [StructLayout(LayoutKind.Sequential)]
        private struct LASTINPUTINFO {
            public uint cbSize;
            public int dwTime;
        }

        public static DateTime LastInput {
            get {
                DateTime bootTime = DateTime.UtcNow.AddMilliseconds(-Environment.TickCount);
                DateTime lastInput = bootTime.AddMilliseconds(LastInputTicks);
                return lastInput;
            }
        }

        public static TimeSpan IdleTime {
            get {
                return DateTime.UtcNow.Subtract(LastInput);
            }
        }

        public static int LastInputTicks {
            get {
                LASTINPUTINFO lii = new LASTINPUTINFO();
                lii.cbSize = (uint)Marshal.SizeOf(typeof(LASTINPUTINFO));
                GetLastInputInfo(ref lii);
                return lii.dwTime;
            }
        }
    }
}
'@

$idlecode2 = @'

for ( $i = 0; $i -lt 10; $i++ ) {
    $Last = [PInvoke.Win32.UserInput]::LastInput
    $Idle = [PInvoke.Win32.UserInput]::IdleTime
    $LastStr = $Last.ToLocalTime().ToString("MM/dd/yyyy hh:mm tt")
    Out-File -FilePath "c:\temp\useridle.txt" -Encoding ascii -Force -InputObject ("Last user keyboard/mouse input: " + $LastStr)
    Out-File -FilePath "c:\temp\useridle.txt" -Append -Encoding ascii -Force -InputObject ("Idle for " + $Idle.Days + " days, " + $Idle.Hours + " hours, " + $Idle.Minutes + " minutes, " + $Idle.Seconds + " seconds.")
}
'@

$hidecode = @"
command = "powershell.exe -nologo -ExecutionPolicy Bypass -command c:\temp\useridle.ps1"
set shell = CreateObject("WScript.Shell")
shell.Run command,0
"@ 
  
Out-File -FilePath "c:\temp\useridle.vbs" -Force -InputObject $hidecode -Encoding ascii
Out-File -FilePath "c:\temp\useridle.ps1" -Force -InputObject "Add-Type @'" -Encoding ascii
Out-File -FilePath "c:\temp\useridle.ps1" -Append -Force -InputObject $idlecode -Encoding ascii
Out-File -FilePath "c:\temp\useridle.ps1" -Append -Force -InputObject "'@" -Encoding ascii
Out-File -FilePath "c:\temp\useridle.ps1" -Append -Force -InputObject $idlecode2 -Encoding ascii

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "c:\temp\useridle.vbs"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$username = Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -expand UserName
$principal = New-ScheduledTaskPrincipal -UserId $username
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal
$taskname = "useridle"
Register-ScheduledTask $taskname -InputObject $task  >$null 2>&1
Start-ScheduledTask -TaskName $taskname
Start-Sleep -Seconds 5
Unregister-ScheduledTask -TaskName $taskname -Confirm:$false
 
$idletime = Get-Content -Path "c:\temp\useridle.txt"
Write-Output $idletime

Remove-Item -Path "c:\temp\useridle.txt"
Remove-Item -Path "c:\temp\useridle.vbs"
Remove-Item -Path "c:\temp\useridle.ps1"
 
exit 0
