# https://github.com/knk90
# Installs Angry IP scanner using choco, runs a scan of the network and then uninstalls it

choco.exe install angryip -y
$PSDefaultParameterValues['*:Encoding'] = 'ascii'
$ips = get-netipaddress -AddressFamily ipv4 | select-object ipaddress
foreach ($i in $ips) {
    $split = $i.ipaddress.Split(".")
    $startrange = $split[0] + "." + $split[1] + "." + $split[2] + "." + "1"
    $endrange = $split[0] + "." + $split[1] + "." + $split[2] + "." + "254"
    $command = "`"c:\Program Files\Angry IP Scanner\ipscan.exe`" -f:range " + $startrange + " " + $endrange + " -s -q -o  c:\programdata\ipscanoutput.txt`""
    if ($startrange -notlike "*127.0*") {
        $command | Out-file -Encoding ASCII c:\programdata\ipscan.bat
        c:\programdata\ipscan.bat
        type c:\programdata\ipscanoutput.txt
    }
}
choco.exe uninstall angryip -y