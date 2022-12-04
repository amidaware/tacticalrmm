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
