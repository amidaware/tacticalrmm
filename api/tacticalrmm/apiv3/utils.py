import random

from django.conf import settings

from tacticalrmm.structs import AgentCheckInConfig


def get_agent_config() -> AgentCheckInConfig:
    return AgentCheckInConfig(
        checkin_hello=random.randint(*getattr(settings, "CHECKIN_HELLO", (30, 60))),
        checkin_agentinfo=random.randint(
            *getattr(settings, "CHECKIN_AGENTINFO", (200, 400))
        ),
        checkin_winsvc=random.randint(
            *getattr(settings, "CHECKIN_WINSVC", (2400, 3000))
        ),
        checkin_pubip=random.randint(*getattr(settings, "CHECKIN_PUBIP", (300, 500))),
        checkin_disks=random.randint(*getattr(settings, "CHECKIN_DISKS", (1000, 2000))),
        checkin_sw=random.randint(*getattr(settings, "CHECKIN_SW", (2800, 3500))),
        checkin_wmi=random.randint(*getattr(settings, "CHECKIN_WMI", (3000, 4000))),
        checkin_syncmesh=random.randint(
            *getattr(settings, "CHECKIN_SYNCMESH", (800, 1200))
        ),
        limit_data=getattr(settings, "LIMIT_DATA", False),
        install_nushell=getattr(settings, "INSTALL_NUSHELL", False),
        install_nushell_version=getattr(settings, "INSTALL_NUSHELL_VERSION", ""),
        install_nushell_url=getattr(settings, "INSTALL_NUSHELL_URL", ""),
        nushell_enable_config=getattr(settings, "NUSHELL_ENABLE_CONFIG", False),
        install_deno=getattr(settings, "INSTALL_DENO", False),
        install_deno_version=getattr(settings, "INSTALL_DENO_VERSION", ""),
        install_deno_url=getattr(settings, "INSTALL_DENO_URL", ""),
        deno_default_permissions=getattr(settings, "DENO_DEFAULT_PERMISSIONS", ""),
    )
