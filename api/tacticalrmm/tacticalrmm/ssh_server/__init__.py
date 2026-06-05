import logging

_log = logging.getLogger("trmm")
if not _log.handlers:
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.DEBUG)
    _sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(_sh)
    _log.setLevel(logging.DEBUG)

from .server import start_ssh_server, _active_connections, get_active_connections  # noqa: E402, F401
