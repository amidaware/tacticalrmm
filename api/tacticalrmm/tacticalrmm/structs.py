import dataclasses
from typing import Any


class TRMMStruct:
    def _to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class AgentCheckInConfig(TRMMStruct):
    checkin_hello: int
    checkin_agentinfo: int
    checkin_winsvc: int
    checkin_pubip: int
    checkin_disks: int
    checkin_sw: int
    checkin_wmi: int
    checkin_syncmesh: int
    limit_data: bool
    install_nushell: bool
    install_nushell_version: str
    install_nushell_url: str
    nushell_enable_config: bool
    install_deno: bool
    install_deno_version: str
    install_deno_url: str
    deno_default_permissions: str
