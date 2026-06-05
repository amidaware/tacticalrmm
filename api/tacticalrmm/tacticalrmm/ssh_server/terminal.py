import asyncio
import logging

import msgpack
import nats

from tacticalrmm.helpers import setup_nats_options

logger = logging.getLogger("trmm")


class NATSTerminal:
    def __init__(self, agent, session_id, shell):
        self.agent = agent
        self.session_id = session_id
        self.shell = shell
        self.nc = None
        self.sub = None
        self._lock = asyncio.Lock()

    async def start(self, output_cb):
        opts = setup_nats_options()
        self.nc = await nats.connect(**opts)
        subj_out = f"{self.agent.agent_id}.terminal.{self.session_id}"

        async def handler(msg):
            try:
                obj = msgpack.loads(msg.data)
            except Exception:
                obj = msg.data
            if isinstance(obj, dict):
                out = obj.get("output", b"")
                done = obj.get("done", False)
                ec = obj.get("exit_code")
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")
                await output_cb(out, done=done, exit_code=ec)
                if done:
                    asyncio.ensure_future(self.stop())
            elif isinstance(obj, (bytes, bytearray)):
                await output_cb(obj.decode("utf-8", errors="replace"))
            elif isinstance(obj, str):
                await output_cb(obj)

        self.sub = await self.nc.subscribe(subj_out, cb=handler)
        await self._pub({"func": "terminal_start", "payload": {"session_id": self.session_id, "shell": self.shell}})

    async def _pub(self, p):
        async with self._lock:
            await self.nc.publish(self.agent.agent_id, msgpack.dumps(p))

    async def write(self, data):
        await self._pub({"func": "terminal_input", "payload": {"session_id": self.session_id, "data": data}})

    async def resize(self, rows, cols):
        await self._pub({"func": "terminal_resize", "payload": {"session_id": self.session_id, "rows": str(rows), "cols": str(cols)}})

    async def stop(self):
        try:
            await self._pub({"func": "terminal_kill", "payload": {"session_id": self.session_id}})
        except Exception as e:
            logger.debug("NATSTerminal stop: failed to send kill: %s", e)
        if self.sub:
            try:
                await self.sub.unsubscribe()
            except Exception as e:
                logger.debug("NATSTerminal stop: failed to unsubscribe: %s", e)
            self.sub = None
        if self.nc and not self.nc.is_closed:
            try:
                await self.nc.close()
            except Exception as e:
                logger.debug("NATSTerminal stop: failed to close NATS connection: %s", e)
            self.nc = None
