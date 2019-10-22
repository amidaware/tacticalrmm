from __future__ import absolute_import
import psutil

def get_services():
    try:
        svc = [x.as_dict() for x in psutil.win_service_iter()]
    except Exception:
        svc = {"error": "error getting services"}
    finally:
        return svc
