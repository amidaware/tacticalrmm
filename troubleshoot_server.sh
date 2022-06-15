#!/usr/bin/env bash

# Tactical RMM install troubleshooting script
# Contributed by https://github.com/dinger1986
# v1.1 1/21/2022 update to include all services

# This script asks for the 3 subdomains, checks they exist, checks they resolve locally and remotely (using google dns for remote), 
# checks services are running, checks ports are opened. The only part that will make the script stop is if the sub domains dont exist, theres literally no point in going further if thats the case

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Resolve Locally used DNS server
locdns=$(resolvectl | grep 'Current DNS Server:' | cut -d: -f2 | awk '{ print $1}')

while [[ $rmmdomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain for the backend (e.g. api.example.com)${NC}: "
read rmmdomain
done

if ping -c 1 $rmmdomain &> /dev/null
then
    echo -ne ${GREEN} Verified $rmmdomain | tee -a checklog.log
	printf >&2 "\n\n"
else
  echo -ne ${RED} $rmmdomain doesnt exist please create it or check for a typo | tee -a checklog.log
  printf >&2 "\n\n"
  printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
  printf >&2 "\n\n"
  exit
fi

while [[ $frontenddomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain for the frontend (e.g. rmm.example.com)${NC}: "
read frontenddomain
done

if ping -c 1 $frontenddomain &> /dev/null
then
    echo -ne ${GREEN} Verified $frontenddomain | tee -a checklog.log
	printf >&2 "\n\n"
else
  echo -ne ${RED} $frontenddomain doesnt exist please create it or check for a typo | tee -a checklog.log
  printf >&2 "\n\n"
  printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
  printf >&2 "\n\n"
  exit
fi

while [[ $meshdomain != *[.]*[.]* ]]
do
echo -ne "${YELLOW}Enter the subdomain for meshcentral (e.g. mesh.example.com)${NC}: "
read meshdomain
done

if ping -c 1 $meshdomain &> /dev/null
then
    echo -ne ${GREEN} Verified $meshdomain | tee -a checklog.log
	printf >&2 "\n\n"
else
  echo -ne ${RED} $meshdomain doesnt exist please create it or check for a typo | tee -a checklog.log
  printf >&2 "\n\n" | tee -a checklog.log
  printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
  printf >&2 "\n\n"
  exit
fi

while [[ $domain != *[.]* ]]
do
echo -ne "${YELLOW}Enter yourdomain used for letsencrypt (e.g. example.com)${NC}: "
read domain
done

	echo -ne ${YELLOW} Checking IPs | tee -a checklog.log 
	printf >&2 "\n\n"

# Check rmmdomain IPs
locapiip=`dig @"$locdns" +short $rmmdomain`
remapiip=`dig @8.8.8.8 +short $rmmdomain`

if [ "$locapiip" = "$remapiip" ]; then
    echo -ne ${GREEN} Success $rmmdomain is Locally Resolved: "$locapiip"  Remotely Resolved: "$remapiip" | tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -ne ${RED} Locally Resolved: "$locapiip"  Remotely Resolved: "$remapiip" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED} Your Local and Remote IP for $rmmdomain all agents will require non-public DNS to find TRMM server | tee -a checklog.log
	printf >&2 "\n\n"

fi


# Check Frontenddomain IPs
locrmmip=`dig @"$locdns" +short $frontenddomain`
remrmmip=`dig @8.8.8.8 +short $frontenddomain`

if [ "$locrmmip" = "$remrmmip" ]; then
    echo -ne ${GREEN} Success $frontenddomain is Locally Resolved: "$locrmmip"  Remotely Resolved: "$remrmmip"| tee -a checklog.log
	printf >&2 "\n\n"
else
	echo -ne ${RED}  Locally Resolved: "$locrmmip"  Remotely Resolved: "$remrmmip" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED} echo Your Local and Remote IP for $frontenddomain all agents will require non-public DNS to find TRMM server | tee -a checklog.log
	printf >&2 "\n\n"

fi

# Check meshdomain IPs
locmeship=`dig @"$locdns" +short $meshdomain`
remmeship=`dig @8.8.8.8 +short $meshdomain`

if [ "$locmeship" = "$remmeship" ]; then
    echo -ne ${GREEN} Success $meshdomain is Locally Resolved: "$locmeship"  Remotely Resolved: "$remmeship" | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log
else
	echo -ne ${RED} Locally Resolved: "$locmeship"  Remotely Resolved: "$remmeship" | tee -a checklog.log
    printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED} Your Local and Remote IP for $meshdomain all agents will require non-public DNS to find TRMM server | tee -a checklog.log
	printf >&2 "\n\n" | tee -a checklog.log

fi

	echo -ne ${YELLOW} Checking Services | tee -a checklog.log 
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
    echo -ne ${GREEN} Success RMM Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'RMM Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# daphne Service
if [ $daphnestatus = active ]; then
    echo -ne ${GREEN} Success daphne Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'daphne Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# celery Service
if [ $celerystatus = active ]; then
    echo -ne ${GREEN} Success celery Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'celery Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# celerybeat Service
if [ $celerybeatstatus = active ]; then
    echo -ne ${GREEN} Success celerybeat Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'celerybeat Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# nginx Service
if [ $nginxstatus = active ]; then
    echo -ne ${GREEN} Success nginx Service is Running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'nginx Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# nats Service
if [ $natsstatus = active ]; then
    echo -ne ${GREEN} Success nats Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'nats Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# nats-api Service
if [ $natsapistatus = active ]; then
    echo -ne ${GREEN} Success nats-api Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'nats-api Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# meshcentral Service
if [ $meshcentralstatus = active ]; then
    echo -ne ${GREEN} Success meshcentral Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'meshcentral Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# mongod Service
if [ $mongodstatus = active ]; then
    echo -ne ${GREEN} Success mongod Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'mongod Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# postgresql Service
if [ $postgresqlstatus = active ]; then
    echo -ne ${GREEN} Success postgresql Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'postgresql Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

# redis-server Service
if [ $redisserverstatus = active ]; then
    echo -ne ${GREEN} Success redis-server Service is running | tee -a checklog.log
	printf >&2 "\n\n"
else
	printf >&2 "\n\n" | tee -a checklog.log
    echo -ne ${RED}  'redis-server Service isnt running (Tactical wont work without this)' | tee -a checklog.log
	printf >&2 "\n\n"

fi

	echo -ne ${YELLOW} Checking Open Ports | tee -a checklog.log 
	printf >&2 "\n\n"

#Get WAN IP
wanip=$(dig @resolver4.opendns.com myip.opendns.com +short)

echo -ne ${GREEN} WAN IP is $wanip | tee -a checklog.log
printf >&2 "\n\n"

#Check if NATs Port is open
if ( nc -zv $wanip 4222 2>&1 >/dev/null ); then
    echo -ne ${GREEN} 'NATs Port is open' | tee -a checklog.log
	printf >&2 "\n\n"
else
    echo -ne ${RED} 'NATs port is closed (you may want this if running locally only)' | tee -a checklog.log
	printf >&2 "\n\n"
fi

#Check if HTTPs Port is open
if ( nc -zv $wanip 443 2>&1 >/dev/null ); then
    echo -ne ${GREEN} 'HTTPs Port is open' | tee -a checklog.log
	printf >&2 "\n\n"
else
    echo -ne ${RED} 'HTTPs port is closed (you may want this if running locally only)' | tee -a checklog.log
	printf >&2 "\n\n"
fi

	echo -ne ${YELLOW} Checking For Proxy | tee -a checklog.log 
	printf >&2 "\n\n"
	echo -ne ${YELLOW} ......this might take a while!!
	printf >&2 "\n\n"

# Detect Proxy via cert
proxyext=$(openssl s_client -showcerts -servername $remapiip -connect $remapiip:443 2>/dev/null | openssl x509 -inform pem -noout -text)
proxyint=$(openssl s_client -showcerts -servername 127.0.0.1 -connect 127.0.0.1:443 2>/dev/null | openssl x509 -inform pem -noout -text)

if [[ $proxyext == $proxyint ]]; then
    echo -ne ${GREEN} No Proxy detected using Certificate | tee -a checklog.log
	printf >&2 "\n\n"
else
    echo -ne ${RED} Proxy detected using Certificate | tee -a checklog.log
	printf >&2 "\n\n"
fi

# Detect Proxy via IP
if [ $wanip != $remrmmip ]; then
    echo -ne ${RED} Proxy detected using IP | tee -a checklog.log
	printf >&2 "\n\n"
else
    echo -ne ${GREEN} No Proxy detected using IP | tee -a checklog.log
	printf >&2 "\n\n"
fi

	echo -ne ${YELLOW} Checking SSL Certificate is up to date | tee -a checklog.log 
	printf >&2 "\n\n"

#SSL Certificate check
cert=$(openssl verify -CAfile /etc/letsencrypt/live/$domain/chain.pem /etc/letsencrypt/live/$domain/cert.pem)

if [[ "$cert" == *"OK"* ]]; then
    echo -ne ${GREEN} SSL Certificate for $domain is fine  | tee -a checklog.log
	printf >&2 "\n\n"

else
    echo -ne ${RED} SSL Certificate has expired or doesnt exist for $domain  | tee -a checklog.log
	printf >&2 "\n\n"
fi
	echo -ne ${YELLOW} Getting summary output of logs | tee -a checklog.log  

tail /rmm/api/tacticalrmm/tacticalrmm/private/log/django_debug.log  | tee -a checklog.log
	printf >&2 "\n\n"
tail /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log  | tee -a checklog.log
	printf >&2 "\n\n"

printf >&2 "\n\n"
echo -ne ${YELLOW} 
printf >&2 "You will have a log file called checklog.log in the directory you ran this script from\n\n"
echo -ne ${NC}
