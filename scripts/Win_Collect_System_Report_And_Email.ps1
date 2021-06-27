<#
    .SYNOPSIS
    Generates a system report in HTML format.

    .DESCRIPTION 
    A report comprised of stopped services, running processes, drive space, network adapter settings, and printers is stored locally with a copy sent via e-mail

    .INPUTS
    Must provide ALL parameter arguments in the following manner (failing to do so will cause the script to exit out prior to creating and sending the report):

    -agentname <enter directly or use the Script Variable {{agent.hostname}}>
    -file <enter file name with the extension .HTM or .HTML>
    -fromaddress <sender's email address>
    -toaddress <recipient's email address>
    -smtpserver <address of SMTP mail server to be used for sending the report>
    -password <password associated with a valid mail account to access the mail server via SMTP>
    -port <587 is the standard port for sending mail over TLS>

    .OUTPUTS
    Results are sent as a HTML file to C:\Temp and e-mailed based on provided parameters

    .NOTES
    Change Log
    V1.0 Initial release and parameterization
    V1.1 Check for C:\Temp path prior to generating report
    V1.2 Parameter checks with exit codes added
  

    Reference Links: 
        www.google.com
        docs.microsoft.com
#>


param(
    $agentname,
    $fromaddress,
    $toaddress,
    $smtpserver,
    $password,
    $port,
    $file
)

#Parameter Checks with exit codes

if ([string]::IsNullOrEmpty($agentname)){
    write-host "You must directly enter a hostname or use the TRMM Script Variable {{agent.hostname}} to pass the hostname from the dashboard."
    exit 1
}

if ([string]::IsNullOrEmpty($file)){
    Write-host "You must provide a file name with a .HTM extension."
    exit 1
}

if ([string]::IsNullOrEmpty($fromaddress)){
    Write-host "You must provide a sender's email address."
    exit 1
}

if ([string]::IsNullOrEmpty($toaddress)){
    write-host "You must provide a recipient's email address."
    exit 1
}

if ([string]::IsNullOrEmpty($smtpserver)){
    write-host "You must provide a SMTP server address."
    exit 1
}

if ([string]::IsNullOrEmpty($password)){
    write-host "You must provide a password for the SMTP server"
    exit 1
}

if ([string]::IsNullOrEmpty($port)){
    write-host "A valid port number is required to send the report."
    exit 1
}

else{

$path = "C:\Temp"
$destination = "$path\$file"


if(!(Test-Path -Path $path)){
write-host "Path does not exist. Creating path prior to generating report."
New-Item -Path "C:\" -Name "Temp" -ItemType "directory"
}

else{
    Write-host "Path alreaedy exists. Attempting to generate report."
}


#HTML Styling

$a = "<style>BODY{font-family: Calibri; font-size: 15pt;}"
$a = $a + "TABLE{border: 1px solid black; border-collapse: collapse;}"
$a = $a + "TH{border: 1px solid green; background: lightgreen; padding: 5px; }"
$a = $a + "TD{border: 1px solid green; padding: 5px; }"
$a = $a + "</style>"
 
#Heading

"<H1 style='color:green;'>System Report For $agentname</H1>" | Out-File $destination -Append

#Network Information

Get-WmiObject win32_networkadapterconfiguration -filter "ipenabled = 'True'"| 
Select PSComputername, DNSHostName, Description,
@{Name = "IPAddress";Expression = 
{[regex]$rx = "(\d{1,3}(\.?)){4}"
$rx.matches($_.IPAddress).Value}},MACAddress | ConvertTo-HTML -Head "<H2 style='color:green;'>Network Information</H2>" -body $a | Out-file $destination -Append

#Get Event logs

Get-EventLog -LogName Application -Newest 10 -EntryType Error | Select TimeGenerated, EventID, Source, Message |  ConvertTo-HTML -Head "<H2 style='color:green;'>Application Error Event Logs</H2>" -body $a | Out-file $file -Append
Get-EventLog -LogName Application -Newest 10 -EntryType Warning | Select TimeGenerated, EventID, Source, Message | ConvertTo-HTML -Head "<H2 style='color:green;'>Application Warning Event Logs</H2>" -body $a | Out-file $file -Append
Get-EventLog -LogName System -Newest 10 -EntryType Error | Select TimeGenerated, EventID, Source, Message | ConvertTo-HTML -Head "<H2 style='color:green;'>System Error Event Logs</H2>" -body $a | Out-file $file -Append
Get-EventLog -LogName System -Newest 10 -EntryType Warning | Select TimeGenerated, EventID, Source, Message | ConvertTo-HTML -Head "<H2 style='color:green;'>System Warning Event Logs</H2>" -body $a | Out-file $file -Append

#Get Stopped Services

Get-Service | Where {($_.Status) -eq "Stopped"} | Select Status, Name, DisplayName | ConvertTo-HTML -Head "<H2 style='color:green;'>Stopped Services</H2>" -body $a | Out-File $destination -Append

#Get Processes and CPU

Get-Process | Select Id, ProcessName, CPU | ConvertTo-HTML -Head "<H2 style='color:green;'>Processes & CPU</H2>" -body $a | Out-File $destination -Append

#Get Mapped Drives

Get-PSDrive | Where {$_.Used -ne $null} | Select Name, @{n='Used';e={[float]($_.Used/1GB)}}, @{n='Free';e={[float]($_.Free/1GB)}}, Root| ConvertTo-HTML -Head "<H2 style='color:green;'>Mapped Drives</H2>" -body $a | Out-File $destination -Append

#Get Printers

Get-Printer | Select Name, Type, PortName | ConvertTo-HTML -Head "<H2 style='color:green;'>Printers</H2>" -body $a | Out-file $destination -append


    
    try {
        #Send Email

        $Subject = "System Report for $agentname"
        $body = Get-Content $destination
 
        $message = new-object System.Net.Mail.MailMessage
        $message.IsBodyHTML = $true
        $message.From = $fromaddress
        $message.To.Add($toaddress)
        $message.Subject = $Subject
        $message.body = $body
        $smtp = new-object Net.Mail.SmtpClient($smtpserver, $port)
        $smtp.EnableSsl = $true
        $smtp.Credentials = New-Object System.Net.NetworkCredential($fromaddress, $Password)
        $smtp.Send($message)

        write-host "System Report successfully sent via email."

        exit 0
    }

    catch {
        write-host "An error occurrd. Please check your parameters, SMTP server name, or credentials and try again."
        exit 1
    }
}

exit $LASTEXITCODE