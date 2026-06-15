import asyncio

import msgpack
import nats

from .logger import gw_log
from tacticalrmm.helpers import setup_nats_options


class CmdProxy:
    def __init__(self, agent, session_id, command, shell="/bin/bash"):
        self.agent = agent
        self.session_id = session_id
        self.command = command
        self.shell = shell
        self.nc = None
        self.sub = None
        self._lock = asyncio.Lock()
        self._done = asyncio.Event()
        self._started = False

    async def start(self, output_cb):
        opts = setup_nats_options()
        self.nc = await nats.connect(**opts)
        cmd_id = f"ssh_{self.session_id[:8]}"
        subj_out = f"{self.agent.agent_id}.cmdoutput.{cmd_id}"

        async def handler(msg):
            try:
                obj = msgpack.loads(msg.data)
            except Exception as e:
                gw_log.error(f"CmdProxy: failed to decode msg: {e}")
                obj = msg.data

            if isinstance(obj, dict):
                done = obj.get("done", False)
                ec = obj.get("exit_code")

                if done:
                    await output_cb("", done=True, exit_code=ec)
                    return

                out = obj.get("line") or obj.get("output", b"")

                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")
                elif not isinstance(out, str):
                    out = str(out)

                if out:
                    await output_cb(out, done=done, exit_code=ec)
            elif isinstance(obj, (bytes, bytearray)):
                await output_cb(obj.decode("utf-8", errors="replace"), done=False)
            elif isinstance(obj, str):
                await output_cb(obj, done=False)

        self.sub = await self.nc.subscribe(subj_out, cb=handler)
        self._started = True
        await self._pub({
            "func": "rawcmd",
            "timeout": 60,
            "stream": True,
            "payload": {
                "command": self.command,
                "shell": self.shell,
                "cmd_id": cmd_id,
            },
            "run_as_user": False,
            "id": 0,
        })

    async def _pub(self, p):
        async with self._lock:
            await self.nc.publish(self.agent.agent_id, msgpack.dumps(p))
            await self.nc.flush()

    async def stop(self):
        if self.sub:
            try:
                await self.sub.unsubscribe()
            except Exception as e:
                gw_log.debug("CmdProxy stop: failed to unsubscribe: %s", e)
            self.sub = None
        if self.nc and not self.nc.is_closed:
            try:
                await self.nc.close()
            except Exception as e:
                gw_log.debug("CmdProxy stop: failed to close NATS connection: %s", e)
            self.nc = None


async def run_exec(user, agent, session_id, command, output_cb):
    exec_proxy = CmdProxy(agent, session_id, command)
    await exec_proxy.start(output_cb)
