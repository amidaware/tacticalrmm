#!/bin/bash
#
# https://www.freecodecamp.org/news/how-to-implement-runtime-environment-variables-with-create-react-app-docker-and-nginx-7f9d42a91d70/
#

# Recreate js config file
rm -rf ${PUBLIC_DIR}/env-config.js
touch ${PUBLIC_DIR}/env-config.js

# Add assignment 
echo "window._env_ = {PROD_URL: \"${API_HOST}\"}" >> ${PUBLIC_DIR}/env-config.js
