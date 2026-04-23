#!/usr/bin/env bash

if [ $EUID -ne 0 ]; then
    echo "ERROR: Must be run as root"
    exit 1
fi

HAS_SYSTEMD=$(ps --no-headers -o comm 1)
if [ "${HAS_SYSTEMD}" != 'systemd' ]; then
    echo "This install script only supports systemd"
    echo "Please install systemd or manually create the service using your systems's service manager"
    exit 1
fi

if [[ $DISPLAY ]]; then
    echo "ERROR: Display detected. Installer only supports running headless, i.e from ssh."
    echo "If you cannot ssh in then please run 'sudo systemctl isolate multi-user.target' to switch to a non-graphical user session and run the installer again."
    echo "If you are already running headless, then you are probably running with X forwarding which is setting DISPLAY, if so then simply run"
    echo "unset DISPLAY"
    echo "to unset the variable and then try running the installer again"
    exit 1
fi

DEBUG=0
INSECURE=0
NOMESH=0
UNINSTALL=0

# INSTALL_PREFIX relocates the agent's install (/bin, /etc, /opt) to account for
# read-only systems. Empty defaults to /. May be set via INSTALL_PREFIX env var
# or --install-prefix.
INSTALL_PREFIX="${INSTALL_PREFIX:-}"

agentDL='agentDLChange'
meshDL='meshDLChange'

apiURL='apiURLChange'
token='tokenChange'
clientID='clientIDChange'
siteID='siteIDChange'
agentType='agentTypeChange'
proxy=''

binName='tacticalagent'
agentSvcName='tacticalagent.service'
meshSvcName='meshagent.service'

# derive_prefixed_paths is called again after arg parsing so --install-prefix can
# override the INSTALL_PREFIX env var. Every path is prefixed with INSTALL_PREFIX.
derive_prefixed_paths() {
    INSTALL_PREFIX="${INSTALL_PREFIX%/}"
    if [ -n "${INSTALL_PREFIX}" ]; then
        agentBinPath="${INSTALL_PREFIX}/bin"
    else
        agentBinPath="/usr/local/bin"
    fi
    agentBin="${agentBinPath}/${binName}"
    agentConf="${INSTALL_PREFIX}/etc/tacticalagent"
    agentSysD="${INSTALL_PREFIX}/etc/systemd/system/${agentSvcName}"
    agentDir="${INSTALL_PREFIX}/opt/tacticalagent"
    meshDir="${INSTALL_PREFIX}/opt/tacticalmesh"
    meshSystemBin="${meshDir}/meshagent"
    meshSysD="${INSTALL_PREFIX}/lib/systemd/system/${meshSvcName}"
}
derive_prefixed_paths

deb=(ubuntu debian raspbian kali linuxmint)
rhe=(fedora rocky centos rhel amzn arch opensuse)

set_locale_deb() {
    locale-gen "en_US.UTF-8"
    localectl set-locale LANG=en_US.UTF-8
    . /etc/default/locale
}

set_locale_rhel() {
    localedef -c -i en_US -f UTF-8 en_US.UTF-8 >/dev/null 2>&1
    localectl set-locale LANG=en_US.UTF-8
    . /etc/locale.conf
}

RemoveOldAgent() {
    if [ -f "${agentSysD}" ]; then
        systemctl disable ${agentSvcName}
        systemctl stop ${agentSvcName}
        rm -f "${agentSysD}"
        systemctl daemon-reload
    fi

    # Remove the compatibility symlink in systemd's default search path if we
    # previously created one for a prefixed install.
    if [ -L "/etc/systemd/system/${agentSvcName}" ]; then
        rm "/etc/systemd/system/${agentSvcName}"
    fi

    if [ -f "${agentConf}" ]; then
        rm -f "${agentConf}"
    fi

    if [ -f "${agentBin}" ]; then
        rm -f "${agentBin}"
    fi

    if [ -d "${agentDir}" ]; then
        rm -rf "${agentDir}"
    fi
}

InstallMesh() {
    if [ -f /etc/os-release ]; then
        distroID=$(
            . /etc/os-release
            echo $ID
        )
        distroIDLIKE=$(
            . /etc/os-release
            echo $ID_LIKE
        )
        if [[ " ${deb[*]} " =~ " ${distroID} " ]]; then
            set_locale_deb
        elif [[ " ${deb[*]} " =~ " ${distroIDLIKE} " ]]; then
            set_locale_deb
        elif [[ " ${rhe[*]} " =~ " ${distroID} " ]]; then
            set_locale_rhel
        else
            set_locale_rhel
        fi
    fi

    meshTmpDir="${INSTALL_PREFIX}/root/meshtemp"
    mkdir -p $meshTmpDir

    meshTmpBin="${meshTmpDir}/meshagent"
    wget --no-check-certificate -q -O ${meshTmpBin} "${meshDL}"
    chmod +x ${meshTmpBin}
    mkdir -p ${meshDir}
    env LC_ALL=en_US.UTF-8 LANGUAGE=en_US XAUTHORITY=foo DISPLAY=bar ${meshTmpBin} -install --installPath=${meshDir}
    sleep 1
    rm -rf ${meshTmpDir}
}

RemoveMesh() {
    if [ -f "${meshSystemBin}" ]; then
        env XAUTHORITY=foo DISPLAY=bar ${meshSystemBin} -uninstall
        sleep 1
    fi

    if [ -f "${meshSysD}" ]; then
        systemctl stop ${meshSvcName} >/dev/null 2>&1
        systemctl disable ${meshSvcName} >/dev/null 2>&1
        rm -f ${meshSysD}
    fi

    rm -rf ${meshDir}
    systemctl daemon-reload
}

Uninstall() {
    RemoveMesh
    RemoveOldAgent
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
    -debug | --debug | debug) DEBUG=1 ;;
    -insecure | --insecure | insecure) INSECURE=1 ;;
    -nomesh | --nomesh | nomesh) NOMESH=1 ;;
    uninstall | -uninstall | --uninstall) UNINSTALL=1 ;;
    --install-prefix=*) INSTALL_PREFIX="${1#*=}" ;;
    --install-prefix | -install-prefix)
        shift
        INSTALL_PREFIX="$1"
        ;;
    *)
        echo "ERROR: Unknown parameter: $1"
        exit 1
        ;;
    esac
    shift
done

derive_prefixed_paths

if [[ $UNINSTALL -eq 1 ]]; then
    Uninstall
    # Remove the current script
    rm "$0"
    exit 0
fi

RemoveOldAgent

mkdir -p \
    "${agentBinPath}" \
    "$(dirname "${agentConf}")" \
    "$(dirname "${agentSysD}")" \
    "${agentDir}" \
    "${meshDir}" \
    "$(dirname "${meshSysD}")"

echo "Downloading tactical agent..."
wget -q -O ${agentBin} "${agentDL}"
if [ $? -ne 0 ]; then
    echo "ERROR: Unable to download tactical agent"
    exit 1
fi
chmod +x ${agentBin}

MESH_NODE_ID=""

if [[ $NOMESH -eq 1 ]]; then
    echo "Skipping mesh install"
else
    if [ -f "${meshSystemBin}" ]; then
        RemoveMesh
    fi
    echo "Downloading and installing mesh agent..."
    InstallMesh
    sleep 2
    echo "Getting mesh node id..."
    MESH_NODE_ID=$(env XAUTHORITY=foo DISPLAY=bar ${agentBin} -m nixmeshnodeid)
fi

INSTALL_CMD="${agentBin} -m install -api ${apiURL} -client-id ${clientID} -site-id ${siteID} -agent-type ${agentType} -auth ${token}"

if [ "${MESH_NODE_ID}" != '' ]; then
    INSTALL_CMD+=" --meshnodeid ${MESH_NODE_ID}"
fi

if [[ $DEBUG -eq 1 ]]; then
    INSTALL_CMD+=" --log debug"
fi

if [[ $INSECURE -eq 1 ]]; then
    INSTALL_CMD+=" --insecure"
fi

if [ "${proxy}" != '' ]; then
    INSTALL_CMD+=" --proxy ${proxy}"
fi

if [ -n "${INSTALL_PREFIX}" ]; then
    INSTALL_CMD+=" -install-prefix ${INSTALL_PREFIX}"
fi

eval "${INSTALL_CMD}"

if [ -n "${INSTALL_PREFIX}" ]; then
    prefixEnvLine="Environment=INSTALL_PREFIX=${INSTALL_PREFIX}"$'\n'
else
    prefixEnvLine=""
fi

tacticalsvc="$(
    cat <<EOF
[Unit]
Description=Tactical RMM Linux Agent

[Service]
Type=simple
${prefixEnvLine}ExecStart=${agentBin} -m svc
User=root
Group=root
Restart=always
RestartSec=5s
LimitNOFILE=1000000
KillMode=process

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${tacticalsvc}" | tee ${agentSysD} >/dev/null

# If /etc/systemd/system is writable, a symlink is created to "install" the service.
# This makes it easy to "reinstall" the service if /etc/ is wiped; TrueNAS does this
# on upgrades. Recreating the symlink is left up to the user.
if [ -n "${INSTALL_PREFIX}" ]; then
    if [ -w "/etc/systemd/system" ]; then
        linkPath="/etc/systemd/system/${agentSvcName}"
        if [ -L "${linkPath}" ] || [ -e "${linkPath}" ]; then
            rm "${linkPath}"
        fi
        ln -s "${agentSysD}" "${linkPath}"
    else
        echo "WARNING: /etc/systemd/system is not writable; skipping service enable/start."
        exit 0
    fi
fi

systemctl daemon-reload
systemctl enable ${agentSvcName}
systemctl start ${agentSvcName}
