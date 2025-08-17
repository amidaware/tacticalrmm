#!/bin/bash

if [ -f /usr/local/mesh_services/meshagent/meshagent ]; then
  /usr/local/mesh_services/meshagent/meshagent -fulluninstall
fi

if [ -f /opt/scnmesh/meshagent ]; then
  /opt/scnmesh/meshagent -fulluninstall
fi

launchctl bootout system /Library/LaunchDaemons/scnagent.plist
rm -rf /usr/local/mesh_services
rm -rf /opt/scnmesh
rm -f /etc/scnagent
rm -rf /opt/scnagent
rm -f /Library/LaunchDaemons/scnagent.plist