#!/bin/bash

### Menu option variables
INPUT=/tmp/menu.sh.$$
menuselection=""
declare -a menuoptions=('Test Install' 'Exit')
#declare -a menuoptions=('Dev Test Prereqs' 'Dev Test Install' 'Standard Install' 'Standard Update' 'Force Update' 'Backup' 'Restore' 'Renew Certs')
REPO_URL='https://github.com/ninjamonkey198206/tacticalrmm.git'
SCRIPTS_REPO_URL='https://github.com/amidaware/community-scripts.git'
FRONTEND_URL='https://github.com/amidaware/tacticalrmm-web/releases/download/v${WEB_VERSION}/${webtar}'
BRANCH="develop-bash-updates"
INSTALL_TYPE="install"
UPDATE_TYPE=""
CERTRENEW=""

### Script Info variables
SCRIPT_VERSION="63"
SCRIPT_URL='https://raw.githubusercontent.com/ninjamonkey198206/tacticalrmm/develop-bash-updates/install.sh'
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

# Main menu
mainMenu()
{
	until [ "$menuselection" = "0" ]; do
		dialog --cr-wrap --clear --no-ok --no-cancel --backtitle "Tactical RMM Installation and Maintenance Utility" --title "Main Menu" --menu "Use the 'Up' and 'Down' keys to navigate, and the 'Enter' key to make your selections." 0 0 0 \
			1 "${menuoptions[0]}" \
			2 "${menuoptions[1]}" 2>"${INPUT}"

		menuselection=$(<"${INPUT}")

		case $menuselection in
			1 ) mainInstall;;
			2 ) [ -f $INPUT ] && rm $INPUT
				exit;;
			* ) derpDerp;;
		esac
	done

	return
}

mainMenu;