
const common = {
    email_alert: false,
    failure_count: 0,
    failures: 5,
    history: [],
    last_run: null,
    more_info: null,
    status: "pending",
    task_on_failure: null,
    text_alert: false,
    agent: null,
    policy: 1
  };

const diskcheck = {
id: 1,
check_type: "diskspace",
disk: "C:",
threshold: 25,
readable_desc: "Disk space check: Drive C",
...common
};

const cpuloadcheck = {
id: 2,
check_type: "cpuload",
cpuload: 85,
readable_desc: "CPU Load check: > 85%",
...common
};

const memcheck = {
id: 3,
check_type: "memory",
threshold: 75,
readable_desc: "Memory checks: > 85%",
...common
};

const scriptcheck = {
id: 4,
check_type: "script",
execution_time: "0.0000",
retcode: 0,
script: {
    description: "Test",
    filename: "local_admin_group.bat",
    filepath: "salt://scripts//userdefined//local_admin_group.bat",
    id: 1,
    name: "Test Script",
    shell: "cmd"
},
stderr: null,
stdout: null,
timeout: 120,
readable_desc: "Script check: Test Script",
...common
};

const winservicecheck = {
id: 5,
check_type: "winsvc",
pass_if_start_pending: false,
restart_if_stopped: false,
svc_display_name: "Agent Activation Runtime_1232as",
svc_name: "AarSvc_1232as",
readable_desc: "Service check: Agent Activation Runtime_1232as",
...common
};

const pingcheck = {
id: 6,
name: "fghfgh",
check_type: "ping",
ip: "10.10.10.10",
readable_desc: "Ping Check: Test Ping Check",
...common
};

const eventlogcheck = {
id: 7,
desc: "asasasa",
check_type: "eventlog",
log_name: "Application",
event_id: 1456,
event_type: "ERROR",
fail_when: "contains",
search_last_days: 1,
readable_desc: "Event log check: asdsasa",
...common,
};

const tasks = [{"id":1,"assigned_check":null,"schedule":"Manual","name":"fghf","run_time_days":[],"run_time_minute":null,"task_type":"manual","win_task_name":"TacticalRMM_UiOgoHSkrxtqWbSZVCGhvjjGdQflZlpnjkd","timeout":120,"retcode":null,"stdout":null,"stderr":null,"execution_time":"0.0000","last_run":null,"enabled":true,"agent":null,"policy":1,"script":1},{"id":2,"assigned_check":null,"schedule":"Mon,Tue at 12:03 AM","name":"vjhkgh","run_time_days":[0,1],"run_time_minute":"00:03","task_type":"scheduled","win_task_name":"TacticalRMM_KlgPQGGgoVcGEnDXXxJSDjymyTGArTzsVSw","timeout":120,"retcode":null,"stdout":null,"stderr":null,"execution_time":"0.0000","last_run":null,"enabled":true,"agent":null,"policy":1,"script":1},{"id":3,"assigned_check":{"id":2,"readable_desc":"Ping Check: 10.10.10.10","script":null,"assigned_task":{"id":1,"name":"test","run_time_days":[],"run_time_minute":null,"task_type":"checkfailure","win_task_name":"TacticalRMM_XROsZidGyNuUEwzvvdlgveDwxsrIKRAlHpr","timeout":120,"retcode":null,"stdout":null,"stderr":null,"execution_time":"0.0000","last_run":null,"enabled":true,"agent":null,"policy":1,"script":1,"assigned_check":2},"history_info":null,"name":"asdfasd","check_type":"ping","status":"pending","more_info":null,"last_run":null,"email_alert":false,"text_alert":false,"fails_b4_alert":1,"fail_count":0,"email_sent":null,"text_sent":null,"outage_history":null,"extra_details":null,"threshold":null,"disk":null,"ip":"10.10.10.10","timeout":null,"stdout":null,"stderr":null,"retcode":null,"execution_time":null,"history":[],"svc_name":null,"svc_display_name":null,"pass_if_start_pending":null,"restart_if_stopped":null,"svc_policy_mode":null,"log_name":null,"event_id":null,"event_type":null,"fail_when":null,"search_last_days":null,"agent":null,"policy":1},"schedule":"Every time check fails","name":"test","run_time_days":[],"run_time_minute":null,"task_type":"checkfailure","win_task_name":"TacticalRMM_XROsZidGyNuUEwzvvdlgveDwxsrIKRAlHpr","timeout":120,"retcode":null,"stdout":null,"stderr":null,"execution_time":"0.0000","last_run":null,"enabled":true,"agent":null,"policy":1,"script":1}]

export {
  diskcheck,
  cpuloadcheck,
  memcheck,
  scriptcheck,
  winservicecheck,
  pingcheck,
  eventlogcheck,
  tasks
}