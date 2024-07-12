#!/usr/bin/env bash

# Tactical RMM install troubleshooting script
# Contributed by https://github.com/dinger1986
# v1.1 1/21/2022 update to include all services
# v 1.2 6/24/2023 changed to add date, easier readability and ipv4 addresses only for checks
# v 1.3 6/24/2024 Adding resolvconf helper

# This script asks for the 3 subdomains, checks they exist, checks they resolve locally and remotely (using google dns for remote),
# checks services are running, checks ports are opened. The only part that will make the script stop is if the sub domains dont exist, theres literally no point in going further if thats the case

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to check if a resolvconf is installed
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if resolvconf command is available
if ! command_exists resolvconf; then
    echo -e "${RED}Error: resolvconf command not found.${NC}"
    echo -e "${YELLOW}Please install it using: ${NC}sudo apt install resolvconf"
    exit 1
fi

# Set date at the top of the troubleshooting script
now=$(date)
echo -e -------------- $now -------------- | tee -a checklog.log

osname=$(lsb_release -si)
osname=${osname^}
osname=$(echo "$osname" | tr '[A-Z]' '[a-z]')
relno=$(lsb_release -sr | cut -d. -f1)

# Resolve Locally used DNS server
resolvestatus=$(systemctl is-active systemd-resolved.service)
if [[ "$osname" == "debian" && "$relno" == 12 ]]; then
	locdns=$(resolvconf -l | tail -n +1 | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

elif [ $resolvestatus = active ]; then
	locdns=$(resolvectl | tail -n +1 | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
else
	while ! [[ $resolveconf ]]; do
		resolveconf=$(sudo systemctl status systemd-resolved.service | grep "Active: active (running)")
		sudo systemctl start systemd-resolved.service
		echo -ne "DNS Resolver not ready yet...${NC}\n"
		sleep 3
	done
	locdns=$(resolvectl | tail -n +1 | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
	sudo systemctl stop systemd-resolved.service
fi

while [[ $rmmdomain != *[.]*[.]* ]]; do
	echo -e "${YELLOW}Enter the subdomain for the backend (e.g. api.example.com)${NC}: "
	read rmmdomain
done

if ping -c 1 $rmmdomain &>/dev/null; then
	echo -e ${GREEN} Verified $rmmdomain | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} $rmmdomain doesnt exist please create it or check for a typo | tee -a checklog.log
	printf >&2 "\n\n"
	printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
	printf >&2 "\n\n"
	exit
fi

while [[ $frontenddomain != *[.]*[.]* ]]; do
	echo -e "${YELLOW}Enter the subdomain for the frontend (e.g. rmm.example.com)${NC}: "
	read frontenddomain
done

if ping -c 1 $frontenddomain &>/dev/null; then
	echo -e ${GREEN} Verified $frontenddomain | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} $frontenddomain doesnt exist please create it or check for a typo | tee -a checklog.log
	printf >&2 "\n\n"
	printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
	printf >&2 "\n\n"
	exit
fi

while [[ $meshdomain != *[.]*[.]* ]]; do
	echo -e "${YELLOW}Enter the subdomain for meshcentral (e.g. mesh.example.com)${NC}: "
	read meshdomain
done

if ping -c 1 $meshdomain &>/dev/null; then
	echo -e ${GREEN} Verified $meshdomain | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} $meshdomain doesnt exist please create it or check for a typo | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
	printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
	printf >&2 "\n\n"
	exit
fi

while [[ $domain != *[.]* ]]; do
	echo -e "${YELLOW}Enter yourdomain used for letsencrypt (e.g. example.com)${NC}: "
	read domain
done

echo -e ${YELLOW} Checking IPs | tee -a checklog.log
printf >&2 "\n\n"

# Check rmmdomain IPs
locapiip=$(dig @"$locdns" +short $rmmdomain | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
remapiip=$(dig @8.8.8.8 +short $rmmdomain | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

if [ "$locapiip" = "$remapiip" ]; then
	echo -e ${GREEN} Success $rmmdomain is Locally Resolved: "$locapiip" Remotely Resolved: "$remapiip" | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} Locally Resolved: "$locapiip" Remotely Resolved: "$remapiip" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} Your Local and Remote IP for $rmmdomain all agents will require non-public DNS to find TRMM server | tee -a checklog.log
	printf >&2 "\n\n"

fi

# Check Frontenddomain IPs
locrmmip=$(dig @"$locdns" +short $frontenddomain | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
remrmmip=$(dig @8.8.8.8 +short $frontenddomain | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

if [ "$locrmmip" = "$remrmmip" ]; then
	echo -e ${GREEN} Success $frontenddomain is Locally Resolved: "$locrmmip" Remotely Resolved: "$remrmmip" | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} Locally Resolved: "$locrmmip" Remotely Resolved: "$remrmmip" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} echo Your Local and Remote IP for $frontenddomain all agents will require non-public DNS to find TRMM server | tee -a checklog.log
	printf >&2 "\n\n"

fi

# Check meshdomain IPs
locmeship=$(dig @"$locdns" +short $meshdomain | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
remmeship=$(dig @8.8.8.8 +short $meshdomain | grep -m 1 -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

if [ "$locmeship" = "$remmeship" ]; then
	echo -e ${GREEN} Success $meshdomain is Locally Resolved: "$locmeship" Remotely Resolved: "$remmeship" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
else
	echo -e ${RED} Locally Resolved: "$locmeship" Remotely Resolved: "$remmeship" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} Your Local and Remote IP for $meshdomain all agents will require non-public DNS to find TRMM server | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log

fi

echo -e ${YELLOW} Checking Services | tee -a checklog.log
printf >&2 "\n\n"

# Check if services are running
rmmstatus=$(systemctl is-active rmm)
daphnestatus=$(systemctl is-active daphne)
celerystatus=$(systemctl is-active celery)
celerybeatstatus=$(systemctl is-active celerybeat)
nginxstatus=$(systemctl is-active nginx)
natsstatus=$(systemctl is-active nats)
natsapistatus=$(systemctl is-active nats-api)
meshcentralstatus=$(systemctl is-active meshcentral)
mongodstatus=$(systemctl is-active mongod)
postgresqlstatus=$(systemctl is-active postgresql)
redisserverstatus=$(systemctl is-active redis-server)

# RMM Service
if [ $rmmstatus = active ]; then
	echo -e ${GREEN} Success RMM Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'RMM Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# daphne Service
if [ $daphnestatus = active ]; then
	echo -e ${GREEN} Success daphne Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'daphne Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# celery Service
if [ $celerystatus = active ]; then
	echo -e ${GREEN} Success celery Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'celery Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# celerybeat Service
if [ $celerybeatstatus = active ]; then
	echo -e ${GREEN} Success celerybeat Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'celerybeat Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# nginx Service
if [ $nginxstatus = active ]; then
	echo -e ${GREEN} Success nginx Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'nginx Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# nats Service
if [ $natsstatus = active ]; then
	echo -e ${GREEN} Success nats Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'nats Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# nats-api Service
if [ $natsapistatus = active ]; then
	echo -e ${GREEN} Success nats-api Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'nats-api Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# meshcentral Service
if [ $meshcentralstatus = active ]; then
	echo -e ${GREEN} Success meshcentral Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'meshcentral Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# mongod Service
if grep -q mongo "/meshcentral/meshcentral-data/config.json"; then
	if [ $mongodstatus = active ]; then
		echo -e ${GREEN} Success mongod Service is running | tee -a checklog.log
		printf >&2 "\n\n"
	else
		printf >&2 "\n\n" | tee -a checklog.log
		echo -e ${RED} 'mongod Service isnt running (Tactical wont work without this)' | tee -a checklog.log
		printf >&2 "\n\n"

	fi
fi
# postgresql Service
if [ $postgresqlstatus = active ]; then
	echo -e ${GREEN} Success postgresql Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'postgresql Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# redis-server Service
if [ $redisserverstatus = active ]; then
	echo -e ${GREEN} Success redis-server Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
	echo -e ${RED} 'redis-server Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

echo -e ${YELLOW} Checking Open Ports | tee -a checklog.log
printf >&2 "\n\n"

#Get WAN IP
wanip=$(dig @resolver4.opendns.com myip.opendns.com +short)

echo -e ${GREEN} WAN IP is $wanip | tee -a checklog.log
printf >&2 "\n\n"

if ! which nc >/dev/null; then
	echo "netcat is not installed, installing now"
	sudo apt-get install netcat -y
fi

#Check if HTTPs Port is open
if (nc -zv $wanip 443 2>&1 >/dev/null); then
	echo -e ${GREEN} 'HTTPs Port is open' | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} 'HTTPs port is closed (you may want this if running locally only)' | tee -a checklog.log
	printf >&2 "\n\n"
fi

echo -e ${YELLOW} Checking For Proxy | tee -a checklog.log
printf >&2 "\n\n"
echo -e ${YELLOW} ......this might take a while!!
printf >&2 "\n\n"

# Detect Proxy via cert
proxyext=$(openssl s_client -showcerts -servername $remapiip -connect $remapiip:443 2>/dev/null | openssl x509 -inform pem -noout -text)
proxyint=$(openssl s_client -showcerts -servername 127.0.0.1 -connect 127.0.0.1:443 2>/dev/null | openssl x509 -inform pem -noout -text)

if [[ $proxyext == $proxyint ]]; then
	echo -e ${GREEN} No Proxy detected using Certificate | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${RED} Proxy detected using Certificate | tee -a checklog.log
	printf >&2 "\n\n"
fi

# Detect Proxy via IP
if [ $wanip != $remrmmip ]; then
	echo -e ${RED} Proxy detected using IP | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -e ${GREEN} No Proxy detected using IP | tee -a checklog.log
	printf >&2 "\n\n"
fi

echo -e ${YELLOW} Checking SSL Certificate is up to date | tee -a checklog.log
printf >&2 "\n\n"

#SSL Certificate check
cert=$(sudo certbot certificates)

if [[ "$cert" != *"INVALID"* ]]; then
	echo -e ${GREEN} SSL Certificate for $domain is fine | tee -a checklog.log
	printf >&2 "\n\n"

else
	echo -e ${RED} SSL Certificate has expired or doesnt exist for $domain | tee -a checklog.log
	printf >&2 "\n\n"
fi

# Get List of Certbot Certificates
sudo certbot certificates | tee -a checklog.log

echo -e ${YELLOW} Getting summary output of logs | tee -a checklog.log

tail /rmm/api/tacticalrmm/tacticalrmm/private/log/django_debug.log | tee -a checklog.log
printf >&2 "\n\n"
tail /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log | tee -a checklog.log
printf >&2 "\n\n"

printf >&2 "\n\n"
echo -e ${YELLOW}
printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
echo -e ${NC}
