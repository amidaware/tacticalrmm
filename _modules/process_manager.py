from __future__ import absolute_import
import psutil
from time import sleep
import random
import string

def get_procs():
    ret = []

    # setup
    for proc in psutil.process_iter():
        with proc.oneshot():
            proc.cpu_percent(interval=None)

    # need time for psutil to record cpu percent
    sleep(1)

    for proc in psutil.process_iter():
        x = {}
        with proc.oneshot():
            x['name'] = proc.name()
            x['cpu_percent'] = proc.cpu_percent(interval=None) / psutil.cpu_count()
            x['memory_percent'] = proc.memory_percent()
            x['pid'] = proc.pid
            x['ppid'] = proc.ppid()
            x['status'] = proc.status()
            x['username'] = proc.username()
            x['id'] = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(10)])
        
        if proc.pid != 0:
            ret.append(x)
    
    return ret