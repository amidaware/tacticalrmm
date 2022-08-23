#!/usr/bin/env bash

if [ $EUID -ne 0 ]; then
  echo "ERROR: Must be run as root"
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

agentBinPath='/opt/tactical'
binName='tacticalagent'
agentBin="${agentBinPath}/${binName}"
agentConf='/etc/tacticalagent'
agentSvcName='com.tactical.plist'
agentSysD="/Library/LaunchDaemons/com.tactical.plist"
meshDir='/usr/local/mesh_services'
meshSystemBin="/usr/local/mesh_services/meshagent/meshagent_osx64"
meshSvcName='meshagent.service'
meshSysD="/lib/systemd/system/${meshSvcName}"

RemoveOldAgent() {
    echo "Uninstalling Tactical agent..."
    launchctl stop "${agentSvcName}"
    launchctl unload ${agentSysD}
    rm ${agentSysD}
    rm "${agentBinPath}/${binName}"
    rm /etc/tacticalagent
    ${meshSystemBin} -uninstall
}

InstallMesh() {
    meshTmpDir=$(mktemp -d)
    meshTmpBin="${meshTmpDir}/MeshAgent.zip"
    curl -k "${meshDL}" -Lo "${meshTmpBin}"
    unzip -d "${meshTmpDir}" "${meshTmpBin}" > /dev/null 2>&1
    installer -pkg "${meshTmpDir}/MeshAgent.mpkg" -target /
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
curl -k "${agentDL}" -Lo "${agentBin}"
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

if [ $# -ne 0 ] && [ $1 == '--debug' ]; then
    INSTALL_CMD="${agentBin} -m install -api ${apiURL} -client-id ${clientID} -site-id ${siteID} -agent-type ${agentType} -auth ${token} -log debug"
else
    INSTALL_CMD="${agentBin} -m install -api ${apiURL} -client-id ${clientID} -site-id ${siteID} -agent-type ${agentType} -auth ${token}"
fi

if [ "${MESH_NODE_ID}" != '' ]; then
    INSTALL_CMD+=" -meshnodeid ${MESH_NODE_ID}"
fi

if [ "${proxy}" != '' ]; then
    INSTALL_CMD+=" -proxy ${proxy}"
fi

eval ${INSTALL_CMD}

tacticalsvc="$(cat << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>Label</key>
        <string>com.tactical.plist</string>
        <key>ServiceDescription</key>
        <string>Tactical RMM Service</string>
        <key>ProgramArguments</key>
        <array>             
            <string>${agentBin}</string>
            <string>-m</string>
            <string>svc</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <true/>
    </dict>
</plist>
EOF
)"

echo "${tacticalsvc}" | tee ${agentSysD} > /dev/null
launchctl load ${agentSysD}
launchctl start com.tactical.plist
