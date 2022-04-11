# Tactical RMM

![CI Tests](https://github.com/amidaware/tacticalrmm/actions/workflows/ci-tests.yml/badge.svg?branch=develop)
[![Coverage Status](https://coveralls.io/repos/github/amidaware/tacticalrmm/badge.svg?branch=develop)](https://coveralls.io/github/amidaware/tacticalrmm?branch=develop)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Tactical RMM is a remote monitoring & management tool, built with Django and Vue.\
It uses an [agent](https://github.com/amidaware/rmmagent) written in golang and integrates with [MeshCentral](https://github.com/Ylianst/MeshCentral)

# [LIVE DEMO](https://rmm.tacticalrmm.io/)
Demo database resets every hour. A lot of features are disabled for obvious reasons due to the nature of this app.

### [Discord Chat](https://discord.gg/upGTkWp)

### [Documentation](https://docs.tacticalrmm.com)

## Features

- Teamviewer-like remote desktop control
- Real-time remote shell
- Remote file browser (download and upload files)
- Remote command and script execution (batch, powershell and python scripts)
- Event log viewer
- Services management
- Windows patch management
- Automated checks with email/SMS alerting (cpu, disk, memory, services, scripts, event logs)
- Automated task runner (run scripts on a schedule)
- Remote software installation via chocolatey
- Software and hardware inventory

## Windows agent versions supported

- Windows 7, 8.1, 10, 11, Server 2008R2, 2012R2, 2016, 2019, 2022

## Linux agent versions supported
- Any distro with systemd

## Installation / Backup / Restore / Usage

### Refer to the [documentation](https://docs.tacticalrmm.com)
