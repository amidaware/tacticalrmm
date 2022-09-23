#!/bin/bash

/usr/local/mesh_services/meshagent/meshagent -fulluninstall
launchctl bootout system /Library/LaunchDaemons/tacticalagent.plist
rm -rf /usr/local/mesh_services
rm -f /etc/tacticalagent
rm -rf /opt/tacticalagent
rm -f /Library/LaunchDaemons/tacticalagent.plist