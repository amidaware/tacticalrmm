#!/usr/bin/env bash

# Tactical RMM install troubleshooting script
# Contributed by https://github.com/dinger1986
# v1.1  1/21/2022  update to include all services
# v1.2  6/24/2023  changed to add date, easier readability and ipv4 addresses only for checks
# v1.3  6/24/2024  Adding resolvconf helper
# v1.4  3/12/2025 Removed Mongo Check and added OS Check and Warning for Ubuntu 20.04
# v1.5  3/12/2025 Switching to auto-detect Tactical RMM domains from config files
# v1.6 thru v1.9  7/18/2025 Added dynamic logging and fixed regex warnings. Cleaning header and sudo check.

# This script is designed to help troubleshoot Tactical RMM installations.

# --- Require sudo/root -------------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo -e "\e[31mERROR: This script must be run as root (use sudo)\e[0m" >&2
  exit 1
fi

# ——— Color setup (only if running on a TTY) ——————————————————————————————
if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; NC=''
fi

# ——— Dynamic log file setup ——————————————————————————————————————————————
LOGFILE="troubleshootinglog_$(date '+%Y-%m-%d-%H-%M-%S').log"
# console gets the raw (colored) output; logfile gets ANSI codes stripped
exec > >(tee >(sed -r 's/\x1B\[[0-9;]*[mK]//g' >>"$LOGFILE")) 2>&1

# ——— Timestamp header ——————————————————————————————————————————————
now=$(date)
echo -e "-------------- $now --------------"

# pure-ERE IPv4 matcher (for all subsequent greps)
IPV4='([0-9]{1,3}\.){3}[0-9]{1,3}'

# ——— Minimum RAM check ——————————————————————————————————————————————
memTotal=$(grep -i MemTotal /proc/meminfo | awk '{print $2}')
if [[ $memTotal -lt 3627528 ]]; then
  echo -e "${RED}ERROR: A minimum of 4GB of RAM is required.${NC}"
  exit 1
fi

# ——— OS support check ——————————————————————————————————————————————
osname=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
relno=$(lsb_release -sr | cut -d. -f1)
fullrelno=$(lsb_release -sr)

not_supported() {
  echo -e "${RED}ERROR: Only Debian 11, Debian 12 and Ubuntu 22.04 are supported.${NC}"
  exit 1
}
needs_updated() {
  echo -e "${YELLOW}WARNING: Ubuntu 20.04 is outdated. Please migrate to Ubuntu 22.04 or Debian 12.${NC}"
}
pass_message() {
  echo -e "${GREEN}You are running $osname $fullrelno, which is supported.${NC}"
}

if [[ "$osname" == "debian" ]]; then
  [[ "$relno" -ne 11 && "$relno" -ne 12 ]] && not_supported || pass_message
elif [[ "$osname" == "ubuntu" ]]; then
  [[ "$fullrelno" == "20.04" ]] && needs_updated
  [[ "$fullrelno" == "22.04" ]] && pass_message || not_supported
else
  not_supported
fi

# ——— Unsupported environments —————————————————————————————————————————
if dpkg -l | grep -qi turnkey; then
  echo -e "${RED}Turnkey Linux is not supported. Use official Debian/Ubuntu ISO.${NC}"
  exit 1
fi
if pgrep -f webmin >/dev/null; then
  echo -e "${RED}Webmin detected. Please use a clean Debian/Ubuntu install.${NC}"
  exit 1
fi

# ——— resolvconf helper check —————————————————————————————————————————————
command -v resolvconf >/dev/null || {
  echo -e "${RED}Error: resolvconf not found.${NC}"
  echo -e "${YELLOW}Install with: sudo apt install resolvconf${NC}"
  exit 1
}

# ——— Local DNS resolver detection —————————————————————————————————————
resolvestatus=$(systemctl is-active systemd-resolved.service)
if [[ "$osname" == "debian" && "$relno" == 12 ]]; then
  locdns=$(resolvconf -l | grep -m1 -Eo "$IPV4")
elif [[ "$resolvestatus" == "active" ]]; then
  locdns=$(resolvectl | grep -m1 -Eo "$IPV4")
else
  until systemctl is-active --quiet systemd-resolved.service; do
    echo "Waiting for systemd-resolved..."
    systemctl start systemd-resolved.service
    sleep 3
  done
  locdns=$(resolvectl | grep -m1 -Eo "$IPV4")
  systemctl stop systemd-resolved.service
fi

# ——— Auto-detect Tactical RMM domains ————————————————————————————————————
echo -e ""
echo -e "${YELLOW}---------- Detecting Tactical RMM domains from installed config... ----------${NC}"

SETTINGS_FILE="/rmm/api/tacticalrmm/tacticalrmm/local_settings.py"
MESH_CONFIG="/meshcentral/meshcentral-data/config.json"

# RMM Backend (api.example.com)
rmmdomain=$(
  grep -E "^ALLOWED_HOSTS\s*=" "$SETTINGS_FILE" 2>/dev/null \
  | grep -Eo "'[^']+'" \
  | tr -d "'" \
  | head -1
)

# Frontend (rmm.example.com)
frontenddomain=$(
  grep -A 3 "CORS_ORIGIN_WHITELIST" "$SETTINGS_FILE" 2>/dev/null \
  | grep -Eo 'https://[^"]+' \
  | cut -d/ -f3 \
  | head -1
)

# MeshCentral (mesh.example.com)
meshdomain=$(
  grep -E '"Cert"\s*:\s*"' "$MESH_CONFIG" 2>/dev/null \
  | head -1 \
  | cut -d'"' -f4
)

# Base domain (example.com)
domain=""
if [[ -n "$rmmdomain" ]]; then
  domain=$(echo "$rmmdomain" | cut -d. -f2-)
fi

echo -e "
${GREEN}Detected Values:${NC}
  RMM Backend (API)   : ${rmmdomain:-${RED}Not Found${NC}}
  Frontend (Web GUI)  : ${frontenddomain:-${RED}Not Found${NC}}
  MeshCentral         : ${meshdomain:-${RED}Not Found${NC}}
  Base Domain         : ${domain:-${RED}Not Found${NC}}
"

if [[ -z "$rmmdomain" || -z "$frontenddomain" || -z "$meshdomain" || -z "$domain" ]]; then
  echo -e "${RED}ERROR: Could not auto-detect all required domains. Please verify your config files.${NC}"
  exit 1
fi

# ——— Connectivity & DNS resolution checks —————————————————————————————————
echo -e ""
echo -e "${YELLOW}---------- Checking IPs and reachability... ----------${NC}"
for svc in "api:$rmmdomain" "frontend:$frontenddomain" "mesh:$meshdomain"; do
  IFS=: read -r name host <<< "$svc"

  locip=$(dig @"$locdns" +short "$host" | grep -m1 -Eo "$IPV4")
  remip=$(dig @8.8.8.8 +short "$host" | grep -m1 -Eo "$IPV4")

  if [[ -z "$locip" || -z "$remip" ]]; then
    echo -e "${RED}ERROR: DNS lookup failed for $host (Local='$locip', Remote='$remip')${NC}"
  elif [[ "$locip" == "$remip" ]]; then
    echo -e "${GREEN}Success [$name] $host ? Local: $locip, Remote: $remip${NC}"
  else
    echo -e "${RED}Mismatch [$name] $host ? Local: $locip, Remote: $remip${NC}"
    echo -e "${RED}Agents may require non-public DNS to reach $host${NC}"
  fi
  echo
done

# ——— Service status checks —————————————————————————————————————————————
echo -e ""
echo -e "${YELLOW}---------- Checking system services... ----------${NC}"
services=(rmm daphne celery celerybeat nginx nats nats-api meshcentral postgresql redis-server)
for s in "${services[@]}"; do
  if systemctl is-active --quiet "$s"; then
    echo -e "${GREEN}Service $s is running${NC}"
  else
    echo -e "${RED}Service $s is NOT running${NC}"
  fi
  echo
done

# ——— WAN IP & port check —————————————————————————————————————————————
wanip=$(dig @resolver4.opendns.com myip.opendns.com +short)
echo -e "${GREEN}Detected WAN IP: $wanip${NC}"

if ! command -v nc &>/dev/null; then
  echo "Installing netcat..."
  apt-get update && apt-get install -y netcat
fi

if nc -zv "$wanip" 443 &>/dev/null; then
  echo -e "${GREEN}Port 443 is open${NC}"
else
  echo -e "${RED}Port 443 is closed (check firewall/NAT)${NC}"
fi

# ——— Proxy detection ————————————————————————————————————————————————
echo -e ""
echo -e "${YELLOW}---------- Checking for proxy via certificate... ----------${NC}"
proxyext=$(openssl s_client -showcerts -servername "$rmmdomain" -connect "$rmmdomain":443 </dev/null 2>/dev/null \
           | openssl x509 -noout -text)
proxyint=$(openssl s_client -showcerts -connect 127.0.0.1:443 </dev/null 2>/dev/null \
           | openssl x509 -noout -text)

if [[ "$proxyext" == "$proxyint" ]]; then
  echo -e "${GREEN}No proxy detected (certificate match)${NC}"
else
  echo -e "${RED}Proxy detected (certificate mismatch)${NC}"
fi

if [[ "$wanip" == "$remip" ]]; then
  echo -e "${GREEN}No proxy detected (WAN IP match)${NC}"
else
  echo -e "${RED}Proxy detected (WAN IP mismatch)${NC}"
fi

# ——— SSL certificate check —————————————————————————————————————————————
echo -e ""
echo -e "${YELLOW}---------- Checking SSL certificate for $domain... ----------${NC}"
cert=$(certbot certificates 2>/dev/null)
if [[ "$cert" != *"INVALID"* ]]; then
  echo -e "${GREEN}SSL certificate for $domain is valid${NC}"
else
  echo -e "${RED}SSL certificate for $domain is INVALID or missing${NC}"
fi

certbot certificates

# ——— Tail recent logs ————————————————————————————————————————————————
echo -e ""
echo -e "${YELLOW}---------- Showing recent Django logs... ----------${NC}"
tail -n 60 /rmm/api/tacticalrmm/tacticalrmm/private/log/django_debug.log
echo
echo -e ""
echo -e "${YELLOW}---------- Showing recent error logs... ----------${NC}"
tail -n 60 /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log
echo

# ——— Final message ————————————————————————————————————————————————
echo -e "${YELLOW}Log saved to ${LOGFILE}${NC}"
