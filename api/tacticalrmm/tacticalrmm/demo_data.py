disks = [
    [
        {
            "free": "343.3G",
            "used": "121.9G",
            "total": "465.3G",
            "device": "C:",
            "fstype": "NTFS",
            "percent": 26,
        },
        {
            "free": "745.2G",
            "used": "1.1T",
            "total": "1.8T",
            "device": "D:",
            "fstype": "NTFS",
            "percent": 59,
        },
        {
            "free": "1.2T",
            "used": "669.7G",
            "total": "1.8T",
            "device": "F:",
            "fstype": "NTFS",
            "percent": 36,
        },
    ],
    [
        {
            "free": "516.7G",
            "used": "413.5G",
            "total": "930.2G",
            "device": "C:",
            "fstype": "NTFS",
            "percent": 44,
        }
    ],
    [
        {
            "free": "346.5G",
            "used": "129.1G",
            "total": "475.6G",
            "device": "C:",
            "fstype": "NTFS",
            "percent": 27,
        }
    ],
    [
        {
            "free": "84.2G",
            "used": "34.4G",
            "total": "118.6G",
            "device": "C:",
            "fstype": "NTFS",
            "percent": 29,
        }
    ],
]

disks_linux_pi = [
    {
        "free": "109.0 GB",
        "used": "3.4 GB",
        "total": "117.2 GB",
        "device": "/dev/mmcblk0p2",
        "fstype": "ext4",
        "percent": 3,
    },
    {
        "free": "203.8 MB",
        "used": "48.3 MB",
        "total": "252.0 MB",
        "device": "/dev/mmcblk0p1",
        "fstype": "vfat",
        "percent": 19,
    },
]

disks_linux_deb = [
    {
        "free": "9.8 GB",
        "used": "9.0 GB",
        "total": "19.8 GB",
        "device": "/dev/vda1",
        "fstype": "ext4",
        "percent": 47,
    },
    {
        "free": "62.6 GB",
        "used": "414.7 GB",
        "total": "503.0 GB",
        "device": "/dev/sda1",
        "fstype": "ext4",
        "percent": 86,
    },
]

disks_mac = [
    {
        "free": "94.2 GB",
        "used": "134.1 GB",
        "total": "228.3 GB",
        "device": "/dev/disk3s1s1",
        "fstype": "apfs",
        "percent": 58,
    },
    {
        "free": "481.6 MB",
        "used": "18.4 MB",
        "total": "500.0 MB",
        "device": "/dev/disk1s3",
        "fstype": "apfs",
        "percent": 3,
    },
    {
        "free": "3.4 GB",
        "used": "1.6 GB",
        "total": "5.0 GB",
        "device": "/dev/disk2s1",
        "fstype": "apfs",
        "percent": 32,
    },
    {
        "free": "94.2 GB",
        "used": "134.1 GB",
        "total": "228.3 GB",
        "device": "/dev/disk3s1",
        "fstype": "apfs",
        "percent": 58,
    },
]

wmi_deb = {
    "cpus": ["AMD Ryzen 9 3900X 12-Core Processor"],
    "gpus": ["Cirrus Logic GD 5446"],
    "disks": ["BUYVM SLAB SCSI HDD sda 512.0 GB", "0x1af4  virtio HDD vda 20.0 GB"],
    "local_ips": ["203.121.23.54/24", "fd70::253:70dc:fe65:143/64"],
    "make_model": "QEMU pc-i440fx-3.1",
}

wmi_pi = {
    "cpus": ["ARMv7 Processor rev 5 (v7l)"],
    "gpus": [],
    "disks": ["MMC SSD mmcblk0 119.4 GB"],
    "local_ips": ["192.168.33.10/24", "fe10::3332:4hgr:9634:1097/64"],
    "make_model": "Raspberry Pi 2 Model B Rev 1.1",
}

wmi_mac = {
    "cpus": ["Apple M1"],
    "gpus": [],
    "disks": [
        "Apple APPLE SSD AP0256Q SCSI SSD disk0 233.8 GB",
        "Apple APPLE SSD AP0256Q SCSI SSD disk1 500.0 MB",
        "Apple APPLE SSD AP0256Q SCSI SSD disk2 5.0 GB",
        "Apple APPLE SSD AP0256Q SCSI SSD disk3 228.3 GB",
    ],
    "local_ips": [
        "192.168.45.113/24",
        "fe80::476:c390:c8dc:11af/64",
    ],
    "make_model": "MacBookAir10,1",
}

check_network_loc_aware_ps1 = r"""
$networkstatus = Get-NetConnectionProfile | Select NetworkCategory | Out-String

if ($networkstatus.Contains("DomainAuthenticated")) {
    exit 0
} else {
    exit 1
}
"""

check_storage_pool_health_ps1 = r"""
$pools = Get-VirtualDisk | select -ExpandProperty HealthStatus

$err = $False

ForEach ($pool in $pools) {
    if ($pool -ne "Healthy") {
        $err = $True
    }
}

if ($err) {
    exit 1
} else {
    exit 0
}
"""

clear_print_spool_bat = r"""
@echo off

net stop spooler

del C:\Windows\System32\spool\printers\* /Q /F /S

net start spooler
"""

restart_nla_ps1 = r"""
Restart-Service NlaSvc -Force
"""

show_temp_dir_py = r"""
#!/usr/bin/python3

import os

temp_dir = "C:\\Windows\\Temp"
files = []
total = 0

with os.scandir(temp_dir) as it:
    for f in it:
        file = {}
        if not f.name.startswith(".") and f.is_file():

            total += 1
            stats = f.stat()

            file["name"] = f.name
            file["size"] = stats.st_size
            file["mtime"] = stats.st_mtime

            files.append(file)

    print(f"Total files: {total}\n")

    for file in files:
        print(file)

"""

redhat_insights = r"""
#!/bin/bash

# poor man’s red hat insights

# this script mimics what ansible does with red hat insights
# pass it a file containing all RHSA’s you want to patch, one per line
# it concatenates the advisories into a single yum command

if [ $# -eq 0 ]
then
  echo "Usage:  $0 <SRCFILE>"
  exit 1
fi

DT=$(date '+%m%d%Y%H%M')

SRCFILE=$1

for i in $(cat $SRCFILE)
do
  ARGS+=" --advisory $i"
done

CHECK="yum check-update -q"
CMD_CHECK="${CHECK}${ARGS}"

eval ${CMD_CHECK} >> /var/tmp/patch-$(hostname)-${DT}.output 2>&1

if [ $? -eq 100 ]; then
  UPDATE="yum update -d 2 -y"
  CMD_UPDATE="${UPDATE}${ARGS}"
  eval ${CMD_UPDATE} >> /var/tmp/patch-$(hostname)-${DT}.output 2>&1
else
  echo "error: exit code must be 100. fix yum errors and try again"
fi
"""

ping_success_output = """
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=28ms TTL=116
Reply from 8.8.8.8: bytes=32 time=26ms TTL=116
Reply from 8.8.8.8: bytes=32 time=29ms TTL=116
Reply from 8.8.8.8: bytes=32 time=23ms TTL=116

Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 23ms, Maximum = 29ms, Average = 26ms
"""

ping_fail_output = """
Pinging 10.42.33.2 with 32 bytes of data:
Request timed out.
Request timed out.
Request timed out.
Request timed out.

Ping statistics for 10.42.33.2:
Packets: Sent = 4, Received = 0, Lost = 4 (100% loss),
"""

spooler_stdout = """
SERVICE_NAME: spooler 
    TYPE               : 110  WIN32_OWN_PROCESS  (interactive)
    STATE              : 3  STOP_PENDING 
                            (NOT_STOPPABLE, NOT_PAUSABLE, IGNORES_SHUTDOWN)
    WIN32_EXIT_CODE    : 0  (0x0)
    SERVICE_EXIT_CODE  : 0  (0x0)
    CHECKPOINT         : 0x0
    WAIT_HINT          : 0x0
Deleted file - C:\Windows\System32\spool\printers\FP00004.SHD
Deleted file - C:\Windows\System32\spool\printers\FP00004.SPL

SERVICE_NAME: spooler 
    TYPE               : 110  WIN32_OWN_PROCESS  (interactive)
    STATE              : 2  START_PENDING 
                            (NOT_STOPPABLE, NOT_PAUSABLE, IGNORES_SHUTDOWN)
    WIN32_EXIT_CODE    : 0  (0x0)
    SERVICE_EXIT_CODE  : 0  (0x0)
    CHECKPOINT         : 0x0
    WAIT_HINT          : 0x7d0
    PID                : 10536
    FLAGS              :
"""


temp_dir_stdout = """
Total files: 427

{'name': '2E71.tmp', 'size': 7430272, 'mtime': 1581925416.2497344}
{'name': 'AdobeARM.log', 'size': 29451, 'mtime': 1594655619.9011872}
{'name': 'adobegc.log', 'size': 10231328, 'mtime': 1595040481.91346}
{'name': 'adobegc_a00168', 'size': 827, 'mtime': 1587681946.9771478}
{'name': 'adobegc_a00736', 'size': 827, 'mtime': 1588706044.6594567}
{'name': 'adobegc_a01612', 'size': 827, 'mtime': 1580168032.7042644}
{'name': 'adobegc_a01872', 'size': 827, 'mtime': 1588695409.1667633}
{'name': 'adobegc_a02040', 'size': 827, 'mtime': 1586472391.868406}
{'name': 'adobegc_a02076', 'size': 827, 'mtime': 1580250789.654343}
{'name': 'adobegc_a02316', 'size': 827, 'mtime': 1584469722.280189}
{'name': 'adobegc_a02840', 'size': 827, 'mtime': 1580168195.0954776}
{'name': 'adobegc_a02844', 'size': 827, 'mtime': 1588704553.4443035}
{'name': 'adobegc_a02940', 'size': 827, 'mtime': 1588705125.4622736}
{'name': 'adobegc_a03388', 'size': 827, 'mtime': 1588694931.7341642}
{'name': 'adobegc_a03444', 'size': 827, 'mtime': 1588694575.377482}
{'name': 'adobegc_a03468', 'size': 827, 'mtime': 1588705816.5495117}
{'name': 'adobegc_a03516', 'size': 827, 'mtime': 1588695236.1638494}
{'name': 'adobegc_a03660', 'size': 827, 'mtime': 1588694714.0769584}
{'name': 'adobegc_a03668', 'size': 827, 'mtime': 1588791976.2615259}
{'name': 'adobegc_a03984', 'size': 827, 'mtime': 1588708060.4916122}
{'name': 'adobegc_a04244', 'size': 827, 'mtime': 1588882348.195425}
{'name': 'adobegc_a04296', 'size': 827, 'mtime': 1587595547.000954}
{'name': 'adobegc_a04400', 'size': 827, 'mtime': 1588698785.5022683}
{'name': 'adobegc_a04476', 'size': 827, 'mtime': 1588696181.497377}
{'name': 'adobegc_a04672', 'size': 827, 'mtime': 1588707309.2342112}
{'name': 'adobegc_a05072', 'size': 827, 'mtime': 1588718744.760823}
{'name': 'adobegc_a05308', 'size': 827, 'mtime': 1588884352.0702107}
{'name': 'adobegc_a05372', 'size': 827, 'mtime': 1587571313.9485312}
{'name': 'adobegc_a06196', 'size': 826, 'mtime': 1594654959.318391}
{'name': 'adobegc_a07432', 'size': 827, 'mtime': 1588887412.235366}
{'name': 'adobegc_a07592', 'size': 827, 'mtime': 1587768346.7856867}
{'name': 'adobegc_a08336', 'size': 827, 'mtime': 1580251587.8173583}
{'name': 'adobegc_a08540', 'size': 826, 'mtime': 1590517886.4135766}
{'name': 'adobegc_a08676', 'size': 827, 'mtime': 1588796865.261678}
{'name': 'adobegc_a08788', 'size': 827, 'mtime': 1586385998.4148164}
{'name': 'adobegc_a09164', 'size': 827, 'mtime': 1588882638.920801}
{'name': 'adobegc_a10672', 'size': 827, 'mtime': 1580142397.240663}
{'name': 'adobegc_a11260', 'size': 827, 'mtime': 1588791820.5066414}
{'name': 'adobegc_a12180', 'size': 827, 'mtime': 1580146831.0441327}
{'name': 'adobegc_a14468', 'size': 827, 'mtime': 1585674106.878755}
{'name': 'adobegc_a14596', 'size': 827, 'mtime': 1580510788.5562158}
{'name': 'adobegc_a15124', 'size': 826, 'mtime': 1590523889.367007}
{'name': 'adobegc_a15936', 'size': 827, 'mtime': 1580256796.572934}
{'name': 'adobegc_a15992', 'size': 826, 'mtime': 1594664396.6619377}
{'name': 'adobegc_a16976', 'size': 827, 'mtime': 1585674384.4933422}
{'name': 'adobegc_a18972', 'size': 826, 'mtime': 1594748694.4924471}
{'name': 'adobegc_a19836', 'size': 827, 'mtime': 1588880974.3856514}
{'name': 'adobegc_a20168', 'size': 827, 'mtime': 1580256300.931633}
{'name': 'adobegc_a20424', 'size': 826, 'mtime': 1590619548.096738}
{'name': 'adobegc_a20476', 'size': 827, 'mtime': 1580241090.30506}
{'name': 'adobegc_a20696', 'size': 827, 'mtime': 1588883054.266526}
{'name': 'adobegc_a21160', 'size': 827, 'mtime': 1585867545.8835862}
{'name': 'adobegc_a21600', 'size': 827, 'mtime': 1584546053.6350517}
{'name': 'adobegc_a21604', 'size': 827, 'mtime': 1585781145.016732}
{'name': 'adobegc_a23208', 'size': 826, 'mtime': 1594766767.8597474}
{'name': 'adobegc_a23792', 'size': 827, 'mtime': 1587748006.602304}
{'name': 'adobegc_a24996', 'size': 827, 'mtime': 1580337748.2107458}
{'name': 'adobegc_a25280', 'size': 827, 'mtime': 1589561457.17108}
{'name': 'adobegc_a25716', 'size': 827, 'mtime': 1586558746.818827}
{'name': 'adobegc_a26788', 'size': 827, 'mtime': 1589317959.1261017}
{'name': 'adobegc_a29788', 'size': 826, 'mtime': 1594853168.0936923}
{'name': 'adobegc_a30772', 'size': 827, 'mtime': 1586645146.8381186}
{'name': 'adobegc_a30868', 'size': 826, 'mtime': 1590705947.4294834}
{'name': 'adobegc_a33340', 'size': 827, 'mtime': 1580424388.6278617}
{'name': 'adobegc_a34072', 'size': 826, 'mtime': 1591036884.930815}
{'name': 'adobegc_a34916', 'size': 827, 'mtime': 1589063225.3951604}
{'name': 'adobegc_a36312', 'size': 826, 'mtime': 1590792347.1066074}
{'name': 'adobegc_a36732', 'size': 827, 'mtime': 1587941146.7667546}
{'name': 'adobegc_a37684', 'size': 826, 'mtime': 1591051545.0491257}
{'name': 'adobegc_a38820', 'size': 826, 'mtime': 1594939568.850206}
{'name': 'adobegc_a39800', 'size': 827, 'mtime': 1586731547.200965}
{'name': 'adobegc_a39968', 'size': 827, 'mtime': 1585953945.0148494}
{'name': 'adobegc_a40276', 'size': 827, 'mtime': 1580774658.3211977}
{'name': 'adobegc_a40312', 'size': 827, 'mtime': 1589237146.946895}
{'name': 'adobegc_a40988', 'size': 827, 'mtime': 1586817946.949773}
{'name': 'adobegc_a40992', 'size': 827, 'mtime': 1580770793.4948478}
{'name': 'adobegc_a41180', 'size': 827, 'mtime': 1588027546.7357743}
{'name': 'adobegc_a41188', 'size': 826, 'mtime': 1595009475.295114}
{'name': 'adobegc_a41640', 'size': 826, 'mtime': 1590878747.5881732}
{'name': 'adobegc_a42100', 'size': 827, 'mtime': 1589150748.9527063}
{'name': 'adobegc_a43012', 'size': 827, 'mtime': 1580683588.5658195}
{'name': 'adobegc_a44676', 'size': 827, 'mtime': 1580597188.6451297}
{'name': 'adobegc_a45184', 'size': 827, 'mtime': 1586904346.5828853}
{'name': 'adobegc_a45308', 'size': 826, 'mtime': 1595025969.4777381}
{'name': 'adobegc_a46804', 'size': 827, 'mtime': 1580772007.5569854}
{'name': 'adobegc_a47368', 'size': 827, 'mtime': 1588100330.3886814}
{'name': 'adobegc_a47428', 'size': 827, 'mtime': 1589307202.4241476}
{'name': 'adobegc_a48120', 'size': 827, 'mtime': 1587061429.3050117}
{'name': 'adobegc_a48264', 'size': 827, 'mtime': 1586040345.9605994}
{'name': 'adobegc_a49348', 'size': 827, 'mtime': 1589308572.5917764}
{'name': 'adobegc_a50068', 'size': 827, 'mtime': 1589823616.2651317}
{'name': 'adobegc_a50512', 'size': 827, 'mtime': 1588113946.9230535}
{'name': 'adobegc_a54396', 'size': 826, 'mtime': 1590965147.3472395}
{'name': 'adobegc_a55764', 'size': 827, 'mtime': 1586126745.5002806}
{'name': 'adobegc_a56868', 'size': 827, 'mtime': 1584988994.5648835}
{'name': 'adobegc_a56920', 'size': 827, 'mtime': 1589826940.2840052}
{'name': 'adobegc_a58060', 'size': 827, 'mtime': 1588200346.9590664}
{'name': 'adobegc_a58664', 'size': 827, 'mtime': 1580772553.408082}
{'name': 'adobegc_a58836', 'size': 827, 'mtime': 1586213145.9856122}
{'name': 'adobegc_a58952', 'size': 827, 'mtime': 1580769957.2542257}
{'name': 'adobegc_a59448', 'size': 827, 'mtime': 1586191309.3788278}
{'name': 'adobegc_a59920', 'size': 827, 'mtime': 1580837382.8384278}
{'name': 'adobegc_a60092', 'size': 827, 'mtime': 1589820894.3119876}
{'name': 'adobegc_a60188', 'size': 827, 'mtime': 1580773319.7630682}
{'name': 'adobegc_a60376', 'size': 827, 'mtime': 1584984234.995152}
{'name': 'adobegc_a60836', 'size': 827, 'mtime': 1586990747.0581498}
{'name': 'adobegc_a61768', 'size': 826, 'mtime': 1591035116.5898964}
{'name': 'adobegc_a62200', 'size': 827, 'mtime': 1586195417.8275757}
{'name': 'adobegc_a62432', 'size': 827, 'mtime': 1580942790.5409286}
{'name': 'adobegc_a65288', 'size': 827, 'mtime': 1588373147.0190327}
{'name': 'adobegc_a65332', 'size': 827, 'mtime': 1580838023.0994027}
{'name': 'adobegc_a65672', 'size': 826, 'mtime': 1591133604.032657}
{'name': 'adobegc_a66164', 'size': 827, 'mtime': 1580837511.0639248}
{'name': 'adobegc_a66532', 'size': 827, 'mtime': 1587077146.9995973}
{'name': 'adobegc_a66744', 'size': 827, 'mtime': 1587061281.624075}
{'name': 'adobegc_a68000', 'size': 826, 'mtime': 1591137947.4248047}
{'name': 'adobegc_a68072', 'size': 827, 'mtime': 1589928347.070936}
{'name': 'adobegc_a68720', 'size': 827, 'mtime': 1581029189.2618403}
{'name': 'adobegc_a68848', 'size': 827, 'mtime': 1587163546.6515636}
{'name': 'adobegc_a69732', 'size': 827, 'mtime': 1580930519.3353608}
{'name': 'adobegc_a70528', 'size': 827, 'mtime': 1589841947.731212}
{'name': 'adobegc_a71096', 'size': 827, 'mtime': 1580920745.8008296}
{'name': 'adobegc_a71132', 'size': 827, 'mtime': 1586299545.3437998}
{'name': 'adobegc_a71648', 'size': 827, 'mtime': 1581031075.2702963}
{'name': 'adobegc_a72972', 'size': 827, 'mtime': 1588626359.7385614}
{'name': 'adobegc_a75840', 'size': 826, 'mtime': 1591373471.8618608}
{'name': 'adobegc_a76096', 'size': 827, 'mtime': 1581030280.123038}
{'name': 'adobegc_a76636', 'size': 827, 'mtime': 1581010194.8814292}
{'name': 'adobegc_a76928', 'size': 827, 'mtime': 1586368563.2366085}
{'name': 'adobegc_a78272', 'size': 827, 'mtime': 1588459547.364358}
{'name': 'adobegc_a78448', 'size': 827, 'mtime': 1589755547.709028}
{'name': 'adobegc_a78868', 'size': 827, 'mtime': 1587249947.0512784}
{'name': 'adobegc_a79232', 'size': 827, 'mtime': 1590014747.2459671}
{'name': 'adobegc_a80708', 'size': 827, 'mtime': 1587854746.995757}
{'name': 'adobegc_a81928', 'size': 826, 'mtime': 1591387037.7909682}
{'name': 'adobegc_a82640', 'size': 827, 'mtime': 1588620563.6037686}
{'name': 'adobegc_a84680', 'size': 827, 'mtime': 1588622988.5522242}
{'name': 'adobegc_a86668', 'size': 827, 'mtime': 1588632347.3290584}
{'name': 'adobegc_a87760', 'size': 826, 'mtime': 1591389738.9057505}
{'name': 'adobegc_a87796', 'size': 827, 'mtime': 1588620113.9931662}
{'name': 'adobegc_a88000', 'size': 827, 'mtime': 1587336346.5873897}
{'name': 'adobegc_a88772', 'size': 827, 'mtime': 1588545946.2672083}
{'name': 'adobegc_a88864', 'size': 826, 'mtime': 1591388571.4809685}
{'name': 'adobegc_a90492', 'size': 826, 'mtime': 1591569945.3237975}
{'name': 'adobegc_a90536', 'size': 827, 'mtime': 1588615525.34365}
{'name': 'adobegc_a90696', 'size': 827, 'mtime': 1588618638.6518161}
{'name': 'adobegc_a92020', 'size': 827, 'mtime': 1588626079.888435}
{'name': 'adobegc_a92036', 'size': 827, 'mtime': 1588883650.2998574}
{'name': 'adobegc_a92060', 'size': 827, 'mtime': 1587422746.7982752}
{'name': 'adobegc_a92332', 'size': 827, 'mtime': 1588617429.6228204}
{'name': 'adobegc_a92708', 'size': 827, 'mtime': 1588621683.480289}
{'name': 'adobegc_a93576', 'size': 827, 'mtime': 1588611949.1138964}
{'name': 'adobegc_a93952', 'size': 826, 'mtime': 1591483547.0099566}
{'name': 'adobegc_a93968', 'size': 827, 'mtime': 1588619947.3429031}
{'name': 'adobegc_a94188', 'size': 827, 'mtime': 1588625869.6090748}
{'name': 'adobegc_a94428', 'size': 827, 'mtime': 1588625083.0555425}
{'name': 'adobegc_a94564', 'size': 827, 'mtime': 1587400776.9892576}
{'name': 'adobegc_a94620', 'size': 827, 'mtime': 1588616005.2649503}
{'name': 'adobegc_a94672', 'size': 827, 'mtime': 1588608305.686614}
{'name': 'adobegc_a95104', 'size': 827, 'mtime': 1588619862.1936185}
{'name': 'adobegc_a95268', 'size': 827, 'mtime': 1588618316.1273627}
{'name': 'adobegc_a95992', 'size': 827, 'mtime': 1588625699.327125}
{'name': 'adobegc_a96116', 'size': 827, 'mtime': 1588625465.4000483}
{'name': 'adobegc_a96140', 'size': 827, 'mtime': 1588707579.585134}
{'name': 'adobegc_a96196', 'size': 827, 'mtime': 1588616659.9653125}
{'name': 'adobegc_a96264', 'size': 827, 'mtime': 1588624388.424492}
{'name': 'adobegc_a96396', 'size': 827, 'mtime': 1588619230.3394928}
{'name': 'adobegc_a97428', 'size': 827, 'mtime': 1587509147.0930684}
{'name': 'adobegc_a97480', 'size': 827, 'mtime': 1589669147.1720312}
{'name': 'adobegc_a97532', 'size': 827, 'mtime': 1588623710.0535893}
{'name': 'adobegc_a97576', 'size': 827, 'mtime': 1588699829.405278}
{'name': 'adobegc_a97888', 'size': 827, 'mtime': 1588700236.4738493}
{'name': 'adobegc_a97936', 'size': 827, 'mtime': 1588705581.3051977}
{'name': 'adobegc_a98628', 'size': 827, 'mtime': 1588707770.5158248}
{'name': 'adobegc_a98676', 'size': 827, 'mtime': 1588707160.0849242}
{'name': 'adobegc_a99320', 'size': 827, 'mtime': 1588286747.3271153}
{'name': 'adobegc_a99416', 'size': 827, 'mtime': 1588705913.0032701}
{'name': 'adobegc_a99776', 'size': 827, 'mtime': 1588695055.6383822}
{'name': 'adobegc_a99944', 'size': 827, 'mtime': 1588700090.9956398}
{'name': 'adobegc_b00736', 'size': 827, 'mtime': 1588706066.725238}
{'name': 'adobegc_b01872', 'size': 827, 'mtime': 1588695416.625433}
{'name': 'adobegc_b02844', 'size': 827, 'mtime': 1588704612.7520032}
{'name': 'adobegc_b02940', 'size': 827, 'mtime': 1588705218.2862568}
{'name': 'adobegc_b03516', 'size': 827, 'mtime': 1588695279.1507645}
{'name': 'adobegc_b03668', 'size': 827, 'mtime': 1588791984.8225732}
{'name': 'adobegc_b03984', 'size': 827, 'mtime': 1588708170.4855063}
{'name': 'adobegc_b04400', 'size': 827, 'mtime': 1588698790.8114717}
{'name': 'adobegc_b06196', 'size': 826, 'mtime': 1594655070.3379285}
{'name': 'adobegc_b08540', 'size': 826, 'mtime': 1590517989.972172}
{'name': 'adobegc_b08676', 'size': 827, 'mtime': 1588796952.7518158}
{'name': 'adobegc_b11260', 'size': 827, 'mtime': 1588791830.28458}
{'name': 'adobegc_b12180', 'size': 827, 'mtime': 1580146854.104489}
{'name': 'adobegc_b14468', 'size': 827, 'mtime': 1585674135.6150348}
{'name': 'adobegc_b15992', 'size': 826, 'mtime': 1594664406.76352}
{'name': 'adobegc_b18972', 'size': 826, 'mtime': 1594748752.0301268}
{'name': 'adobegc_b20424', 'size': 826, 'mtime': 1590619550.6114154}
{'name': 'adobegc_b20696', 'size': 827, 'mtime': 1588883091.2836785}
{'name': 'adobegc_b25280', 'size': 827, 'mtime': 1589561471.058807}
{'name': 'adobegc_b26788', 'size': 827, 'mtime': 1589318049.2721062}
{'name': 'adobegc_b30868', 'size': 826, 'mtime': 1590705949.9086082}
{'name': 'adobegc_b34072', 'size': 826, 'mtime': 1591036916.1677504}
{'name': 'adobegc_b36312', 'size': 826, 'mtime': 1590792349.6286027}
{'name': 'adobegc_b37684', 'size': 826, 'mtime': 1591051547.7088954}
{'name': 'adobegc_b41188', 'size': 826, 'mtime': 1595009499.2530031}
{'name': 'adobegc_b41640', 'size': 826, 'mtime': 1590878750.2055979}
{'name': 'adobegc_b48120', 'size': 827, 'mtime': 1587061437.18547}
{'name': 'adobegc_b49348', 'size': 827, 'mtime': 1589308608.9336922}
{'name': 'adobegc_b50068', 'size': 827, 'mtime': 1589823624.2151668}
{'name': 'adobegc_b54396', 'size': 826, 'mtime': 1590965149.8471487}
{'name': 'adobegc_b56868', 'size': 827, 'mtime': 1584989020.8257363}
{'name': 'adobegc_b56920', 'size': 827, 'mtime': 1589826973.5304308}
{'name': 'adobegc_b58952', 'size': 827, 'mtime': 1580770043.2167466}
{'name': 'adobegc_b59448', 'size': 827, 'mtime': 1586191317.2202032}
{'name': 'adobegc_b60376', 'size': 827, 'mtime': 1584984269.807791}
{'name': 'adobegc_b68000', 'size': 826, 'mtime': 1591137949.8555748}
{'name': 'adobegc_b68072', 'size': 827, 'mtime': 1589928349.6981187}
{'name': 'adobegc_b70528', 'size': 827, 'mtime': 1589841950.8458745}
{'name': 'adobegc_b71096', 'size': 827, 'mtime': 1580920761.6914532}
{'name': 'adobegc_b72972', 'size': 827, 'mtime': 1588626390.183644}
{'name': 'adobegc_b76636', 'size': 827, 'mtime': 1581010200.9350817}
{'name': 'adobegc_b78448', 'size': 827, 'mtime': 1589755550.4021}
{'name': 'adobegc_b79232', 'size': 827, 'mtime': 1590014749.9412005}
{'name': 'adobegc_b82640', 'size': 827, 'mtime': 1588620586.923453}
{'name': 'adobegc_b84680', 'size': 827, 'mtime': 1588623002.5390074}
{'name': 'adobegc_b87796', 'size': 827, 'mtime': 1588620149.2323031}
{'name': 'adobegc_b90536', 'size': 827, 'mtime': 1588615561.6454446}
{'name': 'adobegc_b90696', 'size': 827, 'mtime': 1588618646.516128}
{'name': 'adobegc_b92020', 'size': 827, 'mtime': 1588626116.4113202}
{'name': 'adobegc_b92332', 'size': 827, 'mtime': 1588617466.6833763}
{'name': 'adobegc_b92708', 'size': 827, 'mtime': 1588621723.2322977}
{'name': 'adobegc_b93968', 'size': 827, 'mtime': 1588619970.3566632}
{'name': 'adobegc_b94188', 'size': 827, 'mtime': 1588625878.801097}
{'name': 'adobegc_b94428', 'size': 827, 'mtime': 1588625091.057683}
{'name': 'adobegc_b94564', 'size': 827, 'mtime': 1587400800.9059412}
{'name': 'adobegc_b95268', 'size': 827, 'mtime': 1588618334.0967414}
{'name': 'adobegc_b95992', 'size': 827, 'mtime': 1588625737.972303}
{'name': 'adobegc_b96116', 'size': 827, 'mtime': 1588625472.4204888}
{'name': 'adobegc_b96196', 'size': 827, 'mtime': 1588616768.8672354}
{'name': 'adobegc_b96396', 'size': 827, 'mtime': 1588619236.3330257}
{'name': 'adobegc_b97480', 'size': 827, 'mtime': 1589669149.7252228}
{'name': 'adobegc_b97532', 'size': 827, 'mtime': 1588623738.1396592}
{'name': 'adobegc_b97576', 'size': 827, 'mtime': 1588699862.141512}
{'name': 'adobegc_b97888', 'size': 827, 'mtime': 1588700318.3893816}
{'name': 'adobegc_b97936', 'size': 827, 'mtime': 1588705599.7656307}
{'name': 'adobegc_b98628', 'size': 827, 'mtime': 1588707795.8756163}
{'name': 'adobegc_b99416', 'size': 827, 'mtime': 1588705935.8479679}
{'name': 'adobegc_b99776', 'size': 827, 'mtime': 1588695083.277253}
{'name': 'adobegc_b99944', 'size': 827, 'mtime': 1588700116.4428499}
{'name': 'adobegc_c00736', 'size': 827, 'mtime': 1588706144.523482}
{'name': 'adobegc_c01872', 'size': 827, 'mtime': 1588695424.6709175}
{'name': 'adobegc_c02844', 'size': 827, 'mtime': 1588704655.3452854}
{'name': 'adobegc_c02940', 'size': 827, 'mtime': 1588705301.4180279}
{'name': 'adobegc_c03984', 'size': 827, 'mtime': 1588708227.6767087}
{'name': 'adobegc_c04400', 'size': 827, 'mtime': 1588698805.7789137}
{'name': 'adobegc_c08676', 'size': 827, 'mtime': 1588796987.8076794}
{'name': 'adobegc_c11260', 'size': 827, 'mtime': 1588791857.2477975}
{'name': 'adobegc_c12180', 'size': 827, 'mtime': 1580146876.464384}
{'name': 'adobegc_c15992', 'size': 826, 'mtime': 1594664430.9030519}
{'name': 'adobegc_c20696', 'size': 827, 'mtime': 1588883097.26129}
{'name': 'adobegc_c25280', 'size': 827, 'mtime': 1589561487.9573958}
{'name': 'adobegc_c26788', 'size': 827, 'mtime': 1589318109.375684}
{'name': 'adobegc_c34072', 'size': 826, 'mtime': 1591036933.363417}
{'name': 'adobegc_c48120', 'size': 827, 'mtime': 1587061454.0755453}
{'name': 'adobegc_c56920', 'size': 827, 'mtime': 1589826993.0616467}
{'name': 'adobegc_c59448', 'size': 827, 'mtime': 1586191349.8506114}
{'name': 'adobegc_c60376', 'size': 827, 'mtime': 1584984292.1612866}
{'name': 'adobegc_c72972', 'size': 827, 'mtime': 1588626413.0896137}
{'name': 'adobegc_c76636', 'size': 827, 'mtime': 1581010218.0554078}
{'name': 'adobegc_c82640', 'size': 827, 'mtime': 1588620613.321756}
{'name': 'adobegc_c84680', 'size': 827, 'mtime': 1588623117.9436429}
{'name': 'adobegc_c87796', 'size': 827, 'mtime': 1588620230.1520216}
{'name': 'adobegc_c92020', 'size': 827, 'mtime': 1588626141.4125187}
{'name': 'adobegc_c92332', 'size': 827, 'mtime': 1588617496.3456864}
{'name': 'adobegc_c93968', 'size': 827, 'mtime': 1588619998.5936964}
{'name': 'adobegc_c94428', 'size': 827, 'mtime': 1588625116.0481493}
{'name': 'adobegc_c94564', 'size': 827, 'mtime': 1587400814.941493}
{'name': 'adobegc_c95268', 'size': 827, 'mtime': 1588618430.4614644}
{'name': 'adobegc_c95992', 'size': 827, 'mtime': 1588625744.1483426}
{'name': 'adobegc_c97532', 'size': 827, 'mtime': 1588623768.123971}
{'name': 'adobegc_c97576', 'size': 827, 'mtime': 1588699912.811693}
{'name': 'adobegc_c98628', 'size': 827, 'mtime': 1588707823.850915}
{'name': 'adobegc_c99416', 'size': 827, 'mtime': 1588705942.7441413}
{'name': 'adobegc_c99944', 'size': 827, 'mtime': 1588700140.0327764}
{'name': 'adobegc_d00736', 'size': 827, 'mtime': 1588706212.1906126}
{'name': 'adobegc_d02844', 'size': 827, 'mtime': 1588704712.9487145}
{'name': 'adobegc_d02940', 'size': 827, 'mtime': 1588705320.1099153}
{'name': 'adobegc_d03984', 'size': 827, 'mtime': 1588708248.2397952}
{'name': 'adobegc_d04400', 'size': 827, 'mtime': 1588698820.0670853}
{'name': 'adobegc_d12180', 'size': 827, 'mtime': 1580146895.6547296}
{'name': 'adobegc_d15992', 'size': 826, 'mtime': 1594664447.5050478}
{'name': 'adobegc_d20696', 'size': 827, 'mtime': 1588883151.742091}
{'name': 'adobegc_d34072', 'size': 826, 'mtime': 1591036946.3382795}
{'name': 'adobegc_d56920', 'size': 827, 'mtime': 1589827011.6453788}
{'name': 'adobegc_d59448', 'size': 827, 'mtime': 1586191396.4112055}
{'name': 'adobegc_d60376', 'size': 827, 'mtime': 1584984310.4665244}
{'name': 'adobegc_d72972', 'size': 827, 'mtime': 1588626429.153277}
{'name': 'adobegc_d76636', 'size': 827, 'mtime': 1581010315.7584887}
{'name': 'adobegc_d82640', 'size': 827, 'mtime': 1588620653.094543}
{'name': 'adobegc_d84680', 'size': 827, 'mtime': 1588623140.4772713}
{'name': 'adobegc_d87796', 'size': 827, 'mtime': 1588620294.8475337}
{'name': 'adobegc_d92020', 'size': 827, 'mtime': 1588626228.1945815}
{'name': 'adobegc_d94428', 'size': 827, 'mtime': 1588625122.2906866}
{'name': 'adobegc_d94564', 'size': 827, 'mtime': 1587400828.0741277}
{'name': 'adobegc_d95268', 'size': 827, 'mtime': 1588618440.307652}
{'name': 'adobegc_d97532', 'size': 827, 'mtime': 1588623787.4921527}
{'name': 'adobegc_d97576', 'size': 827, 'mtime': 1588699931.81901}
{'name': 'adobegc_d98628', 'size': 827, 'mtime': 1588707855.1049612}
{'name': 'adobegc_e00736', 'size': 827, 'mtime': 1588706245.611989}
{'name': 'adobegc_e02844', 'size': 827, 'mtime': 1588704734.7796671}
{'name': 'adobegc_e02940', 'size': 827, 'mtime': 1588705346.8015952}
{'name': 'adobegc_e03984', 'size': 827, 'mtime': 1588708267.3839262}
{'name': 'adobegc_e04400', 'size': 827, 'mtime': 1588698844.0438626}
{'name': 'adobegc_e12180', 'size': 827, 'mtime': 1580146918.2748847}
{'name': 'adobegc_e15992', 'size': 826, 'mtime': 1594664462.674065}
{'name': 'adobegc_e34072', 'size': 826, 'mtime': 1591036960.5743244}
{'name': 'adobegc_e56920', 'size': 827, 'mtime': 1589827029.9772768}
{'name': 'adobegc_e59448', 'size': 827, 'mtime': 1586191423.5797856}
{'name': 'adobegc_e60376', 'size': 827, 'mtime': 1584984320.550245}
{'name': 'adobegc_e72972', 'size': 827, 'mtime': 1588626449.11985}
{'name': 'adobegc_e82640', 'size': 827, 'mtime': 1588620658.7476456}
{'name': 'adobegc_e84680', 'size': 827, 'mtime': 1588623162.9596686}
{'name': 'adobegc_e87796', 'size': 827, 'mtime': 1588620363.3213055}
{'name': 'adobegc_e92020', 'size': 827, 'mtime': 1588626236.2562673}
{'name': 'adobegc_e94428', 'size': 827, 'mtime': 1588625177.8788607}
{'name': 'adobegc_e94564', 'size': 827, 'mtime': 1587400848.3485818}
{'name': 'adobegc_e97532', 'size': 827, 'mtime': 1588623800.5197835}
{'name': 'adobegc_e97576', 'size': 827, 'mtime': 1588699954.884931}
{'name': 'adobegc_e98628', 'size': 827, 'mtime': 1588707930.3610473}
{'name': 'adobegc_f00736', 'size': 827, 'mtime': 1588706262.6876884}
{'name': 'adobegc_f02844', 'size': 827, 'mtime': 1588704857.8128686}
{'name': 'adobegc_f02940', 'size': 827, 'mtime': 1588705386.8754816}
{'name': 'adobegc_f03984', 'size': 827, 'mtime': 1588708377.0388029}
{'name': 'adobegc_f04400', 'size': 827, 'mtime': 1588698865.876907}
{'name': 'adobegc_f12180', 'size': 827, 'mtime': 1580146941.4048574}
{'name': 'adobegc_f15992', 'size': 826, 'mtime': 1594664480.5364697}
{'name': 'adobegc_f59448', 'size': 827, 'mtime': 1586191468.308414}
{'name': 'adobegc_f60376', 'size': 827, 'mtime': 1584984342.4760692}
{'name': 'adobegc_f72972', 'size': 827, 'mtime': 1588626520.413051}
{'name': 'adobegc_f82640', 'size': 827, 'mtime': 1588620707.6957185}
{'name': 'adobegc_f84680', 'size': 827, 'mtime': 1588623185.9664042}
{'name': 'adobegc_f87796', 'size': 827, 'mtime': 1588620372.2095447}
{'name': 'adobegc_f94428', 'size': 827, 'mtime': 1588625198.4473124}
{'name': 'adobegc_f98628', 'size': 827, 'mtime': 1588707956.3923628}
{'name': 'adobegc_g00736', 'size': 827, 'mtime': 1588706340.7434888}
{'name': 'adobegc_g02844', 'size': 827, 'mtime': 1588704879.0104535}
{'name': 'adobegc_g02940', 'size': 827, 'mtime': 1588705417.8788993}
{'name': 'adobegc_g03984', 'size': 827, 'mtime': 1588708394.9106903}
{'name': 'adobegc_g04400', 'size': 827, 'mtime': 1588698895.7362301}
{'name': 'adobegc_g12180', 'size': 827, 'mtime': 1580146949.484896}
{'name': 'adobegc_g72972', 'size': 827, 'mtime': 1588626624.4677527}
{'name': 'adobegc_g82640', 'size': 827, 'mtime': 1588620723.5959775}
{'name': 'adobegc_g84680', 'size': 827, 'mtime': 1588623225.1320856}
{'name': 'adobegc_g87796', 'size': 827, 'mtime': 1588620425.5512018}
{'name': 'adobegc_g94428', 'size': 827, 'mtime': 1588625228.557094}
{'name': 'adobegc_h00736', 'size': 827, 'mtime': 1588706456.0406094}
{'name': 'adobegc_h02844', 'size': 827, 'mtime': 1588704948.776196}
{'name': 'adobegc_h02940', 'size': 827, 'mtime': 1588705450.0687082}
{'name': 'adobegc_h03984', 'size': 827, 'mtime': 1588708415.418625}
{'name': 'adobegc_h04400', 'size': 827, 'mtime': 1588698929.891593}
{'name': 'adobegc_h12180', 'size': 827, 'mtime': 1580146955.5651238}
{'name': 'adobegc_h82640', 'size': 827, 'mtime': 1588620743.5954738}
{'name': 'adobegc_h84680', 'size': 827, 'mtime': 1588623352.3280022}
{'name': 'adobegc_h87796', 'size': 827, 'mtime': 1588620447.1586652}
{'name': 'adobegc_h94428', 'size': 827, 'mtime': 1588625239.4658115}
{'name': 'adobegc_i00736', 'size': 827, 'mtime': 1588706484.0562284}
{'name': 'adobegc_i02940', 'size': 827, 'mtime': 1588705465.7495365}
{'name': 'adobegc_i03984', 'size': 827, 'mtime': 1588708539.8739815}
{'name': 'adobegc_i04400', 'size': 827, 'mtime': 1588698952.9581492}
{'name': 'adobegc_i12180', 'size': 827, 'mtime': 1580147014.8754144}
{'name': 'adobegc_i82640', 'size': 827, 'mtime': 1588620751.6867297}
{'name': 'adobegc_i84680', 'size': 827, 'mtime': 1588623400.7245765}
{'name': 'adobegc_i87796', 'size': 827, 'mtime': 1588620470.659986}
{'name': 'adobegc_i94428', 'size': 827, 'mtime': 1588625266.8207235}
{'name': 'adobegc_j00736', 'size': 827, 'mtime': 1588706506.187664}
{'name': 'adobegc_j03984', 'size': 827, 'mtime': 1588708569.6812017}
{'name': 'adobegc_j04400', 'size': 827, 'mtime': 1588698970.8107784}
{'name': 'adobegc_j12180', 'size': 827, 'mtime': 1580147035.305319}
{'name': 'adobegc_j82640', 'size': 827, 'mtime': 1588620768.686572}
{'name': 'adobegc_j87796', 'size': 827, 'mtime': 1588620476.2220924}
{'name': 'adobegc_j94428', 'size': 827, 'mtime': 1588625305.749532}
{'name': 'adobegc_k00736', 'size': 827, 'mtime': 1588706597.5977101}
{'name': 'adobegc_k03984', 'size': 827, 'mtime': 1588708585.727807}
{'name': 'adobegc_k04400', 'size': 827, 'mtime': 1588699002.9317427}
{'name': 'adobegc_k12180', 'size': 827, 'mtime': 1580147056.48849}
{'name': 'adobegc_k94428', 'size': 827, 'mtime': 1588625326.7249243}
{'name': 'adobegc_l00736', 'size': 827, 'mtime': 1588706650.0458724}
{'name': 'adobegc_l04400', 'size': 827, 'mtime': 1588699173.7167861}
{'name': 'adobegc_l12180', 'size': 827, 'mtime': 1580147075.7756407}
{'name': 'adobegc_m00736', 'size': 827, 'mtime': 1588706696.6210747}
{'name': 'adobegc_m04400', 'size': 827, 'mtime': 1588699299.9061432}
{'name': 'adobegc_n00736', 'size': 827, 'mtime': 1588706702.6324935}
{'name': 'adobegc_n04400', 'size': 827, 'mtime': 1588699322.7834435}
{'name': 'adobegc_o04400', 'size': 827, 'mtime': 1588699343.7964466}
{'name': 'adobegc_p04400', 'size': 827, 'mtime': 1588699361.8530748}
{'name': 'adobegc_q04400', 'size': 827, 'mtime': 1588699435.7401783}
{'name': 'adobegc_r04400', 'size': 827, 'mtime': 1588699497.8403273}
{'name': 'adobegc_s04400', 'size': 827, 'mtime': 1588699564.148772}
{'name': 'adobegc_t04400', 'size': 827, 'mtime': 1588699581.2896767}
{'name': 'adobegc_u04400', 'size': 827, 'mtime': 1588699598.6942072}
{'name': 'adobegc_v04400', 'size': 827, 'mtime': 1588699628.5083873}
{'name': 'adobegc_w04400', 'size': 827, 'mtime': 1588699651.7972827}
{'name': 'AdobeIPCBrokerCustomHook.log', 'size': 110, 'mtime': 1594148255.931315}
{'name': 'ArmUI.ini', 'size': 257928, 'mtime': 1594655604.2703094}
{'name': 'bep_ie_tmp.log', 'size': 5750, 'mtime': 1594630046.8321078}
{'name': 'BROMJ6945DW.INI', 'size': 164, 'mtime': 1594932054.8597217}
{'name': 'CCSF_DebugLog.log', 'size': 22720, 'mtime': 1594619167.7750485}
{'name': 'chrome_installer.log', 'size': 215231, 'mtime': 1593199121.0920432}
{'name': 'dd_vcredist_amd64_20200710192056.log', 'size': 9218, 'mtime': 1594434073.4356828}
{'name': 'dd_vcredist_amd64_20200710192056_000_vcRuntimeMinimum_x64.log', 'size': 340038, 'mtime': 1594434071.8020437}
{'name': 'dd_vcredist_amd64_20200710192056_001_vcRuntimeAdditional_x64.log', 'size': 195928, 'mtime': 1594434073.3878088}
{'name': 'FXSAPIDebugLogFile.txt', 'size': 0, 'mtime': 1580005774.2871478}
{'name': 'FXSTIFFDebugLogFile.txt', 'size': 0, 'mtime': 1580005774.2402809}
{'name': 'install.ps1', 'size': 22662, 'mtime': 1594434168.2012112}
{'name': 'logserver.exe', 'size': 360392, 'mtime': 1591966026.0}
{'name': 'MpCmdRun.log', 'size': 414950, 'mtime': 1595033174.3764453}
{'name': 'Ofcdebug.ini', 'size': 2208, 'mtime': 1594619167.7125623}
{'name': 'ofcpipc.dll', 'size': 439232, 'mtime': 1591380338.0}
{'name': 'PDApp.log', 'size': 450550, 'mtime': 1594148263.081737}
{'name': 'show_temp_dir.py', 'size': 505, 'mtime': 1595040826.2968051}
{'name': 'tem33F0.tmp', 'size': 68, 'mtime': 1580005493.3622465}
{'name': 'temE0A2.tmp', 'size': 206, 'mtime': 1580005825.1382103}
{'name': 'tmdbg20.dll', 'size': 264648, 'mtime': 1591966082.0}
{'name': 'tm_icrcL_A606D985_38CA_41ab_BCD9_60F771CF800D', 'size': 0, 'mtime': 1594629977.2000608}
{'name': 'TS_3AD6.tmp', 'size': 262144, 'mtime': 1594629969.3296628}
{'name': 'TS_A4CE.tmp', 'size': 327680, 'mtime': 1594629996.4481225}
{'name': 'winagent-v0.9.4.exe', 'size': 13265088, 'mtime': 1594615216.1575873}
{'name': 'wuredist.cab', 'size': 6295, 'mtime': 1594458610.4993813}
"""
