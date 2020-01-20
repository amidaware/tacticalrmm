# Tactical RMM

[![Build Status](https://travis-ci.com/wh1te909/tacticalrmm.svg?branch=develop)](https://travis-ci.com/wh1te909/tacticalrmm)
[![Build Status](https://dev.azure.com/dcparsi/Tactical%20RMM/_apis/build/status/wh1te909.tacticalrmm?branchName=master)](https://dev.azure.com/dcparsi/Tactical%20RMM/_build/latest?definitionId=4&branchName=master)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Tactical RMM is a remote monitoring & management tool for Windows computers, built with Django and Vue.\
It uses an [agent](https://github.com/wh1te909/winagent) written in python, as well as the [SaltStack](https://github.com/saltstack/salt) api and [MeshCentral](https://github.com/Ylianst/MeshCentral)

*Tactical RMM is currently in alpha and subject to breaking changes. Use in production at your own risk.*

## Features

- Teamviewer-like remote desktop control
- Real-time remote shell
- Remote file browser (download and upload files)
- Remote command and script execution
- Event log viewer
- Services management
- Windows patch management
- Automated checks with email/SMS alerting (cpu, disk, memory, services, event logs)
- Remote software installation via chocolatey
- Software and hardware inventory

## Server Requirements

- Any modern linux distro (an install script is provided for Ubuntu Server 18.04)
- A domain you own with at least 3 subdomains
- Google Authenticator app (2 factor is NOT optional)

## Windows versions supported

- Windows 7, 8.1, 10, Server 2008R2, 2012R2, 2016, 2019