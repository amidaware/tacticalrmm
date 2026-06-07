import logging
import os

_gateway_debug = os.environ.get("TRMM_GATEWAY_DEBUG", "").lower() in ("1", "true", "yes")
_log = logging.getLogger("trmm")


class _GatewayLog:
    def debug(self, msg, *args, **kwargs):
        if _gateway_debug:
            _log.error(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if _gateway_debug:
            _log.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if _gateway_debug:
            _log.error(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if _gateway_debug:
            _log.error(msg, *args, **kwargs)


gw_log = _GatewayLog()
