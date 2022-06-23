#!/usr/bin/env bash

### Menu option variables
INPUT=/tmp/menu.sh.$$
menuselection=""

### Arrays
declare -a mainmenuoptions=('Installation' 'Update' 'Utilities' 'Exit')
declare -a installmenuoptions=('Standard Install' 'Dev Test Prereqs' 'Dev Test Install' 'Return' 'Exit')
declare -a updatemenuoptions=('Standard Update' 'Backup and Update' 'Force Update' 'Return' 'Exit')
declare -a utilitymenuoptions=('Backup' 'Restore' 'Renew Certs' 'Import Certs' 'Edit UWSGI config' 'Add Fail2ban - Use at your own risk' 'Run Server Troubleshooter' 'Return' 'Exit')
declare -a cfgfiles=('InputAndError.cfg' 'MiscFunctions.cfg' 'SystemInfoFunctions.cfg' 'UserInput.cfg' 'NetworkFunctions.cfg' 'InstallFunctions.cfg' 'DatabaseFunctions.cfg' 'CertificateFunctions.cfg' 'ConfigAndServiceFunctions.cfg' 'UpdateRestoreFunctions.cfg' 'TroubleshootingFunctions.cfg' 'ParentFunctions.cfg')

### Script Info variables
REPO_OWNER="ninjamonkey198206"
BRANCH="develop-installer-update"
SCRIPT_VERSION="69"
CFG_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}"
SCRIPT_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}/installer-util.sh"
REPO_URL="https://github.com/${REPO_OWNER}/tacticalrmm.git"
SCRIPTS_REPO_URL="https://github.com/amidaware/community-scripts.git"
FRONTEND_URL="https://github.com/amidaware/tacticalrmm-web/releases/download/v${WEB_VERSION}/${webtar}"
THIS_SCRIPT=$(readlink -f "$0")

### Misc info variables
INSTALL_TYPE="install"
UPDATE_TYPE="standard"
SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.10.4'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'
LATEST_SETTINGS_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}/api/tacticalrmm/tacticalrmm/settings.py"

### Variables required for automated install
autoinstall=""
rmmhost=""
frontendhost=""
meshhost=""
letsemail=""
rootdomain=""
sslcacert=""
sslkey=""
sslcert=""


### Get cfg files function
getCfgFiles()
{
	if [ ! -f "$PWD/script-cfg/$2" ]; then
		wget -q "$1/script-cfg/$2" -O "$PWD/script-cfg/$2"
	fi
}

### Check if directory exists, if not, create
if [ ! -d $PWD/script-cfg ]; then
	mkdir $PWD/script-cfg
fi

### Get cfg files
for i in "${cfgfiles[@]}"
do
	getCfgFiles "$CFG_URL" "$i";
done

### Import functions
. $PWD/script-cfg/InputAndError.cfg
. $PWD/script-cfg/MiscFunctions.cfg
. $PWD/script-cfg/SystemInfoFunctions.cfg
. $PWD/script-cfg/UserInput.cfg
. $PWD/script-cfg/NetworkFunctions.cfg
. $PWD/script-cfg/InstallFunctions.cfg
. $PWD/script-cfg/DatabaseFunctions.cfg
. $PWD/script-cfg/CertificateFunctions.cfg
. $PWD/script-cfg/ConfigAndServiceFunctions.cfg
. $PWD/script-cfg/UpdateRestoreFunctions.cfg
. $PWD/script-cfg/TroubleshootingFunctions.cfg
. $PWD/script-cfg/ParentFunctions.cfg

### Get commandline input function
getCommandLineArgs()
{
	while getopts "auto:api:branch:ca:cert:domain:email:help:key:mesh:repo:rmm:" option; do
		case $option in
      		auto ) autoinstall="1"
				INSTALL_TYPE="${OPTARG}";;
			api ) rmmhost="${OPTARG}";;
			branch ) BRANCH="${OPTARG}";;
			ca ) sslcacert="${OPTARG}";;
			cert ) sslcert="${OPTARG}";;
			domain ) rootdomain="${OPTARG}";;
			email ) letsemail="${OPTARG}";;
			help ) helpText
				exit;;
			key ) sslkey="${OPTARG}";;
			mesh ) meshhost="${OPTARG}";;
			repo ) REPO_OWNER="${OPTARG}";;
			rmm ) frontendhost="${OPTARG}";;
	     	\?) echo -e "Error: Invalid option"
				clear -x
				exit 1;;
		esac
	done

	if [ "$autoinstall" == "1" ]; then
		if [ -z "$rmmhost" ] || [ -z "$sslcacert" ] || [ -z "$sslcert" ] || [ -z "$rootdomain" ] || [ -z "$letsemail" ] || [ -z "$sslkey" ] || [ -z "$meshhost" ] || [ -z "$frontendhost" ]; then
			echo -e "Error: To perform an automated installation, you must provide all required information."
			echo -e "\n"
			echo -e "api host, mesh host, rmm host, root domain, email address, CA cert path, Cert path, and Private key path are all required."
			echo -e "\n"
			echo -e "Run ./$THIS_SCRIPT -h for further details."
			clear -x
			exit 1
		elif [ "$INSTALL_TYPE" == "devprep" ] || [ "$INSTALL_TYPE" == "devinstall" ]; then
			if [ "$REPO_OWNER" == "amidaware" ] || [ "$BRANCH" == "master" ]; then
				echo -e "Error: You've selected a developer installation type, but not changed the repo, branch, or both."
				echo -e "\n"
				echo -e "Run ./$THIS_SCRIPT -h for details on how to select them."
				clear -x
				exit 1
			fi
		else
			return
		fi
	fi
}				

### Get commandline input
getCommandLineArgs;

### Set colors
setColors;		# MiscFunctions

### Gather OS info
getOSInfo;		# SystemInfoFunctions

### Install script pre-reqs
installPreReqs;		# InstallFunctions

### Check for new functions versions, include url, filename, and script name as variables
for i in "${cfgfiles[@]}"
do
	checkCfgVer "$CFG_URL" "$i" "$THIS_SCRIPT";		# MiscFunctions
done

### Check for new script version, pass script version, url, and script name variables in that order
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";		# MiscFunctions

### Install additional prereqs
installAdditionalPreReqs;		# InstallFunctions

### Fallback if lsb_release -si returns anything else than Ubuntu, Debian, or Raspbian
wutOSThis;		# SystemInfoFunctions

### Verify compatible OS and version
verifySupportedOS;		# SystemInfoFunctions

### Check if root
checkRoot;		# MiscFunctions

### Check if Tactical user exists, if not prompt to create it
checkTacticalUser;		# MiscFunctions

### Check language/locale
checkLocale;	# SystemInfoFunctions

### Prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

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
			* ) derpDerp;;
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
			8 "${utilitymenuoptions[7]}" \
			9 "${utilitymenuoptions[8]}" 2>"${INPUT}"

		menuselection=$(<"${INPUT}")

		case $menuselection in
			1 ) backupTRMM;;
      		2 ) INSTALL_TYPE="restore"
				restoreTRMM;;
      		3 ) renewCerts;;
			4 ) importCerts;;
			5 ) changeUWSGIProcs;;
			6 ) installFail2ban;;
      		7 ) troubleShoot;;
      		8 ) return;;
			9 ) [ -f $INPUT ] && rm $INPUT
				clear -x
				exit;;
			* ) derpDerp;;
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
			* ) derpDerp;;
		esac
	done

	return
}

# Main menu
mainMenu()
{
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
			* ) derpDerp;;
		esac
	done

	return
}

mainMenu;
