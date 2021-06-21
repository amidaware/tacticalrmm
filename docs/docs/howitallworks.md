# How It All Works

INSERT WIREFRAME GRAPHIC HERE USING <https://www.yworks.com/yed-live/>

## Server

## Windows Agent

Found in `%programfiles%\TacticalAgent`

### Services

3 services exist on all clients

* `Mesh Agent`
![MeshService](images/trmm_services_mesh.png)
![MeshAgentTaskManager](images/trmm_services__taskmanager_mesh.png)

**AND**

* `TacticalAgent` and `Tactical RMM RPC Service`
![TacticalAgentServices](images/trmm_services.png)
![TacticalAgentTaskManager](images/trmm_services__taskmanager_agent.png)

The [MeshCentral](https://meshcentral.com/) system which is accessible from <https://mesh.example.com> and is used

`Tactical RMM Agent`

* It runs 2 goroutines
  * one is the checkrunner which runs all the checks and then just sleeps until it's time to run more checks
  * 2nd goroutine periodically sends info about the agent to the rmm and also handles agent recovery

!!!note
    In Task Manager you will see additional `Tactical RMM Agent` processes appear and disappear. These are your Checks and Tasks running at scheduled intervals

`Tactical RMM RPC Service`

* Uses the pub/sub model so anytime you do anything realtime from rmm (like a send command or run script)
* It maintains a persistent connection to your to the api.example.com rmm server on `port:4222` and is listening for events (using [nats](https://nats.io/))
* It handles your Agent updates (Auto triggers at 35mins past every hour or when run manually from server Agents | Update Agents menu)

***

### Agent Installation Process

* Adds Defender AV exclusions
* Copies temp files to `c:\windows\temp\tacticalxxx` folder.
* INNO setup installs app into `%ProgramData%\TacticalAgent\` folder

***

### Agent Update Process

Downloads latest `winagent-vx.x.x-x86/64.exe` to `%programfiles%`

Executes the file (INNO setup exe)

Files create `c:\Windows\temp\Tacticalxxxx\` folder for install (and log files)
