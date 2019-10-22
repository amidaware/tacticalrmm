import datetime
from datetime import timezone
from statistics import mean

from djangormm.celery import app
from django.core.exceptions import ObjectDoesNotExist

from agents.models import Agent
from .models import ( 
    DiskCheck, 
    DiskCheckEmail, 
    PingCheck, 
    PingCheckEmail, 
    CpuLoadCheck, 
    CpuLoadCheckEmail, 
    CpuHistory, 
    MemCheck, 
    MemoryHistory, 
    MemCheckEmail,
    WinServiceCheck,
    WinServiceCheckEmail
)

@app.task
def handle_check_email_alert_task(check_type, pk):
    if check_type == "ping":
        check = PingCheck.objects.get(pk=pk)
        eml = PingCheckEmail
    elif check_type == "diskspace":
        check = DiskCheck.objects.get(pk=pk)
        eml = DiskCheckEmail
    elif check_type == "cpuload":
        check = CpuLoadCheck.objects.get(pk=pk)
        eml = CpuLoadCheckEmail
    elif check_type == "memory":
        check = MemCheck.objects.get(pk=pk)
        eml = MemCheckEmail
    elif check_type == "winsvc":
        check = WinServiceCheck.objects.get(pk=pk)
        eml = WinServiceCheckEmail
    else:
        return {"error": "no check"}

    try:
        latest_email = (
            eml.objects.filter(email=check).order_by("-sent")[:1].get()
        )
    except Exception as e:
        # first time sending email
        eml(email=check).save()
        check.send_email()
    else:
        last_sent = latest_email.sent
        delta = datetime.datetime.now(
            timezone.utc
        ) - datetime.timedelta(hours=24)
        # send an email only if the last email sent is older than 24 hours
        if last_sent < delta:
            eml(email=check).save()
            check.send_email()
    
    return "ok"

@app.task
def determine_agent_status():
    agents = Agent.objects.all()
    offline = datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=4)
    
    for agent in agents:
        overdue = datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=agent.overdue_time)
        if (agent.last_seen < offline) and (agent.last_seen > overdue):
            agent.status = "offline"
        elif (agent.last_seen < offline) and (agent.last_seen < overdue):
            agent.status = "overdue"
        else:
            agent.status = "online"
        agent.save(update_fields=["status"])
    
    return "ok"

@app.task
def disk_check_alert():
    agents_with_checks = DiskCheck.objects.all()
    if agents_with_checks:
        for diskcheck in agents_with_checks:
            agent = Agent.objects.get(pk=diskcheck.agent.pk)
            total = agent.disks[diskcheck.disk]["total"]
            free = agent.disks[diskcheck.disk]["free"]
            diskcheck.more_info = f"Total: {total}B, Free: {free}B"
            diskcheck.save(update_fields=["more_info"])
            percent_used = agent.disks[diskcheck.disk]["percent"]
            percent_free = 100 - percent_used
            if percent_free < diskcheck.threshold:
                diskcheck.status = "failing"
                diskcheck.save(update_fields=["status", "last_run"])
                if diskcheck.email_alert:
                    handle_check_email_alert_task.delay("diskspace", diskcheck.pk)
            else:
                if diskcheck.status != "passing":
                    diskcheck.status = "passing"
                    diskcheck.save(update_fields=["status"])

                diskcheck.save(update_fields=["last_run"])
    return "ok"


@app.task
def cpu_load_check_alert():
    agents_with_checks = CpuLoadCheck.objects.all()
    if agents_with_checks:
        for check in agents_with_checks:
            threshold = check.cpuload
            agent = Agent.objects.get(pk=check.agent.pk)
            try:
                cpuhistory = CpuHistory.objects.get(agent=agent)
            except ObjectDoesNotExist:
                pass
            else:
                check.more_info = cpuhistory.format_nice()
                check.save(update_fields=["more_info", "last_run"])
                avg = int(mean(cpuhistory.cpu_history))
                if avg > threshold:
                    check.status = "failing"
                    check.save(update_fields=["status"])

                    if check.email_alert:
                        handle_check_email_alert_task.delay("cpuload", check.pk)

                else:
                    if check.status != "passing":
                        check.status = "passing"
                        check.save(update_fields=["status"])
                    check.save(update_fields=["last_run"])
    
    return "ok"

@app.task
def restart_win_service_task(pk, svcname):
    agent = Agent.objects.get(pk=pk)
    resp = agent.salt_api_cmd(
        hostname = agent.hostname,
        timeout = 60,
        func = f"service.restart",
        arg = svcname,
    )
    data = resp.json()
    if not data["return"][0][agent.hostname]:
        return {"error": f"restart service {svcname} failed on {agent.hostname}"}
    return "ok"

@app.task
def win_service_check_task():
    agents_with_checks = WinServiceCheck.objects.all()
    if agents_with_checks:
        for check in agents_with_checks:
            alert = False
            agent = Agent.objects.get(pk=check.agent.pk)
            status = list(filter(lambda x: x["name"] == check.svc_name, agent.services))[0]["status"]
            if status == "running":
                check.status = "passing"
                if check.failure_count != 0:
                    check.failure_count = 0
                    check.save(update_fields=["failure_count"])
            elif status == "start_pending":
                if check.pass_if_start_pending:
                    check.status = "passing"
                    if check.failure_count != 0:
                        check.failure_count = 0
                        check.save(update_fields=["failure_count"])
                else:
                    check.status = "failing"
                    new_count = check.failure_count + 1
                    check.failure_count = new_count
                    if new_count >= check.failures:
                        alert = True
                    check.save(update_fields=["failure_count"])

            else:
                check.status = "failing"
                new_count = check.failure_count + 1
                check.failure_count = new_count
                if new_count >= check.failures:
                    alert = True
                check.save(update_fields=["failure_count"])
            
            if check.restart_if_stopped:
                if status == "stopped":
                    restart_win_service_task.delay(agent.pk, check.svc_name)

            check.more_info = f"Status {status.upper()}"
            check.save(update_fields=["status", "more_info", "last_run"])

            if alert:
                if check.email_alert:
                    handle_check_email_alert_task.delay("winsvc", check.pk)

    return "ok"




@app.task
def mem_check_alert():
    agents_with_checks = MemCheck.objects.all()
    if agents_with_checks:
        for check in agents_with_checks:
            threshold = check.threshold
            agent = Agent.objects.get(pk=check.agent.pk)
            try:
                memhistory = MemoryHistory.objects.get(agent=agent)
            except ObjectDoesNotExist:
                pass
            else:
                check.more_info = memhistory.format_nice()
                check.save(update_fields=["more_info", "last_run"])
                avg = int(mean(memhistory.mem_history))
                if avg > threshold:
                    check.status = "failing"
                    check.save(update_fields=["status"])

                    if check.email_alert:
                        handle_check_email_alert_task.delay("memory", check.pk)

                else:
                    if check.status != "passing":
                        check.status = "passing"
                        check.save(update_fields=["status"])
                    check.save(update_fields=["last_run"])
    
    return "ok"