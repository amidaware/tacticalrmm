$pools = Get-VirtualDisk | select -ExpandProperty HealthStatus

$err = $False

ForEach ($pool in $pools) {
    if ($pool -ne "Healthy") {
        $err = $True
    }
}

if ($err) {
    exit 1
}
else {
    exit 0
}