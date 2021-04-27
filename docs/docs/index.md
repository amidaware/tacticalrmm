# Tactical RMM Documentation

[![Build Status](https://dev.azure.com/dcparsi/Tactical%20RMM/_apis/build/status/wh1te909.tacticalrmm?branchName=develop)](https://dev.azure.com/dcparsi/Tactical%20RMM/_build/latest?definitionId=4&branchName=develop)
[![Coverage Status](https://coveralls.io/repos/github/wh1te909/tacticalrmm/badge.png?branch=develop&kill_cache=1)](https://coveralls.io/github/wh1te909/tacticalrmm?branch=develop)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Tactical RMM is a remote monitoring & management tool for Windows computers, built with Django, Vue and Golang.
It uses an [agent](https://github.com/wh1te909/rmmagent) written in Golang and integrates with [MeshCentral](https://github.com/Ylianst/MeshCentral)

## [LIVE DEMO](https://rmm.tacticalrmm.io/)

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
