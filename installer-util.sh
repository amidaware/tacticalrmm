#!/usr/bin/env bash

# Fix for ncurses derpy lines in putty and similar apps
export NCURSES_NO_UTF8_ACS=1

# Menu option variables
INPUT=/tmp/menu.sh.$$
menuselection=""

# Arrays
declare -a mainmenuoptions=('Installation' 'Update' 'Utilities' 'Exit')
declare -a installmenuoptions=('Standard Install' 'Dev Test Prereqs' 'Dev Test Install' 'Return' 'Exit')
declare -a updatemenuoptions=('Standard Update' 'Backup and Update' 'Force Update' 'Return' 'Exit')
declare -a utilitymenuoptions=('Backup' 'Restore' 'Renew Certs' 'Import Certs' 'Add Fail2ban - Use at your own risk' 'Run Server Troubleshooter' 'Return' 'Exit')
declare -a cfgfiles=('InputAndError.cfg' 'MiscFunctions.cfg' 'SystemInfoFunctions.cfg' 'UserInput.cfg' 'NetworkFunctions.cfg' 'InstallFunctions.cfg' 'DatabaseFunctions.cfg' 'CertificateFunctions.cfg' 'ConfigAndServiceFunctions.cfg' 'UpdateRestoreFunctions.cfg' 'TroubleshootingFunctions.cfg' 'ParentFunctions.cfg')

# Log file variables
rundate="$(date '+%Y_%m_%d__%H_%M_%S')"
installlog="$PWD/trmm-install_$rundate.log"
restorelog="$PWD/trmm-restore_$rundate.log"
updatelog="$PWD/trmm-update_$rundate.log"
backuplog="$PWD/trmm-backup_$rundate.log"
checklog="$PWD/trmm-checklog_$rundate.log"
preinstalllog="$PWD/trmm-preinstall-log_$rundate.log"
currentlog="$preinstalllog"

# Script Info variables
REPO_OWNER="ninjamonkey198206"
BRANCH="develop-installer-update-ws"
SCRIPT_VERSION="69"
CFG_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}"
SCRIPT_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}/installer-util.sh"
REPO_URL="https://github.com/${REPO_OWNER}/tacticalrmm.git"
SCRIPTS_REPO_URL="https://github.com/amidaware/community-scripts.git"
THIS_SCRIPT=$(readlink -f "$0")

# Misc info variables
INSTALL_TYPE="install"
UPDATE_TYPE="standard"
SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.10.4'
NODE_MAJOR_VER='16'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'
LATEST_SETTINGS_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}/api/tacticalrmm/tacticalrmm/settings.py"

# Variables required for automated install
autoinstall=""
rmmhost=""
frontendhost=""
meshhost=""
letsemail=""
rootdomain=""
sslcacert=""
sslkey=""
sslcert=""
trmmuser=""
trmmpass=""
backupfile=""
troubleshoot=""
certtype=""
sudopass=""

# Remove script run command from history to prevent sudo password leak
#history -d $(($(history 1 | awk '{print $1}')-1))

# Check if directory exists, if not, create
if [ ! -d "$PWD"/script-cfg ]; then
	mkdir "$PWD"/script-cfg 2>&1 | tee -a "${currentlog}"
fi

# Get cfg files function
getCfgFiles()
{
	if [ ! -f "$PWD/script-cfg/$2" ]; then
		wget "$1/script-cfg/$2" -O "$PWD/script-cfg/$2" 2>&1 | tee -a "${currentlog}"
	fi
}

# Get cfg files
for i in "${cfgfiles[@]}"
do
	getCfgFiles "$CFG_URL" "$i";
done

# Import functions
. "$PWD"/script-cfg/InputAndError.cfg
. "$PWD"/script-cfg/MiscFunctions.cfg
. "$PWD"/script-cfg/SystemInfoFunctions.cfg
. "$PWD"/script-cfg/UserInput.cfg
. "$PWD"/script-cfg/NetworkFunctions.cfg
. "$PWD"/script-cfg/InstallFunctions.cfg
. "$PWD"/script-cfg/DatabaseFunctions.cfg
. "$PWD"/script-cfg/CertificateFunctions.cfg
. "$PWD"/script-cfg/ConfigAndServiceFunctions.cfg
. "$PWD"/script-cfg/UpdateRestoreFunctions.cfg
. "$PWD"/script-cfg/TroubleshootingFunctions.cfg
. "$PWD"/script-cfg/ParentFunctions.cfg

# Set colors
# MiscFunctions
setColors;

# Get commandline input
while getopts i:a:b:c:e:d:m:f:g:h:k:s:p:r:o:t:u:n:w: option
do
	case $option in
      	i) autoinstall="1"
			INSTALL_TYPE="$(translateToLowerCase ${OPTARG})";;
		a) rmmhost="$(translateToLowerCase ${OPTARG})";;
		b) BRANCH="$(translateToLowerCase ${OPTARG})";;
		c) sslcacert="${OPTARG}";;
		e) sslcert="${OPTARG}";;
		d) rootdomain="$(translateToLowerCase ${OPTARG})";;
		m) letsemail="$(translateToLowerCase ${OPTARG})";;
		f) backupfile="${OPTARG}";;
		g) sudopass="${OPTARG}";;
		h) helpText
			exit 1;;
		k) sslkey="${OPTARG}";;
		s) meshhost="$(translateToLowerCase ${OPTARG})";;
		p) trmmpass="${OPTARG}";;
		r) REPO_OWNER="$(translateToLowerCase ${OPTARG})";;
		o) frontendhost="$(translateToLowerCase ${OPTARG})";;
		t) troubleshoot="1";;
		u) UPDATE_TYPE="$(translateToLowerCase ${OPTARG})";;
		n) trmmuser="${OPTARG}";;
		w) certtype="$(translateToLowerCase ${OPTARG})";;
	    \?) echo -e "Error: Invalid option"
			helpText
			exit 1;;
	esac
done

if [ "$autoinstall" == "1" ]; then

	# Check that update type is valid
	if [ "$INSTALL_TYPE" == "update" ] && ([ "$UPDATE_TYPE" != "standard" ] && [ "$UPDATE_TYPE" != "forced" ]); then
		echo -e "${RED} Error: You've selected update, but not selected an appropriate type. ${NC}" | tee -a "${currentlog}"
		echo -e "${RED} Run $THIS_SCRIPT -h help for details on how to select them. ${NC}"
		exit 1
	fi

	# Check that backup file exists
	if [ "$INSTALL_TYPE" == "restore" ] && ([ -z "$backupfile" ] || [ ! -f "$backupfile" ]); then
		echo -e "${RED} Error: You've selected restore, but not provided a valid backup file. ${NC}" | tee -a "${currentlog}"
		echo -e "${RED} Run $THIS_SCRIPT -h help for details on how to enter this. ${NC}"
		exit 1
	fi

	# Check that install type is valid
	if [ "$INSTALL_TYPE" != "devprep" ] && [ "$INSTALL_TYPE" != "devinstall" ] && [ "$INSTALL_TYPE" != "install" ] && [ "$INSTALL_TYPE" != "update" ] && [ "$INSTALL_TYPE" != "restore" ] && [ "$INSTALL_TYPE" != "backup" ]; then
		echo -e "${RED} Error: You've selected an invalid function type. ${NC}" | tee -a "${currentlog}"
		echo -e "${RED} Run $THIS_SCRIPT -h help for details on the available options. ${NC}"
		exit 1
	fi

	# Check all required input is available for install
	if [ "$INSTALL_TYPE" == "devprep" ] || [ "$INSTALL_TYPE" == "devinstall" ] || [ "$INSTALL_TYPE" == "install" ]; then
		if [ -z "$rmmhost" ] || [ -z "$certtype" ] || [ -z "$rootdomain" ] || [ -z "$meshhost" ] || [ -z "$frontendhost" ] || [ -z "$trmmuser" ] || [ -z "$trmmpass" ] || [ -z "$letsemail" ]; then
			echo -e "${RED} Error: To perform an automated installation, you must provide all required information. ${NC}" | tee -a "${currentlog}"
			echo -e "${RED} install type, api host, mesh host, rmm host, root domain, email address, certificate install type, and T-RMM username and password are all required. ${NC}" | tee -a "${currentlog}"
			echo -e "${RED} Run $THIS_SCRIPT -h help for further details. ${NC}"
			exit 1
		fi

		# Check that certificate install type is valid
		if [ "$certtype" != "import" ] && [ "$certtype" != "webroot" ]; then
			echo -e "${RED} Error: You've selected an invalid certificate installation type. ${NC}" | tee -a "${currentlog}"
			echo -e "${RED} Run $THIS_SCRIPT -h help for details on the available options. ${NC}"
			exit 1
		fi

		# Check for required input if import certificate
		if [ "$certtype" == "import" ] && ([ -z "$sslcacert" ] || [ -z "$sslcert" ] || [ -z "$sslkey" ]); then
			echo -e "${RED} Error: To perform an automated installation using imported certificates, you must provide all required information. ${NC}" | tee -a "${currentlog}"
			echo -e "${RED} install type, api host, mesh host, rmm host, root domain, email address, certificate install type, CA cert path, Cert path, Private key path, and T-RMM username and password are all required. ${NC}" | tee -a "${currentlog}"
			echo -e "${RED} Run $THIS_SCRIPT -h help for further details. ${NC}"
			exit 1
		fi
	fi

	# Check that email address format is valid
	if [ "$INSTALL_TYPE" == "devprep" ] || [ "$INSTALL_TYPE" == "devinstall" ] || [ "$INSTALL_TYPE" == "install" ]; then
		if [[ $letsemail != *[@]*[.]* ]]; then
			echo -e "${RED} Error: You've entered an invalid email address. ${NC}" | tee -a "${currentlog}"
			echo -e "${RED} Run $THIS_SCRIPT -h help for details on the correct format. ${NC}"
			exit 1
		fi
	fi

	# Check that repo and branch match install type
	if ([ "$INSTALL_TYPE" == "devprep" ] || [ "$INSTALL_TYPE" == "devinstall" ]) && [ "$BRANCH" == "master" ]; then
		echo -e "${RED} Error: You've selected a developer installation type, but not changed the repo, branch, or both. ${NC}" | tee -a "${currentlog}"
		echo -e "${RED} Run $THIS_SCRIPT -h help for details on how to select them. ${NC}"
		exit 1
	fi

	if [ -n "$rmmhost" ] && [ -n "$meshhost" ] && [ -n "$frontendhost" ] && [ -n "$rootdomain" ]; then
		# Check subdomains are valid format
		# User Input
		subdomainFormatCheck "$rmmhost" "api";
		subdomainFormatCheck "$meshhost" "mesh";
		subdomainFormatCheck "$frontendhost" "rmm";
	
		# Check root domain format is valid
		# User Input
		rootDomainFormatCheck "$rootdomain";
	
		# Check that entries resolve via dns
		# User Input
		rmmdomain="$rmmhost.$rootdomain"
		frontenddomain="$frontendhost.$rootdomain"
		meshdomain="$meshhost.$rootdomain"
		checkDNSEntriesExist "$rmmdomain";
		checkDNSEntriesExist "$frontenddomain";
		checkDNSEntriesExist "$meshdomain";
	fi

	if [ -n "$sslcacert" ] && [ -n "$sslcert" ] && [ -n "$sslkey" ]; then
		# Check that cert file exists
		# User Input
		checkCertExists "$sslcacert" "CA Chain";
		checkCertExists "$sslcert" "Fullchain Cert";
		checkCertExists "$sslkey" "Private Key";
	fi

	# Verify repo exists
	# MiscFunctions
	verifyRepoExists "$SCRIPT_URL";
fi

# Gather OS info
# SystemInfoFunctions
getOSInfo;

# Install script pre-reqs
# InstallFunctions
installPreReqs;

# Check for new functions versions, include url, filename, and script name as variables
for i in "${cfgfiles[@]}"
do
	# MiscFunctions
	checkCfgVer "$CFG_URL" "$i" "$THIS_SCRIPT";
done

# Check for new script version, pass script version, url, and script name variables in that order
# MiscFunctions
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";

# Install additional prereqs
# InstallFunctions
installAdditionalPreReqs;

# Fallback if lsb_release -si returns anything else than Ubuntu, Debian, or Raspbian
# SystemInfoFunctions
wutOSThis;

# Verify compatible OS and version
# SystemInfoFunctions
verifySupportedOS;

# Verify system meets minimum recommended specs
# SystemInfoFunctions
checkTotalSystemMemory;
checkCPUAndThreadCount;

# Check if root
# MiscFunctions
checkRoot;

# Check if Tactical user exists, if not prompt to create it
# MiscFunctions
checkTacticalUser;

# Check language/locale
# SystemInfoFunctions
checkLocale;

# Prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service 2>&1 | tee -a "${currentlog}"

####################
#  Menu Functions  #
####################

# Installation menu
installMenu()
{
  	until [ "$menuselection" = "0" ]; do
		dialog --cr-wrap --clear --no-ok --no-cancel --backtitle "Tactical RMM Installation and Maintenance Utility" --title "Installation Menu" --menu "Use the 'Up' and 'Down' keys to navigate, and the 'Enter' key to make your selections.\n\nSelect Return to return to the previous menu." 0 0 0 \
			1 "${installmenuoptions[0]}" \
      		2 "${installmenuoptions[1]}" \
      		3 "${installmenuoptions[2]}" \
      		4 "${installmenuoptions[3]}" \
			5 "${installmenuoptions[4]}" 2>"${INPUT}"

		menuselection=$(<"${INPUT}")

		case $menuselection in
			1 ) INSTALL_TYPE="install"
        		mainInstall;;
      		2 ) INSTALL_TYPE="devprep"
        		mainInstall;;
      		3 ) INSTALL_TYPE="devinstall"
			  	decideMainRepos
        		mainInstall;;
      		4 ) return;;
			5 ) [ -f $INPUT ] && rm $INPUT
				clear -x
				exit;;
			\?) derpDerp;;
		esac
	done

	return
}

# Utilities menu
utilityMenu()
{
  	until [ "$menuselection" = "0" ]; do
		dialog --cr-wrap --clear --no-ok --no-cancel --backtitle "Tactical RMM Installation and Maintenance Utility" --title "Utility Menu" --menu "Use the 'Up' and 'Down' keys to navigate, and the 'Enter' key to make your selections.\n\nSelect Return to return to the previous menu." 0 0 0 \
			1 "${utilitymenuoptions[0]}" \
      		2 "${utilitymenuoptions[1]}" \
      		3 "${utilitymenuoptions[2]}" \
      		4 "${utilitymenuoptions[3]}" \
      		5 "${utilitymenuoptions[4]}" \
			6 "${utilitymenuoptions[5]}" \
			7 "${utilitymenuoptions[6]}" \
			8 "${utilitymenuoptions[7]}" 2>"${INPUT}"

		menuselection=$(<"${INPUT}")

		case $menuselection in
			1 ) backupTRMM;;
      		2 ) INSTALL_TYPE="restore"
				restoreTRMM;;
      		3 ) getHostAndDomainInfo
				renewCerts;;
			4 ) if [ ! -f /etc/nginx/sites-available/rmm.conf ]; then
					troubleshoot="1"
					getHostAndDomainInfo
				else
					getExistingDomainInfo
				fi
				importCerts;;
			5 ) installFail2ban;;
      		6 ) troubleShoot;;
      		7 ) return;;
			8 ) [ -f $INPUT ] && rm $INPUT
				clear -x
				exit;;
			\?) derpDerp;;
		esac
	done

	return
}

# Update menu
updateMenu()
{
  	until [ "$menuselection" = "0" ]; do
		dialog --cr-wrap --clear --no-ok --no-cancel --backtitle "Tactical RMM Installation and Maintenance Utility" --title "Update Menu" --menu "Use the 'Up' and 'Down' keys to navigate, and the 'Enter' key to make your selections.\n\nSelect Return to return to the previous menu." 0 0 0 \
			1 "${updatemenuoptions[0]}" \
      		2 "${updatemenuoptions[1]}" \
      		3 "${updatemenuoptions[2]}" \
			4 "${updatemenuoptions[3]}" \
			5 "${updatemenuoptions[4]}" 2>"${INPUT}"

		menuselection=$(<"${INPUT}")

		case $menuselection in
			1 ) INSTALL_TYPE="update"
				UPDATE_TYPE="standard"
        		updateTRMM;;
      		2 ) INSTALL_TYPE="update"
				UPDATE_TYPE="standard"
				backupTRMM
        		updateTRMM;;
			3 ) INSTALL_TYPE="update"
				UPDATE_TYPE="forced"
        		updateTRMM;;
      		4 ) return;;
			5 ) [ -f $INPUT ] && rm $INPUT
				clear -x
				exit;;
			\?) derpDerp;;
		esac
	done

	return
}

# Main menu
mainMenu()
{
	# Automated install types install, devprep, or devinstall
	if [ "$autoinstall" == "1" ] && ([ "$INSTALL_TYPE" == "install" ] || [ "$INSTALL_TYPE" == "devinstall" ] || [ "$INSTALL_TYPE" == "devprep" ]); then
		echo 'Defaults        timestamp_timeout=15' | sudo tee /etc/sudoers.d/timeout
		mainInstall;
		sudo rm /etc/sudoers.d/timeout
	# Automated update
	elif [ "$autoinstall" == "1" ] && [ "$INSTALL_TYPE" == "update" ]; then
		echo 'Defaults        timestamp_timeout=15' | sudo tee /etc/sudoers.d/timeout
		updateTRMM;
		sudo rm /etc/sudoers.d/timeout
	# Automated restore
	elif [ "$autoinstall" == "1" ] && [ "$INSTALL_TYPE" == "restore" ]; then
		echo 'Defaults        timestamp_timeout=15' | sudo tee /etc/sudoers.d/timeout
		restoreTRMM;
		sudo rm /etc/sudoers.d/timeout
	# Automated backup
	elif [ "$autoinstall" == "1" ] && [ "$INSTALL_TYPE" == "backup" ]; then
		echo 'Defaults        timestamp_timeout=15' | sudo tee /etc/sudoers.d/timeout
		backupTRMM;
		sudo rm /etc/sudoers.d/timeout
	# Automated troubleshoot
	elif [ "$autoinstall" != "1" ] && [ "$troubleshoot" == "1" ]; then
		echo 'Defaults        timestamp_timeout=15' | sudo tee /etc/sudoers.d/timeout
		troubleShoot;
		sudo rm /etc/sudoers.d/timeout
	else
		until [ "$menuselection" = "0" ]; do
			dialog --cr-wrap --clear --no-ok --no-cancel --backtitle "Tactical RMM Installation and Maintenance Utility" --title "Main Menu" --menu "Use the 'Up' and 'Down' keys to navigate, and the 'Enter' key to make your selections." 0 0 0 \
				1 "${mainmenuoptions[0]}" \
      			2 "${mainmenuoptions[1]}" \
      			3 "${mainmenuoptions[2]}" \
				4 "${mainmenuoptions[3]}" 2>"${INPUT}"

			menuselection=$(<"${INPUT}")

			case $menuselection in
				1 ) installMenu;;
      			2 ) updateMenu;;
      			3 )	utilityMenu;;
				4 ) [ -f $INPUT ] && rm $INPUT
					clear -x
					exit;;
				\?) derpDerp;;
			esac
		done
	fi
	return
}

mainMenu;
