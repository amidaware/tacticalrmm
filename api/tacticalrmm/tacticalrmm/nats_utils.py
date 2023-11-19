import asyncio
from typing import TYPE_CHECKING, Any

import msgpack
import nats
from nats.errors import TimeoutError as NatsTimeout

from tacticalrmm.exceptions import NatsDown
from tacticalrmm.helpers import setup_nats_options

if TYPE_CHECKING:
    from nats.aio.client import Client as NClient

NATS_DATA = dict[str, Any]

BULK_NATS_TASKS = list[tuple[str, Any]]


async def _anats_message(*, nc: "NClient", subject: str, data: "NATS_DATA") -> None:
    try:
        payload = msgpack.dumps(data)
    except:
        return

    await nc.publish(subject=subject, payload=payload)


async def abulk_nats_command(*, items: "BULK_NATS_TASKS") -> None:
    """Fire and forget"""
    opts = setup_nats_options()
    try:
        nc = await nats.connect(**opts)
    except Exception:
        raise NatsDown

    tasks = [_anats_message(nc=nc, subject=item[0], data=item[1]) for item in items]
    await asyncio.gather(*tasks)
    await nc.flush()
    await nc.close()


async def a_nats_cmd(
    *, nc: "NClient", sub: str, data: NATS_DATA, timeout: int = 10
) -> str | Any:
    try:
        msg = await nc.request(
            subject=sub, payload=msgpack.dumps(data), timeout=timeout
        )
    except NatsTimeout:
        return "timeout"

    try:
        return msgpack.loads(msg.data)
    except Exception as e:
        return str(e)
