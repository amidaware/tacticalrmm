# Define the Variables 1-3

# 1. Enter the beginning of the time range being reviewed. Use the same time format as configured in the endpoint's time & date settings (for example, for USA date&time: MM-DD-YYY hh:mm:ss).

$StartTime = "12-01-2017 17:00:00"

# 2. Enter the end of the time range being reviewed. Use the same time format as configured in the endpoint's time & date settings (for example, for USA date&time: MM-DD-YYY hh:mm:ss).

$EndTime = "12-14-2017 17:00:00" 

# 3. Location of the result file. Make sure the file type is csv.

$ResultFile = "C:\Temp\LoginAttemptsResultFile.csv"

# Create the output file and define the column headers.

"Time Created, Domain\Username, Login Attempt" | Add-Content $ResultFile

# Query the server for the login events.

$colEvents = Get-WinEvent -FilterHashtable @{logname='Security'; StartTime="$StartTime"; EndTime="$EndTime"}

# Iterate through the collection of login events.

Foreach ($Entry in $colEvents)

{

If (($Entry.Id -eq "4624") -and ($Entry.Properties[8].value -eq "2"))

{

$TimeCreated = $Entry.TimeCreated

$Domain = $Entry.Properties[6].Value

$Username = $Entry.Properties[5].Value

$Result = "$TimeCreated,$Domain\$Username,Interactive Login Success" | Add-Content $ResultFile

}

If (($Entry.Id -eq "4624") -and ($Entry.Properties[8].value -eq "10"))

{

$TimeCreated = $Entry.TimeCreated

$Domain = $Entry.Properties[6].Value

$Username = $Entry.Properties[5].Value

$Result = "$TimeCreated,$Domain\$Username,Remote Login Success" | Add-Content $ResultFile

}

If ($Entry.Id -eq "4625")

{

$TimeCreated = $Entry.TimeCreated

$Domain = $Entry.Properties[6].Value

$Username = $Entry.Properties[5].Value

$Result = "$TimeCreated,$Domain\$Username,Login Failure" | Add-Content $ResultFile

}

}
