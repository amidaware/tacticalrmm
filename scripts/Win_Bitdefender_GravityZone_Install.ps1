<#
.Synopsis
    Installs BitDefender Gravity Zone
.DESCRIPTION
    Find the BitDefender URL on your GravityZone page
    Network > Packages > Select Name You Want > Send Download Links > Select Installation Links > Appropriate Link
    $exe is deprecated. The filename is extracted from $url
    $url is the Installation Link in the GravityZone
    $log if provided will output verbose logs with timestamps. This can be used to determine how long the installer took.

    TacticalRMM: Need to add Custom Fields to the Client or Site and invoke them in the Script Arguments; example shown.
    Name the url "bdurl" in the client custom field.
        -url {{client.bdurl}

    SuperOps.ai: Add url and exe run time variables.

.NOTES
    General notes
    v1.0 initial release by https://github.com/jhtechIL/
    v1.0.1 has the following changes
        -   $exe parameter is determined from the $url. A deprecation notice is output if it's specified. The param will
            be kept to prevent errors from those that have it specified.
        -   Dynamically get the temp folder instead of using a hardcoded folder.
        -   Add many checks to verify we are on the happy path. Output messages if we stray from the happy path.
        -   Added -log parameter to output verbose logs with timestamps.
        -   Prefer Exit() over [Environment]::Exit since the later closes the console window while testing.
        -   Downgrade TLS for Windows prior to Windows 10

    The string between the [] is a base64 encoded URL for the installer
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("StringBetweenSquareBraces="))
#>

param(
    [string] $url,
    [string] $exe,
    [switch] $log
)

function Get-TimeStamp() {
    return Get-Date -UFormat "%Y-%m-%d %H:%M:%S"
}

if ($log) {
    # Skip the "Stdout:" line
    Write-Output ""
}

if (($null -ne $exe) -and ($exe.Length -gt 0)) {
    Write-Output "$(Get-Timestamp) The -exe parameter is deprecated (not needed)"
}

if (($null -eq $url) -or ($url.Length -eq 0)) {
    Write-Output "$(Get-Timestamp) Url parameter is not specified"
    Exit(1)
}

$exe = [uri]::UnescapeDataString($([uri]$url).segments[-1])
if ($null -eq $exe) {
    Write-Output "$(Get-Timestamp) Exe could not be extracted from the URL"
    Write-Output "$(Get-Timestamp) Make sure the URL is not modified from the original URL"
    Exit(1)
}

# Check if software is installed. If key is present, terminate script
if ($log) {
    Write-Output "$(Get-Timestamp) Checking if Bitdefender is installed..."
}
$64bit = if ([System.IntPtr]::Size -eq 8) { $true } else { $false }
$RegKeys = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\')
if ($true -eq $64bit) { $RegKeys += 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\' }
$Apps = @($RegKeys | Get-ChildItem | Get-ItemProperty | Where-Object { $_.DisplayName -like "*BitDefender*" })
if ($Apps.Count -gt 0) {
    Write-Output "$(Get-Timestamp) Bitdefender is already installed"
    Exit(0)
}

$tmpDir = [System.IO.Path]::GetTempPath()
if (!(Test-Path $tmpDir)) {
    Write-Output "$(Get-Timestamp) Couldn't get path to temp folder"
    Exit(1)
}
$tmpExe = Join-Path -Path $tmpDir -ChildPath $exe

# Download
if ($log) {
    Write-Output "$(Get-Timestamp) Bitdefender is not installed"
    Write-Output "$(Get-Timestamp) Downloading installer..."
}
if ([Environment]::OSVersion.Version -le (new-object 'Version' 7,0)) {
    # This is required for Windows 7, 8.1
    Write-Output "$(Get-Timestamp) Adjusting TLS version(s) for Windows prior to Win 10"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls12
}
$(New-Object System.Net.WebClient).DownloadFile($url, $tmpExe)
if (!$?) {
    Write-Output "$(Get-Timestamp) Download failed: $($error[0].ToString())"
    Write-Output "$(Get-Timestamp) Stacktrace: $($error[0].Exception.ToString())"
    Write-Output "$(Get-Timestamp) Filename: ${tmpExe}"
    Exit(1)
}
if ((Get-Item -LiteralPath $tmpExe).length -eq 0) {
    Write-Output "$(Get-Timestamp) Downloaded file is 0 bytes"
    Write-Output "$(Get-Timestamp) Filename: ${tmpExe}"
    Get-Item -LiteralPath $tmpExe
    Exit(1)
}

# Install
if ($log) {
    Write-Output "$(Get-Timestamp) Downloaded"
    Write-Output "$(Get-Timestamp) Installing..."
}
$tmpExe = Get-Item -LiteralPath $tmpExe
Start-Process -FilePath $tmpExe -ArgumentList '/quietinstall /skipeula ' -Wait
if (!$?) {
    Write-Output "$(Get-Timestamp) Installation failed: $($error[0].ToString())"
    Write-Output "$(Get-Timestamp) Stacktrace: $($error[0].Exception.ToString())"
    if (Test-Path -PathType Leaf -Path $tmpExe) {
        Remove-Item $tmpExe
    }
    Exit(1)
}
if ($log) {
    Write-Output "$(Get-Timestamp) Installed"
    Write-Output "$(Get-Timestamp) Cleaning up temp file..."
}

# Cleanup
if (Test-Path -PathType Leaf -Path $tmpExe) {
    Remove-Item $tmpExe
}
if ($log) {
    Write-Output "$(Get-Timestamp) Finished!"
}
Exit(0)

