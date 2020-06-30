#!/bin/sh

node node_modules/meshcentral --createaccount ${MESH_USER} --pass ${MESH_PASS} --email ${EMAIL_USER}
node node_modules/meshcentral --adminaccount ${MESH_USER}

FILE=/token/token.key
if [ ! -f "$FILE" ]; then
    node ./node_modules/meshcentral --logintokenkey > /token/token.key
fi

node node_modules/meshcentral
