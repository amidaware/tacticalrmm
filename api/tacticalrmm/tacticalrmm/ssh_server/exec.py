import asyncio
import logging

import msgpack
import nats

from tacticalrmm.helpers import setup_nats_options

logger = logging.getLogger("trmm")


class SSHExec:
    def __init__(self, agent, session_id, command, shell="/bin/bash"):
        self.agent = agent
        self.session_id = session_id
        self.command = command
        self.shell = shell
        self.nc = None
        self.sub = None
        self._lock = asyncio.Lock()
        self._output_cb = None

    async def start(self, output_cb):
        self._output_cb = output_cb
        opts = setup_nats_options()
        self.nc = await nats.connect(**opts)
        subj_out = f"{self.agent.agent_id}.exec.{self.session_id}"

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
                elif not isinstance(out, str):
                    out = str(out)

                await output_cb(out, done=done, exit_code=ec)

                if done:
                    await self.stop()
            elif isinstance(obj, (bytes, bytearray)):
                await output_cb(obj.decode("utf-8", errors="replace"), done=False)
            elif isinstance(obj, str):
                await output_cb(obj, done=False)

        self.sub = await self.nc.subscribe(subj_out, cb=handler)

        cmd_id = f"ssh_{self.session_id}"
        await self._pub({
            "func": "rawcmd",
            "timeout": 60,
            "stream": True,
            "payload": {
                "command": self.command,
                "shell": self.shell,
                "cmd_id": cmd_id,
            },
            "id": cmd_id,
        })

    async def _pub(self, p):
        async with self._lock:
            await self.nc.publish(self.agent.agent_id, msgpack.dumps(p))

    async def stop(self):
        if self.sub:
            try:
                await self.sub.unsubscribe()
            except Exception as e:
                logger.debug("SSHExec stop: failed to unsubscribe: %s", e)
            self.sub = None
        if self.nc and not self.nc.is_closed:
            try:
                await self.nc.close()
            except Exception as e:
                logger.debug("SSHExec stop: failed to close NATS connection: %s", e)
            self.nc = None