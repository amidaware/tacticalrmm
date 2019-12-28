from __future__ import absolute_import
import psutil


def fixmesh():
    mesh = [
        p.info
        for p in psutil.process_iter(attrs=["pid", "name"])
        if "meshagent" in p.info["name"].lower()
    ]
    if mesh:
        try:
            mesh_pid = mesh[0]["pid"]
            x = psutil.Process(mesh_pid)
        except Exception as e:
            pass
        else:
            return x.cpu_percent(5)
