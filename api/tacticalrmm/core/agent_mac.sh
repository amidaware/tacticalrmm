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

RemoveOldAgent() {
    echo "Uninstalling Tactical agent..."
    launchctl stop "${agentSvcName}"
    launchctl unload ${agentSysD}
    rm ${agentSysD}
    rm "${agentBinPath}/${binName}"
    rm /etc/tacticalagent
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
    if [ -f "/usr/local/mesh_services/meshagent/meshagent_osx64" ]; then
        echo "Stopping Mesh Agent…"
        sudo /bin/launchctl unload /Library/LaunchDaemons/meshagent_osx64_LaunchDaemon.plist
        sudo /bin/launchctl unload /Library/LaunchDaemons/meshagentDiagnostic_periodicStart.plist &> /dev/null
        sudo /bin/launchctl unload /Library/LaunchDaemons/meshagentDiagnostic.plist &> /dev/null
        sudo rm /Library/LaunchDaemons/meshagentDiagnostic_periodicStart.plist &> /dev/null
        sudo rm /Library/LaunchDaemons/meshagentDiagnostic.plist &> /dev/null
        sudo rm /usr/local/mesh_services/meshagent/meshagent_osx64
        sudo rm /usr/local/mesh_services/meshagentDiagnostic/meshagentDiagnostic &> /dev/null
        sudo rm /Library/LaunchDaemons/meshagent_osx64_LaunchDaemon.plist
        sudo rm /Library/LaunchAgents/meshagent_osx64_LaunchAgent.plist
        sudo rm -R /usr/local/mesh_services/meshagent
        echo "Mesh Agent was uninstalled."
    else
        echo "Mesh install not detected"
    fi
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
    if [[ $(sysctl machdep.cpu.brand_string) != *"Intel"* ]]; then
        echo "Skipping mesh, did not detect a supported mesh platform."
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