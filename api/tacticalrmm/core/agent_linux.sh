#!/usr/bin/env bash

if [ $EUID -ne 0 ]; then
  echo "ERROR: Must be run as root"
  exit 1
fi

HAS_SYSTEMD=$(ps --no-headers -o comm 1)
if [ "${HAS_SYSTEMD}" != 'systemd1' ]; then
    echo "This install script only supports systemd"
    echo "Please install systemd or manually create the service using your systems's service manager"
    exit 1
fi

agentDL='agentDLChange'
meshDL='meshDLChange'

apiURL='apiURLChange'
token='tokenChange'
clientID='clientIDChange'
siteID='siteIDChange'
agentType='agentTypeChange'
proxy=''

agentBinPath='/usr/local/bin'
binName='tacticalagent'
agentBin="${agentBinPath}/${binName}"
agentConf='/etc/tacticalagent'
agentSvcName='tacticalagent.service'
agentSysD="/etc/systemd/system/${agentSvcName}"
meshDir='/opt/tacticalmesh'
meshSystemBin="${meshDir}/meshagent"
meshSvcName='meshagent.service'
meshSysD="/lib/systemd/system/${meshSvcName}"

RemoveOldAgent() {
    if [ -f "${agentSysD}" ]; then
        systemctl disable --now ${agentSvcName}
        rm -f ${agentSysD}
        systemctl daemon-reload
    fi

    if [ -f "${agentConf}" ]; then
        rm -f ${agentConf}
    fi

    if [ -f "${agentBin}" ]; then
        rm -f ${agentBin}
    fi
}

InstallMesh() {
    meshTmpDir=$(mktemp -d -t "mesh-XXXXXXXXX")
    meshTmpBin="${meshTmpDir}/meshagent"
    wget -q -O ${meshTmpBin} ${meshDL}
    chmod +x ${meshTmpBin}
    mkdir -p ${meshDir}
    ${meshTmpBin} -install --installPath=${meshDir}
    sleep 1
    rm -rf ${meshTmpDir}
}

RemoveMesh() {
    if [ -f "${meshSystemBin}" ]; then
        ${meshSystemBin} -uninstall
        sleep 1
    fi

    if [ -f "${meshSysD}" ]; then
        systemctl disable --now ${meshSvcName} > /dev/null 2>&1
        rm -f ${meshSysD}
    fi

    rm -rf ${meshDir}
    systemctl daemon-reload
}

Uninstall() {
    RemoveMesh
    RemoveOldAgent
}

if [ $# -ne 0 ] && [ $1 == 'uninstall' ]; then
    Uninstall
    exit 0
fi

RemoveOldAgent

echo "Downloading tactical agent..."
wget -q -O ${agentBin} "${agentDL}"
chmod +x ${agentBin}

MESH_NODE_ID=""

if [ $# -ne 0 ] && [ $1 == '--nomesh' ]; then
    echo "Skipping mesh install"
else
    if [ -f "${meshSystemBin}" ]; then
        RemoveMesh
    fi
    echo "Downloading and installing mesh agent..."
    InstallMesh
    sleep 2
    echo "Getting mesh node id..."
    MESH_NODE_ID=$(${agentBin} -m nixmeshnodeid)
fi

if [ ! -d "${agentBinPath}" ]; then
    echo "Creating ${agentBinPath}"
    mkdir -p ${agentBinPath}
fi

INSTALL_CMD="${agentBin} -m install -api ${apiURL} -client-id ${clientID} -site-id ${siteID} -agent-type ${agentType} -auth ${token}"

if [ "${MESH_NODE_ID}" != '' ]; then
    INSTALL_CMD+=" -meshnodeid ${MESH_NODE_ID}"
fi

if [ "${proxy}" != '' ]; then
    INSTALL_CMD+=" -proxy ${proxy}"
fi

eval ${INSTALL_CMD}

tacticalsvc="$(cat << EOF
[Unit]
Description=Tactical RMM Linux Agent

[Service]
Type=simple
ExecStart=${agentBin} -m svc
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
echo "${tacticalsvc}" | tee ${agentSysD} > /dev/null

systemctl daemon-reload
systemctl enable --now ${agentSvcName}