

if (Get-Module -ListAvailable -Name RunAsUser) {
} 
else {
    Install-Module RunAsUser -force
}
if (-not (Test-Path -LiteralPath C:\Temp)) {
    
    try {
        New-Item -Path C:\Temp -ItemType Directory -ErrorAction Stop | Out-Null #-Force
    }
    catch {
        Write-Error -Message "Unable to create directory 'C:\Temp'. Error was: $_" -ErrorAction Stop
    }
    "Successfully created directory 'C:\Temp'."

}
else {
}
$scriptblock = {
    Add-Type @'
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

    $Last = [PInvoke.Win32.UserInput]::LastInput
    $Idle = [PInvoke.Win32.UserInput]::IdleTime
    $DTnow = [DateTimeOffset]::Now

    $LastStr = $Last.ToLocalTime().ToString("MMM d h:mm tt")
    $IdleStr = $Idle.ToString("d\d\ h\h\ m\m")
    $DTnowStr = $DTnow.ToString("MMM d h:mm tt")
    "Device is idle for $IdleStr" | Out-File C:\Temp\IdleTime.txt

}
invoke-ascurrentuser -scriptblock $scriptblock -NoWait | Out-Null
Start-Sleep -Seconds 2
type "C:\Temp\IdleTime.txt"
del "C:\Temp\IdleTime.txt"