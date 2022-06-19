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
BASE_SCRIPT_URL="https://raw.githubusercontent.com/${REPO_OWNER}/tacticalrmm/${BRANCH}"
SCRIPT_VERSION="66"
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

### Get cfg files function
getCfgFiles()
{
	if [ ! -f "$PWD/$2" ]; then
		wget -q "$1/bash/$2" -O "$PWD/bash/$2"
	fi
}

### Get bashfunctions file
getCfgFiles "$BASE_SCRIPT_URL" "bashfunctions.cfg";

mkdir -p $PWD/bash
### Get cfg files
for i in "${cfgfiles[@]}"
do
	getCfgFiles "$BASE_SCRIPT_URL" "$i";
done

### Import functions
. $PWD/bashfunctions.cfg

### Set colors
setColors;		# MiscFunctions

### Gather OS info
getOSInfo;		# SystemInfoFunctions

### Install script pre-reqs
installPreReqs;		# InstallFunctions

### Check for new functions version, only include script name as variable
checkCfgVer "$BASE_SCRIPT_URL" "bashfunctions.cfg" "$THIS_SCRIPT";

### Check for new script version, pass script version, url, and script name variables in that order
checkScriptVer "$SCRIPT_VERSION" "$SCRIPT_URL" "$THIS_SCRIPT";

### Install additional prereqs
installAdditionalPreReqs;		# InstallFunctions

### Fallback if lsb_release -si returns anything else than Ubuntu, Debian, or Raspbian
wutOSThis;		# SystemInfoFunctions

### Verify compatible OS and version
verifySupportedOS;		# SystemInfoFunctions

### Check if root
checkRoot;		# MiscFunctions

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
      		2 ) restoreTRMM;;
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
			1 ) UPDATE_TYPE="standard"
        		updateTRMM;;
      		2 ) UPDATE_TYPE="standard"
				backupTRMM
        		updateTRMM;;
			3 ) UPDATE_TYPE="forced"
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
