#!/bin/bash

### Menu option variables
INPUT=/tmp/menu.sh.$$
menuselection=""
declare -a menuoptions=('Dev Test Prereqs' 'Dev Test Install' 'Standard Install' 'Standard Update' 'Force Update' 'Backup' 'Restore' 'Renew Certs')
devurl=""
devbranch=""
installtype=""
updatetype=""
certrenew=""

### Script Info variables
SCRIPT_VERSION="63"
SCRIPT_URL='https://raw.githubusercontent.com/amidaware/tacticalrmm/master/install.sh'
THIS_SCRIPT=$(readlink -f "$0")

### Misc info variables
SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.10.4'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'

### Import functions
. $PWD/bashfunctions.cfg

### Set colors
setColors;

### Gather OS info
getOSInfo;

### Install script pre-reqs
installPreReqs;

### Check for new functions version, only include script name as variable
checkCfgVer "$THIS_SCRIPT";

### Check for new script version, pass script version, url, and script name variables in that order
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";

### Install additional prereqs
installAdditionalPreReqs;

### Fallback if lsb_release -si returns anything else than Ubuntu, Debian or Raspbian
wutOSThis;

### Verify compatible OS and version
verifySupportedOS;

### Check if root
checkRoot;

### Check language/locale
checkLocale;

### Prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

#########################
#  Main Menu Functions  #
#########################

mainInstall()
{
  ### Repo info for Postegres and Mongo
  setInstallRepos;

  ### Create usernames and passwords
  generateUsersAndPass;

  ### This does... something
  cls;

  ### Get host/domain info
  getHostAndDomainInfo;

  ### Configure hosts file
  print_green 'Configuring Hosts file'
  configHosts;

  ### Certificate generation
  print_green 'Installing Certbot'
  installCertbot;

  ### Install Nginx
  print_green 'Installing Nginx'
  installNginx;

  ### Install NodeJS
  print_green 'Installing NodeJS'
  installNodeJS;

  ### Install and enable MongoDB
  print_green 'Installing MongoDB'
  installMongo;

  ### Install Python
  print_green "Installing Python ${PYTHON_VER}"
  installPython;

  ### Installing Redis
  print_green 'Installing redis'
  installRedis;

  ### Install and enable Postgresql
  print_green 'Installing postgresql'
  installPostgresql;

  ### Postgres DB creation
  print_green 'Creating database for the rmm'
  createPGDB;

  ### Clone main repo
  print_green 'Cloning primary repo'
  clonePrimaryRepo
  
  ### Clone scripts repo
  cloneScriptsRepo;

  ### Installing NATS
  print_green 'Installing NATS'
  installNats "install";

  ### Install MeshCentral
  print_green 'Installing MeshCentral'
  installMeshCentral;
  
  ### Create MeshCentral config
  print_green 'Generating MeshCentral Config'
  createMeshConfig;

  ### Create local settings file
  print_green 'Generating Local Settings'
  createLocalSettings;

  ### Install NATS-API and correct permissions
  print_green 'Installing NATS API'
  installNatsApi;

  ### Install backend, configure primary admin user, setup admin 2fa
  print_green 'Installing the backend'
  configureBackend;
    
  ### Determine Proc setting for UWSGI
  print_green 'Optimizing UWSGI for number of processors'
  setUwsgiProcs;

  ### Create UWSGI config
  print_green 'Creating UWSGI configuration'
  createUwsgiConf;

  ### Create RMM UWSGI systemd service
  print_green 'Creating UWSGI service'
  createUwsgiService;

  ### Create Daphne systemd service
  print_green 'Creating Daphne service'
  createDaphneService;

  ### Create NATS systemd service
  print_green 'Creating NATS service'
  createNatsService;

  ### Create NATS-api systemd service
  print_green 'Creating NATS-API service'
  createNatsApiService;

  ### Create Backend Nginx site config
  print_green 'Creating Backend Nginx config'
  createBackendNginxConf;

  ### Create MeshCentral Nginx configuration
  print_green 'Creating MeshCentral Nginx config'
  createMeshNginxConf;

  ### Enable Mesh and RMM sites
  sudo ln -s /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf
  sudo ln -s /etc/nginx/sites-available/meshcentral.conf /etc/nginx/sites-enabled/meshcentral.conf

  ### Create conf directory
  sudo mkdir /etc/conf.d

  ### Create Celery systemd service
  print_green 'Creating Celery service'
  createCeleryService;

  ### Configure Celery service
  print_green 'Creating Celery config'
  createCeleryConf;

  ### Create CeleryBeat systemd service
  print_green 'Creating CeleryBeat service'
  createCeleryBeatService;

  ### Correct conf dir ownership
  sudo chown ${USER}:${USER} -R /etc/conf.d/

  ### Create MeshCentral systemd service
  print_green 'Creating MeshCentral service'
  createMeshCentralService;

  ### Update services info
  sudo systemctl daemon-reload

  ### Verify and correct permissions
  if [ -d ~/.npm ]; then
    sudo chown -R $USER:$GROUP ~/.npm
  fi

  if [ -d ~/.config ]; then
    sudo chown -R $USER:$GROUP ~/.config
  fi

  ### Install frontend
  print_green 'Installing the frontend'
  installFrontEnd;

  ### Set front end Nginx config and enable
  print_green 'Creating Frontend Nginx config'
  createFrontendNginxConf;

  ### Enable Frontend site
  sudo ln -s /etc/nginx/sites-available/frontend.conf /etc/nginx/sites-enabled/frontend.conf

  ### Enable RMM, Daphne, Celery, and Nginx services
  print_green 'Enabling Services'

  for i in rmm.service daphne.service celery.service celerybeat.service nginx
  do
    sudo systemctl enable ${i}
    sudo systemctl stop ${i}
    sudo systemctl start ${i}
  done
  sleep 5

  ### Enable MeshCentral service
  sudo systemctl enable meshcentral

  print_green 'Starting meshcentral and waiting for it to install plugins'

  sudo systemctl restart meshcentral

  sleep 3

  # The first time we start meshcentral, it will need some time to generate certs and install plugins.
  # This will take anywhere from a few seconds to a few minutes depending on the server's hardware
  # We will know it's ready once the last line of the systemd service stdout is 'MeshCentral HTTP server running on port.....'
  while ! [[ $CHECK_MESH_READY ]]; do
    CHECK_MESH_READY=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
    echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
    sleep 3
  done

  ### Generating MeshCentral key
  print_green 'Generating meshcentral login token key'
  generateMeshToken;

  ### Configuring MeshCentral admin user and device group, restart service
  print_green 'Creating meshcentral account and group'
  configMeshUserGroup;

  ### Enable and configure NATS service
  print_green 'Starting NATS service'
  enableNatsService;

  ### Disable django admin
  sed -i 's/ADMIN_ENABLED = True/ADMIN_ENABLED = False/g' /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

  ### Restart core services
  print_green 'Restarting services'

  for i in rmm.service daphne.service celery.service celerybeat.service
  do
    sudo systemctl stop ${i}
    sudo systemctl start ${i}
  done

  printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
  printf >&2 "\n\n"
  printf >&2 "${YELLOW}Installation complete!${NC}\n\n"
  printf >&2 "${YELLOW}Access your rmm at: ${GREEN}https://${frontenddomain}${NC}\n\n"
  printf >&2 "${YELLOW}Django admin url (disabled by default): ${GREEN}https://${rmmdomain}/${ADMINURL}/${NC}\n\n"
  printf >&2 "${YELLOW}MeshCentral username: ${GREEN}${meshusername}${NC}\n"
  printf >&2 "${YELLOW}MeshCentral password: ${GREEN}${MESHPASSWD}${NC}\n\n"

  if [ "$BEHIND_NAT" = true ]; then
    echo -ne "${YELLOW}Read below if your router does NOT support Hairpin NAT${NC}\n\n"
    echo -ne "${GREEN}If you will be accessing the web interface of the RMM from the same LAN as this server,${NC}\n"
    echo -ne "${GREEN}you'll need to make sure your 3 subdomains resolve to ${IPV4}${NC}\n"
    echo -ne "${GREEN}This also applies to any agents that will be on the same local network as the rmm.${NC}\n"
    echo -ne "${GREEN}You'll also need to setup port forwarding in your router on ports 80, 443 and 4222 tcp.${NC}\n\n"
  fi

  printf >&2 "${YELLOW}Please refer to the github README for next steps${NC}\n\n"
  printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
  printf >&2 "\n"
}
