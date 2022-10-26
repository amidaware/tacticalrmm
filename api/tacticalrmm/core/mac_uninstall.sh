#!/bin/bash

if [ -f /usr/local/mesh_services/meshagent/meshagent ]; then
  /usr/local/mesh_services/meshagent/meshagent -fulluninstall
fi

if [ -f /opt/tacticalmesh/meshagent ]; then
  /opt/tacticalmesh/meshagent -fulluninstall
fi

launchctl bootout system /Library/LaunchDaemons/tacticalagent.plist
rm -rf /usr/local/mesh_services
rm -rf /opt/tacticalmesh
rm -f /etc/tacticalagent
rm -rf /opt/tacticalagent
rm -f /Library/LaunchDaemons/tacticalagent.plist