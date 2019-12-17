from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tacticalrmm.settings')

app = Celery('tacticalrmm', backend='redis://localhost', broker='redis://localhost')
#app.config_from_object('django.conf:settings', namespace='CELERY')
app.broker_url = 'redis://localhost:6379'
app.result_backend = 'redis://localhost:6379'
app.accept_content = ['application/json']
app.result_serializer = 'json'
app.task_serializer = 'json'
app.conf.task_track_started = True
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    
    from checks.tasks import (
        disk_check_alert, 
        cpu_load_check_alert, 
        mem_check_alert, 
        win_service_check_task,
        determine_agent_status,
        checks_failing_task
    )

    sender.add_periodic_task(10.0, disk_check_alert.s())
    sender.add_periodic_task(10.0, cpu_load_check_alert.s())
    sender.add_periodic_task(10.0, mem_check_alert.s())
    sender.add_periodic_task(10.0, win_service_check_task.s())
    sender.add_periodic_task(60.0, determine_agent_status.s())
    sender.add_periodic_task(7.0, checks_failing_task.s())