import asyncio
import contextlib
import uuid
import logging
from agents.utils import (
    is_windows_path,
    is_posix_abs_path,
)
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from packaging import version as pyver

from agents.models import Agent, AgentHistory, AgentPlat
from logs.models import AuditLog
from tacticalrmm.constants import (
    AgentHistoryType,
    AuditActionType,
    AuditObjType,
    WINDOWS_TOKENS,
    LINUX_TOKENS,
    DARWIN_TOKENS,
)
from tacticalrmm.permissions import _has_perm_on_agent
from tacticalrmm.helpers import setup_nats_options
import nats
import msgpack
import os

# Shared across all CommandStreamConsumer instances
active_streams = {}
logger = logging.getLogger("trmm")


class CommandStreamConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_task = None
        self.stop_evt = None
        self.agent_id = None
        self.group_name = None
        self.cmd_id = None
        self.authorized = False

    async def connect(self):
        """Handle websocket connection."""
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        if not self.user.is_authenticated:
            await self.close(4401)
            return

        if self.user.block_dashboard_login:
            await self.close()
            return

        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        has_permission = await self.has_perm(self.agent_id)
        if not has_permission:
            await self.accept()
            await self.send_json(
                {
                    "error": "You do not have permission to perform this action.",
                    "status": 403,
                }
            )
            await self.close(code=4003)
            return

        agent = await self.get_agent(self.agent_id)
        if pyver.parse(agent.version) < pyver.parse("2.10.0"):
            await self.accept()
            await self.send_json(
                {
                    "error": "The streaming feature requires agent version 2.10.0 or higher.",
                    "status": 400,
                }
            )
            await self.close()
            return

        # Don’t create a group yet, cmd_id not known
        await self.accept()
        self.authorized = True

    async def disconnect(self, close_code):
        """Cleanup on disconnect."""
        chan = self.channel_name

        if chan in active_streams:
            cmd_streams = active_streams[chan]
            if self.cmd_id in cmd_streams:
                stop_evt, stream_task = cmd_streams.pop(self.cmd_id, (None, None))
                if stop_evt:
                    stop_evt.set()
                if stream_task and not stream_task.done():
                    with contextlib.suppress(asyncio.CancelledError):
                        await stream_task
            if not cmd_streams:
                active_streams.pop(chan)

        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not getattr(self, "authorized", False):
            await self.close(4403)
            return

        agent = await self.get_agent(self.agent_id)
        try:
            cmd = content["cmd"]
            shell = content.get("shell") or "cmd"
            custom_shell = content.get("custom_shell")
            run_as_user = bool(content.get("run_as_user", False))
            timeout = int(content.get("timeout", 30))
        except (KeyError, ValueError, TypeError):
            await self.send_json({"error": "Invalid command payload"})
            return

        shell = custom_shell if shell == "custom" and custom_shell else shell
        cmd_id = content.get("cmd_id") or uuid.uuid4().hex
        self.cmd_id = cmd_id

        # Create per-session group now that cmd_id is known
        self.group_name = f"agent_cmd_{self.agent_id}_{cmd_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.send_json({"cmd_id": cmd_id})
        subject_output = f"{self.agent_id}.cmdoutput.{cmd_id}"

        hist = await AgentHistory.objects.acreate(
            agent=agent,
            type=AgentHistoryType.CMD_RUN,
            command=cmd,
            username=self.user.username[:50],
        )

        await AuditLog.objects.acreate(
            username=self.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{self.user.username} issued {shell} command on {agent.hostname}.",
            after_value=cmd,
            debug_info={
                "ip": self.scope.get("client")[0] if self.scope.get("client") else ""
            },
        )

        chan = self.channel_name
        if chan not in active_streams:
            active_streams[chan] = {}

        data = {
            "func": "rawcmd",
            "timeout": timeout,
            "stream": True,
            "payload": {"command": cmd, "shell": shell, "cmd_id": cmd_id},
            "run_as_user": run_as_user,
            "id": hist.pk,
        }

        self.stop_evt = asyncio.Event()
        self.stream_task = asyncio.create_task(
            agent.nats_stream_cmd(
                data,
                timeout=timeout + 2,
                stop_evt=self.stop_evt,
                output_subject=subject_output,
                group=self.group_name,
            )
        )
        active_streams[chan][cmd_id] = (self.stop_evt, self.stream_task)

    async def stream_output(self, event):
        await self.send_json(
            {
                k: v
                for k, v in event.items()
                if k in ("output", "done", "exit_code", "cmd_id")
            }
        )

    async def has_perm(self, agent_id: str) -> bool:
        return await database_sync_to_async(self._has_perm_on_agent)(agent_id)

    async def get_agent(self, agent_id: str):
        return await Agent.objects.aget(agent_id=agent_id)

    def _has_perm(self, perm: str) -> bool:
        if self.user.is_superuser or (
            self.user.role and getattr(self.user.role, "is_superuser")
        ):
            return True
        elif not self.user.role:
            return False
        return getattr(self.user.role, perm, False)

    def _has_perm_on_agent(self, agent_id: str) -> bool:
        return self._has_perm("can_send_cmd") and _has_perm_on_agent(
            self.user, agent_id
        )


class InvalidTerminalShellError(Exception):
    pass


class TerminalStreamConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_id = None
        self.session_id = None
        self.group_name = None
        self.killed = False
        self.started = False
        self.message_id = 0

        # NATS (reused per WS session)
        self.nc = None
        self.sub = None
        self.nats_lock = asyncio.Lock()

    async def connect(self):
        self.user = self.scope["user"]
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]

        if not await self.has_perm(self.agent_id):
            await self.accept()
            await self.send_json({"error": "Permission denied", "status": 403})
            await self.close(code=4003)
            return

        self.group_name = f"terminal_{self.agent_id}_{self.session_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        # send kill only if we didn't already send it from explicit "kill" action
        if not self.killed:
            with contextlib.suppress(Exception):
                await self._send_kill()

        # unsubscribe + close nats connection
        with contextlib.suppress(Exception):
            if self.sub is not None:
                await self.sub.unsubscribe()
                self.sub = None

        with contextlib.suppress(Exception):
            if self.nc is not None and not self.nc.is_closed:
                await self.nc.close()
                self.nc = None

    async def receive_json(self, content):
        action = content.get("action")
        # log incoming payload
        print(f"[TerminalStreamConsumer] Received action: {action}, payload: {content}")

        if action == "start":
            await self._start_terminal(content)
        elif action == "input":
            await self._send_input(content.get("data", ""))
        elif action == "resize":
            await self._send_resize(content.get("rows"), content.get("cols"))
        elif action == "kill":
            self.killed = True
            with contextlib.suppress(Exception):
                await self._send_kill()
        else:
            await self.send_json({"error": f"Unknown action: {action}"})

    async def stream_output(self, event):
        await self.send_json(
            {
                "action": "trmmcli.output",
                "data": {
                    "output": event.get("output", ""),
                    "session_id": event.get("session_id", ""),
                    "exit_code": event.get("exit_code", None),
                    "done": event.get("done", False),
                    "messageId": event.get("messageId", ""),
                },
            }
        )

    async def _ensure_nats(self):
        if self.nc is not None and not self.nc.is_closed:
            return
        opts = setup_nats_options()
        self.nc = await nats.connect(**opts)

    async def _nats_publish(self, payload: dict):
        # serialize writes on this connection
        async with self.nats_lock:
            try:
                await self._ensure_nats()
                await self.nc.publish(self.agent_id, msgpack.dumps(payload))
            except Exception as e:
                logger.exception("Terminal NATS publish failed: %s", e)
                # reset so next call reconnects
                with contextlib.suppress(Exception):
                    if self.nc and not self.nc.is_closed:
                        await self.nc.close()
                self.nc = None
                raise

    async def _start_terminal(self, content):
        if self.started:
            return

        agent = await Agent.objects.aget(agent_id=self.agent_id)

        requested_shell_raw = (content.get("shell") or "").strip()
        effective_raw = (agent.effective_default_shell or "").strip()

        try:
            if requested_shell_raw:
                shell = self._resolve_explicit_shell(requested_shell_raw, agent.plat)
                shell_source = "frontend"
            else:
                shell = self._resolve_default_shell(effective_raw, agent.plat)
                shell_source = "default"

            logger.info(
                "Starting terminal for agent=%s session=%s shell=%s source=%s",
                self.agent_id,
                self.session_id,
                shell,
                shell_source,
            )

            subject_output = f"{self.agent_id}.terminal.{self.session_id}"
            await self._ensure_nats()

            async def message_handler(msg):
                try:
                    try:
                        obj = msgpack.loads(msg.data)
                    except Exception:
                        obj = msg.data

                    payload: dict[str, object] = {"session_id": self.session_id}

                    if isinstance(obj, dict):
                        out = obj.get("output")
                        if isinstance(out, (bytes, bytearray)):
                            payload["output"] = out.decode("utf-8", errors="ignore")
                        elif isinstance(out, str):
                            payload["output"] = out

                        if obj.get("done") is True:
                            payload["done"] = True
                            self.started = False
                        if "exit_code" in obj:
                            payload["exit_code"] = obj["exit_code"]

                    elif isinstance(obj, (bytes, bytearray)):
                        payload["output"] = obj.decode("utf-8", errors="ignore")
                    elif isinstance(obj, str):
                        payload["output"] = obj
                    else:
                        payload["output"] = str(obj)

                    self.message_id += 1
                    payload["messageId"] = str(self.message_id)

                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "stream_output", **payload},
                    )

                except Exception as e:
                    logger.exception(
                        "Error handling terminal NATS message for agent %s",
                        self.agent_id,
                    )
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "stream_output",
                            "session_id": self.session_id,
                            "output": f"[ERROR] Failed to process agent output: {e}",
                        },
                    )

            # subscribe first so we don't miss the initial prompt
            self.sub = await self.nc.subscribe(subject_output, cb=message_handler)

            await self._nats_publish(
                {
                    "func": "terminal_start",
                    "payload": {
                        "session_id": self.session_id,
                        "shell": shell,
                    },
                }
            )

            self.started = True

        except InvalidTerminalShellError as e:
            logger.warning(
                "Rejected terminal start for agent=%s session=%s shell=%r: %s",
                self.agent_id,
                self.session_id,
                requested_shell_raw,
                e,
            )
            self.started = False
            await self._send_terminal_error(str(e), code="invalid_shell")
            return

        except Exception as e:
            logger.exception(
                "Failed to start terminal for agent=%s session=%s: %s",
                self.agent_id,
                self.session_id,
                e,
            )
            self.started = False
            await self._send_terminal_error(
                "Failed to start terminal session.",
                code="terminal_start_failed",
            )
            return

    async def _send_input(self, value):
        if not self.started:
            return
        if not value:
            return

        await self._nats_publish(
            {
                "func": "terminal_input",
                "payload": {"session_id": self.session_id, "data": value},
            }
        )

    async def _send_resize(self, rows, cols):
        if not self.started:
            return

        if not rows or not cols:
            return

        await self._nats_publish(
            {
                "func": "terminal_resize",
                "payload": {
                    "session_id": self.session_id,
                    "rows": str(rows),
                    "cols": str(cols),
                },
            }
        )

    async def _send_kill(self):
        await self._nats_publish(
            {
                "func": "terminal_kill",
                "payload": {"session_id": self.session_id},
            }
        )

    def _resolve_explicit_shell(self, shell: str, plat: str) -> str:
        shell = (shell or "").strip()
        shell_lc = shell.lower()

        if plat == AgentPlat.WINDOWS:
            if shell_lc in WINDOWS_TOKENS:
                return shell_lc

            if is_windows_path(shell):
                if os.path.isfile(shell):
                    return shell

                raise InvalidTerminalShellError(
                    "Invalid shell. The specified Windows executable path does not exist."
                )

            raise InvalidTerminalShellError(
                "Invalid shell. Use 'cmd', 'powershell', or an absolute Windows .exe path."
            )

        if plat == AgentPlat.LINUX:
            if shell_lc in LINUX_TOKENS:
                return shell_lc

            if is_posix_abs_path(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell

                raise InvalidTerminalShellError(
                    "Invalid shell. The specified path does not exist or is not executable."
                )

            raise InvalidTerminalShellError(
                "Invalid shell. Use a supported shell (e.g. bash) or an absolute executable path."
            )

        if plat == AgentPlat.DARWIN:
            if shell_lc in DARWIN_TOKENS:
                return shell_lc

            if is_posix_abs_path(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell

                raise InvalidTerminalShellError(
                    "Invalid shell. The specified path does not exist or is not executable."
                )

            raise InvalidTerminalShellError(
                "Invalid shell. Use a supported shell (e.g. zsh, bash) or an absolute executable path."
            )

        raise InvalidTerminalShellError("Unsupported agent platform.")

    def _resolve_default_shell(self, shell: str, plat: str) -> str:
        shell = (shell or "").strip()
        shell_lc = shell.lower()

        if plat == AgentPlat.WINDOWS:
            if shell_lc in WINDOWS_TOKENS:
                return shell_lc
            if is_windows_path(shell):
                return shell
            return "cmd"

        if plat == AgentPlat.LINUX:
            if shell_lc in LINUX_TOKENS:
                return shell_lc
            if is_posix_abs_path(shell):
                return shell
            return "bash"

        if plat == AgentPlat.DARWIN:
            if shell_lc in DARWIN_TOKENS:
                return shell_lc
            if is_posix_abs_path(shell):
                return shell
            return "bash"

        return "cmd"

    async def _send_terminal_error(self, message: str, code: str = "invalid_shell"):
        await self.send_json(
            {
                "action": "terminal_error",
                "error": message,
                "code": code,
            }
        )

    async def has_perm(self, agent_id: str) -> bool:
        return await database_sync_to_async(self._has_perm_on_agent)(agent_id)

    async def get_agent(self, agent_id: str):
        return await Agent.objects.aget(agent_id=agent_id)

    def _has_perm_on_agent(self, agent_id: str) -> bool:
        return self._has_perm("can_use_terminal") and _has_perm_on_agent(
            self.user, agent_id
        )

    def _has_perm(self, perm: str) -> bool:
        if self.user.is_superuser or (
            self.user.role and getattr(self.user.role, "is_superuser")
        ):
            return True
        elif not self.user.role:
            return False
        return getattr(self.user.role, perm, False)
