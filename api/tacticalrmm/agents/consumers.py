import asyncio
import contextlib
import json
import logging
import uuid

import msgpack
import nats
import validators
from agents.models import Agent, AgentHistory, AgentPlat
from agents.utils import is_posix_abs_path, is_windows_path
from channels.db import database_sync_to_async
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
    AsyncWebsocketConsumer,
)
from django.contrib.auth.models import AnonymousUser
from logs.models import AuditLog
from packaging import version as pyver
from tacticalrmm.constants import (
    DARWIN_TOKENS,
    LINUX_TOKENS,
    WINDOWS_TOKENS,
    AgentHistoryType,
    AuditActionType,
    AuditObjType,
)
from tacticalrmm.helpers import setup_nats_options
from tacticalrmm.permissions import _has_perm_on_agent

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
        self._start_lock = asyncio.Lock()
        self.nc = None
        self.sub = None
        self.nats_lock = asyncio.Lock()

    async def connect(self):
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
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]

        if not validators.uuid(self.session_id):
            await self.close()
            return

        if not await self.has_perm(self.agent_id):
            await self.close(code=4003)
            return

        self.group_name = f"terminal_{self.agent_id}_{self.session_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if not self.killed:
            with contextlib.suppress(Exception):
                await self._send_kill()

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
        logger.debug(
            "[TerminalStreamConsumer] Received action=%s payload=%s",
            action,
            content,
        )

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
        async with self.nats_lock:
            try:
                await self._ensure_nats()
                await self.nc.publish(self.agent_id, msgpack.dumps(payload))
            except Exception as e:
                logger.exception("Terminal NATS publish failed: %s", e)
                with contextlib.suppress(Exception):
                    if self.nc and not self.nc.is_closed:
                        await self.nc.close()
                self.nc = None
                raise

    async def _start_terminal(self, content):
        async with self._start_lock:
            if self.started:
                return
            self.started = True

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
                    decoded_output = None
                    exit_code = None
                    done = False

                    if isinstance(obj, dict):
                        out = obj.get("output")
                        if isinstance(out, (bytes, bytearray)):
                            decoded_output = out.decode("utf-8", errors="ignore")
                            payload["output"] = decoded_output
                        elif isinstance(out, str):
                            decoded_output = out
                            payload["output"] = decoded_output

                        done = obj.get("done") is True
                        if done:
                            payload["done"] = True
                            self.started = False

                        if "exit_code" in obj:
                            exit_code = obj["exit_code"]
                            payload["exit_code"] = exit_code

                        if (
                            done
                            and exit_code == 1
                            and isinstance(decoded_output, str)
                            and decoded_output.startswith("[ERROR] ")
                        ):
                            await self._send_terminal_error(
                                decoded_output.removeprefix("[ERROR] ").strip(),
                                code="terminal_start_failed",
                            )
                            return

                        if isinstance(
                            decoded_output, str
                        ) and decoded_output.startswith("[INFO] "):
                            await self._send_terminal_info(
                                decoded_output.removeprefix("[INFO] ").strip(),
                                code="terminal_fallback",
                            )
                            return
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

            self.sub = await self.nc.subscribe(subject_output, cb=message_handler)

            run_as_user = bool(content.get("run_as_user", False))
            if agent.plat != AgentPlat.WINDOWS:
                run_as_user = False

            await self._nats_publish(
                {
                    "func": "terminal_start",
                    "payload": {
                        "session_id": self.session_id,
                        "shell": shell,
                    },
                    "run_as_user": run_as_user,
                }
            )

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
                return shell
            raise InvalidTerminalShellError(
                "Invalid shell. Use 'cmd', 'powershell', or an absolute Windows .exe path."
            )

        if plat == AgentPlat.LINUX:
            if shell_lc in LINUX_TOKENS:
                return shell_lc
            if is_posix_abs_path(shell):
                return shell
            raise InvalidTerminalShellError(
                "Invalid shell. Use a supported shell (e.g. bash) or an absolute POSIX path."
            )

        if plat == AgentPlat.DARWIN:
            if shell_lc in DARWIN_TOKENS:
                return shell_lc
            if is_posix_abs_path(shell):
                return shell
            raise InvalidTerminalShellError(
                "Invalid shell. Use a supported shell (e.g. zsh, bash) or an absolute POSIX path."
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

    async def _send_terminal_info(self, message: str, code: str = "terminal_info"):
        await self.send_json(
            {
                "action": "terminal_info",
                "message": message,
                "code": code,
            }
        )

    async def has_perm(self, agent_id: str) -> bool:
        return await database_sync_to_async(self._has_perm_on_agent)(agent_id)

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


class AgentTerminalConsumer(AsyncWebsocketConsumer):
    """SSH / Telnet terminal to a device on the agent's LAN, tunneled through
    the MeshCentral relay. Output is sent to the browser as binary frames for
    xterm.js; the client sends JSON control messages for input/resize."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.agent_id = None
        self.started = False
        self.protocol = None
        self.tunnel = None
        self.telnet = None
        self.ssh_conn = None
        self.ssh_proc = None
        self.bridge_task = None
        self.reader_task = None
        self.sock_a = None
        self.sock_b = None

    async def connect(self):
        self.user = self.scope.get("user")
        if isinstance(self.user, AnonymousUser) or not getattr(
            self.user, "is_authenticated", False
        ):
            await self.close(4401)
            return
        if self.user.block_dashboard_login:
            await self.close(4401)
            return

        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        if not await self.has_perm(self.agent_id):
            await self.accept()
            await self.send(text_data=json.dumps({"action": "error", "data": "Permission denied"}))
            await self.close(4003)
            return
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        try:
            msg = json.loads(text_data)
        except Exception:
            return
        action = msg.get("action")

        if action == "start" and not self.started:
            self.started = True
            await self.start_session(msg.get("data", {}))
        elif action == "input":
            await self.handle_input(msg.get("data", {}).get("input", ""))
        elif action == "resize":
            await self.handle_resize(msg.get("data", {}))
        elif action == "disconnect":
            await self.close()

    async def start_session(self, data):
        from agents.term_proxy import (
            TelnetFilter,
            bridge_socket_to_tunnel,
            tcp_socketpair,
        )
        from agents.web_proxy import TunnelStream
        from core.utils import get_core_settings
        from meshctrl.utils import get_auth_token

        protocol = str(data.get("protocol", "ssh")).lower()
        address = str(data.get("address", "")).strip()
        try:
            port = int(data.get("port"))
            assert 0 < port < 65536
        except Exception:
            await self.term_error("Invalid port")
            return
        if not address:
            await self.term_error("Address is required")
            return

        self.protocol = protocol
        agent = await self.get_agent(self.agent_id)
        hex_node = await database_sync_to_async(lambda a: a.hex_mesh_node_id)(agent)
        if hex_node == "error":
            await self.term_error("Missing mesh node id")
            return

        core = await database_sync_to_async(get_core_settings)()
        auth_token = get_auth_token(core.mesh_api_superuser, core.mesh_token)

        await self.audit_session(agent, protocol, address, port)

        from agents.web_proxy import TunnelError

        try:
            self.tunnel = await TunnelStream.open(
                hex_node_id=hex_node, addr=address, port=port,
                use_tls=False, auth_token=auth_token,
            )
        except TunnelError as e:
            await self.term_error(str(e))
            return
        except Exception as e:
            await self.term_error(f"Could not reach {address}:{port} via agent ({e})")
            return

        if protocol == "telnet":
            self.telnet = TelnetFilter()
            self.reader_task = asyncio.create_task(self.telnet_reader())
            await self.send(text_data=json.dumps({"action": "connected"}))
        elif protocol == "ssh":
            await self.start_ssh(data)
        else:
            await self.term_error("protocol must be ssh or telnet")

    async def start_ssh(self, data):
        import asyncssh
        from agents.term_proxy import bridge_socket_to_tunnel, tcp_socketpair

        username = str(data.get("username", "") or "")
        password = data.get("password", "") or ""
        cols = int(data.get("cols", 80) or 80)
        rows = int(data.get("rows", 24) or 24)

        loop = asyncio.get_running_loop()
        self.sock_a, self.sock_b = tcp_socketpair()
        self.bridge_task = await bridge_socket_to_tunnel(self.tunnel, self.sock_b, loop)

        try:
            self.ssh_conn = await asyncssh.connect(
                sock=self.sock_a,
                username=username,
                password=password,
                known_hosts=None,
                login_timeout=25,
                keepalive_interval=30,
            )
        except asyncssh.PermissionDenied:
            await self.term_error("SSH authentication failed")
            return
        except Exception as e:
            await self.term_error(f"SSH connection failed: {e}")
            return

        try:
            self.ssh_proc = await self.ssh_conn.create_process(
                term_type="xterm-256color", term_size=(cols, rows),
                encoding=None, stderr=asyncssh.STDOUT,
            )
        except Exception as e:
            await self.term_error(f"Could not open shell: {e}")
            return

        self.reader_task = asyncio.create_task(self.ssh_reader())
        await self.send(text_data=json.dumps({"action": "connected"}))

    async def telnet_reader(self):
        try:
            while True:
                data = await self.tunnel.read()
                if data == b"":
                    break
                clean, reply = self.telnet.feed(data)
                if reply:
                    await self.tunnel.write(reply)
                if clean:
                    await self.send(bytes_data=clean)
        except Exception:
            pass
        finally:
            await self.send_closed()

    async def ssh_reader(self):
        try:
            while True:
                data = await self.ssh_proc.stdout.read(65536)
                if not data:
                    break
                await self.send(bytes_data=data)
        except Exception:
            pass
        finally:
            await self.send_closed()

    async def handle_input(self, data):
        if not data:
            return
        raw = data.encode("utf-8", "replace") if isinstance(data, str) else data
        try:
            if self.protocol == "telnet" and self.tunnel:
                # escape IAC in user data
                await self.tunnel.write(raw.replace(b"\xff", b"\xff\xff"))
            elif self.protocol == "ssh" and self.ssh_proc:
                self.ssh_proc.stdin.write(raw)
        except Exception:
            pass

    async def handle_resize(self, data):
        try:
            cols = int(data.get("cols", 80))
            rows = int(data.get("rows", 24))
            if self.protocol == "ssh" and self.ssh_proc:
                self.ssh_proc.change_terminal_size(cols, rows)
        except Exception:
            pass

    async def term_error(self, message):
        with contextlib.suppress(Exception):
            await self.send(text_data=json.dumps({"action": "error", "data": message}))
            await self.close(4000)

    async def send_closed(self):
        with contextlib.suppress(Exception):
            await self.send(text_data=json.dumps({"action": "closed"}))
            await self.close()

    async def disconnect(self, close_code):
        with contextlib.suppress(Exception):
            if self.reader_task:
                self.reader_task.cancel()
            if self.bridge_task:
                self.bridge_task.cancel()
            if self.ssh_proc:
                self.ssh_proc.close()
            if self.ssh_conn:
                self.ssh_conn.close()
            if self.tunnel:
                await self.tunnel.close()
            for s in (self.sock_a, self.sock_b):
                if s:
                    with contextlib.suppress(Exception):
                        s.close()

    @database_sync_to_async
    def audit_session(self, agent, protocol, address, port):
        AuditLog.audit_mesh_session(
            username=self.user.username,
            agent=agent,
            debug_info={
                "feature": "remote_terminal",
                "target": f"{protocol}://{address}:{port}",
            },
        )

    async def has_perm(self, agent_id):
        return await database_sync_to_async(self._has_perm_on_agent)(agent_id)

    async def get_agent(self, agent_id):
        return await Agent.objects.aget(agent_id=agent_id)

    def _has_perm(self, perm):
        if self.user.is_superuser or (
            self.user.role and getattr(self.user.role, "is_superuser")
        ):
            return True
        elif not self.user.role:
            return False
        return getattr(self.user.role, perm, False)

    def _has_perm_on_agent(self, agent_id):
        return self._has_perm("can_use_mesh") and _has_perm_on_agent(
            self.user, agent_id
        )
