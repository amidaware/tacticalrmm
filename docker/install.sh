#!/usr/bin/env bash
set -o nounset
set -o errexit
set -o pipefail

temp="/tmp/tactical"

args="$*"
version="latest"
branch="master"

branchRegex=" --branch ([^ ]+)"
if [[ " ${args}" =~ ${branchRegex} ]]; then
  branch="${BASH_REMATCH[1]}"
fi

echo "branch=${branch}"
tactical_cli="https://raw.githubusercontent.com/wh1te909/tacticalrmm/${branch}/docker/tactical-cli"

versionRegex=" --version ([^ ]+)"
if [[ " ${args}" =~ ${versionRegex} ]]; then
  version="${BASH_REMATCH[1]}"
fi

rm -rf "${temp}"
if ! mkdir "${temp}"; then
  echo >&2 "Failed to create temporary directory"
  exit 1
fi

cd "${temp}"
echo "Downloading tactical-cli from branch ${branch}"
if ! curl -sS "${tactical_cli}"; then
  echo >&2 "Failed to download installation package ${tactical_cli}"
  exit 1
fi

chmod +x tactical-cli
./tactical-cli ${args} --version "${version}" 2>&1 | tee -a ~/install.log

cd ~
if ! rm -rf "${temp}"; then
  echo >&2 "Warning: Failed to remove temporary directory ${temp}"
fi
