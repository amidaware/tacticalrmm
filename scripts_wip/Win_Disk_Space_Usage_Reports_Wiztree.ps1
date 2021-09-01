<# 
From https://smsagent.blog/2018/08/15/create-disk-usage-reports-with-powershell-and-wiztree/

To use the script, simply download the WizTree Portable app, extract the WizTree64.exe and place it in the same location as the script (assuming 64-bit OS).  Set the run location in the script (ie $PSScriptRoot if calling the script, or the directory location if running in the ISE), the temporary location where it can create files, and the server share where you want to copy the reports to. Then just run the script in admin context.

 #>

 
# Script to export html and csv reports of file and directory content on the system drive

# Use to identify large files/directories for disk space cleanup
# Uses WizTree portable to quickly retrieve file and directory sizes from the Master File Table on disk
# Download and extract the WizTree64.exe and place in the same directory as this script

# Set the running location
$RunLocation = $PSScriptRoot
#$RunLocation = "C:\temp"
$TempLocation = "C:\temp"

# Set Target share to copy the reports to
$TargetRoot = "\\server-01\sharename\DirectorySizeInfo"

# Free disk space thresholds (percentages) for summary report
$script:Thresholds = @{}
$Thresholds.Warning = 80
$Thresholds.Critical = 90

# Custom function to exit with a specific code
function ExitWithCode { 
    param 
    ( 
        $exitcode 
    ) 
    $host.SetShouldExit($exitcode) 
    exit 
} 

# Function to set the progress bar colour based on the the threshold value in the summary report
function Set-PercentageColour {
    param(
        [int]$Value
    )

    If ($Value -lt $Thresholds.Warning) {
        $Hex = "#00ff00" # Green
    }

    If ($Value -ge $Thresholds.Warning -and $Value -lt $Thresholds.Critical) {
        $Hex = "#ff9900" # Amber
    }

    If ($Value -ge $Thresholds.Critical) {
        $Hex = "#FF0000" # Red
    }

    Return $Hex
}

# Define Html CSS style
$Style = @"
<style>
table { 
    border-collapse: collapse;
}
td, th { 
    border: 1px solid #ddd;
    padding: 8px;
}
th {
    padding-top: 12px;
    padding-bottom: 12px;
    text-align: left;
    background-color: #4286f4;
    color: white;
}
</style>
"@

# Set the filenames of WizTree csv's
$FilesCSV = "Files_$(Get-Date –Format 'yyyyMMdd_hhmmss').csv"
$FoldersCSV = "Folders_$(Get-Date –Format 'yyyyMMdd_hhmmss').csv"

# Set the filenames of customised csv's
$ExportedFilesCSV = "Exported_Files_$(Get-Date –Format 'yyyyMMdd_hhmmss').csv"
$ExportedFoldersCSV = "Exported_Folders_$(Get-Date –Format 'yyyyMMdd_hhmmss').csv"

# Set the filenames of html reports
$ExportedFilesHTML = "Largest_Files_$(Get-Date –Format 'yyyyMMdd_hhmmss').html"
$ExportedFoldersHTML = "Largest_Folders_$(Get-Date –Format 'yyyyMMdd_hhmmss').html"
$SummaryHTMLReport = "Disk_Usage_Summary_$(Get-Date –Format 'yyyyMMdd_hhmmss').html"

# Run the WizTree portable app
Start-Process –FilePath "$RunLocation\WizTree64.exe" –ArgumentList """$Env:SystemDrive"" /export=""$TempLocation\$FilesCSV"" /admin 1 /sortby=2 /exportfolders=0" –Verb runas –Wait
Start-Process –FilePath "$RunLocation\WizTree64.exe" –ArgumentList """$Env:SystemDrive"" /export=""$TempLocation\$FoldersCSV"" /admin 1 /sortby=2 /exportfiles=0" –Verb runas –Wait



#region Files

# Remove the first 2 rows from the CSVs to leave just the relevant data
$CSVContent = Get-Content –Path $TempLocation\$FilesCSV –ReadCount 0 
$CSVContent = $CSVContent | Select –Skip 1
$CSVContent = $CSVContent | Select –Skip 1

# Create a table to store the results
$Table = [System.Data.DataTable]::new("Directory Structure")
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Name", [System.String]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (Bytes)", [System.Int64]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (KB)", [System.Decimal]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (MB)", [System.Decimal]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (GB)", [System.Decimal]))

# Populate the table from the CSV data
Foreach ($csvrow in $CSVContent) {
    $Content = $csvrow.split(',')
    [void]$Table.rows.Add(($Content[0].Replace('"', '')), $Content[2], ([math]::Round(($Content[2] / 1KB), 2)), ([math]::Round(($Content[2] / 1MB), 2)), ([math]::Round(($Content[2] / 1GB), 2)))
}

# Export the table to a new CSV
$Table | Sort 'Size (Bytes)' –Descending | Export-CSV –Path $TempLocation\$ExportedFilesCSV –NoTypeInformation –UseCulture

# Export the largest 100 results into html format
$Table |
Sort 'Size (Bytes)' –Descending |
Select –First 100 |
ConvertTo-Html –Property 'Name', 'Size (Bytes)', 'Size (KB)', 'Size (MB)', 'Size (GB)' –Head $style –Body "<h2>100 largest files on $env:COMPUTERNAME</h2>" –CssUri "http://www.w3schools.com/lib/w3.css"  | 
Out-String | Out-File $TempLocation\$ExportedFilesHTML

#endregion



#region Folders

# Remove the first 2 rows from the CSVs to leave just the relevant data
$CSVContent = Get-Content –Path $TempLocation\$FoldersCSV –ReadCount 0 
$CSVContent = $CSVContent | Select –Skip 1
$CSVContent = $CSVContent | Select –Skip 1

# Create a table to store the results
$Table = [System.Data.DataTable]::new("Directory Structure")
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Name", [System.String]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (Bytes)", [System.Int64]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (KB)", [System.Decimal]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (MB)", [System.Decimal]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Size (GB)", [System.Decimal]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Files", [System.String]))
[void]$Table.Columns.Add([System.Data.DataColumn]::new("Folders", [System.String]))

# Populate the table from the CSV data
Foreach ($csvrow in $CSVContent) {
    $Content = $csvrow.split(',')
    [void]$Table.rows.Add($($Content[0].Replace('"', '')), $Content[2], ([math]::Round(($Content[2] / 1KB), 2)), ([math]::Round(($Content[2] / 1MB), 2)), ([math]::Round(($Content[2] / 1GB), 2)), $Content[5], $Content[6])
}

# Export the table to a new CSV
$Table | Sort 'Size (Bytes)' –Descending | Export-CSV –Path $TempLocation\$ExportedFoldersCSV –NoTypeInformation –UseCulture

# Export the largest 100 results into html format
$Table |
Sort 'Size (Bytes)' –Descending |
Select –First 100 |
ConvertTo-Html –Property 'Name', 'Size (Bytes)', 'Size (KB)', 'Size (MB)', 'Size (GB)', 'Files', 'Folders' –Head $style –Body "<h2>100 largest directories on $env:COMPUTERNAME</h2>" –CssUri "http://www.w3schools.com/lib/w3.css"  | 
Out-String | Out-File $TempLocation\$ExportedFoldersHTML

#endregion



#region Create HTML disk usage summary report

# Get system drive data
$WMIDiskInfo = Get-CimInstance –ClassName Win32_Volume –Property Capacity, FreeSpace, DriveLetter | Where { $_.DriveLetter -eq $env:SystemDrive } | Select Capacity, FreeSpace, DriveLetter
$DiskInfo = [pscustomobject]@{
    DriveLetter      = $WMIDiskInfo.DriveLetter
    'Capacity (GB)'  = [math]::Round(($WMIDiskInfo.Capacity / 1GB), 2)
    'FreeSpace (GB)' = [math]::Round(($WMIDiskInfo.FreeSpace / 1GB), 2)
    'UsedSpace (GB)' = [math]::Round((($WMIDiskInfo.Capacity / 1GB) – ($WMIDiskInfo.FreeSpace / 1GB)), 2)
    'Percent Free'   = [math]::Round(($WMIDiskInfo.FreeSpace * 100 / $WMIDiskInfo.Capacity), 2)
    'Percent Used'   = [math]::Round((($WMIDiskInfo.Capacity – $WMIDiskInfo.FreeSpace) * 100 / $WMIDiskInfo.Capacity), 2)
}

# Create html header
$html = @"
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="http://www.w3schools.com/lib/w3.css"&gt;
<body>
"@

# Set html
$html = $html + @"
<h2>Disk Space Usage for Drive $($DiskInfo.DriveLetter) on $env:COMPUTERNAME</h2>
<table cellpadding="0" cellspacing="0" width="700">
<tr>
  <td style="background-color:$(Set-PercentageColour –Value $($DiskInfo.'Percent Used'));padding:10px;color:#ffffff;" width="$($DiskInfo.'Percent Used')%">
    $($DiskInfo.'UsedSpace (GB)') GB ($($DiskInfo.'Percent Used') %)
  </td>
  <td style="background-color:#eeeeee;padding-top:10px;padding-bottom:10px;color:#333333;" width="$($DiskInfo.'Percent Used')%">
  </td>
</tr>
</table>
<table cellpadding="0" cellspacing="0" width="700">
<tr>
    <td style="padding:5px;" width="80%">
    Capacity: $($DiskInfo.'Capacity (GB)') GB
    </td>
</tr>
<tr>
    <td style="padding:5px;" width="80%">
    FreeSpace: $($DiskInfo.'FreeSpace (GB)') GB
    </td>
</tr>
<tr>
    <td style="padding:5px;" width="80%">
    Percent Free: $($DiskInfo.'Percent Free') %
    </td>
</tr>
</table>
"@

If ($DiskInfo.'FreeSpace (GB)' -lt 20) {

    $html = $html + @"
    <table cellpadding="0" cellspacing="0" width="700">  
    <tr>
        <td style="padding:5px;color:red;font-weight:bold" width="80%">
        You need to free $(20 – $DiskInfo.'FreeSpace (GB)') GB on this disk to pass the W10 readiness check!
        </td>
    </tr>
    </table>
"@
}

# Close html document
$html = $html + @"
</body>
</html>
"@

# Export to file
$html | 
Out-string | 
Out-File $TempLocation\$SummaryHTMLReport


#endregion




#region Copy files to share

# Create a subfolder with computername if doesn't exist
If (!(Test-Path $TargetRoot\$env:COMPUTERNAME)) {
    $null = New-Item –Path $TargetRoot –Name $env:COMPUTERNAME –ItemType Directory
}

# Create a subdirectory with current date-time
$DateString = ((Get-Date).ToUniversalTime() | get-date –Format "yyyy-MM-dd_HH-mm-ss").ToString()
If (!(Test-Path $TargetRoot\$env:COMPUTERNAME\$DateString)) {
    $null = New-Item –Path $TargetRoot\$env:COMPUTERNAME –Name $DateString –ItemType Directory
}

# Set final target location
$TargetLocation = "$TargetRoot\$env:COMPUTERNAME\$DateString"

# Copy files
$Files = @(
    $ExportedFilesCSV
    $ExportedFoldersCSV
    $ExportedFilesHTML
    $ExportedFoldersHTML
    $SummaryHTMLReport
)
Try {
    Robocopy $TempLocation $TargetLocation $Files /R:10 /W:5 /NP 
}
Catch {}

#endregion


# Cleanup temp files
$Files = @(
    $FilesCSV
    $FoldersCSV
    $ExportedFilesCSV
    $ExportedFoldersCSV
    $ExportedFilesHTML
    $ExportedFoldersHTML
    $SummaryHTMLReport
)

Foreach ($file in $files) {
    Remove-Item –Path $TempLocation\$file –Force
}


# Force a code 0 on exit, in case of some non-terminating error.
ExitWithCode 0