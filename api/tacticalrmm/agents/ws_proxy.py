"""
WebSocket proxying for the Remote Web Proxy.

Lets WebSocket-based features of a proxied device work through the tunnel -
most importantly the Proxmox / PBS noVNC & xterm.js consoles
(wss://device/api2/json/nodes/.../vncwebsocket?...).

Flow: the browser opens a WebSocket to /agentproxy/<token>/<path> (same origin as
the popup). This consumer opens a raw TCP tunnel to the device through the agent,
performs the WebSocket upgrade handshake with the device over that tunnel, then
relays frames between the browser (decoded by Channels) and the device (raw WS
frames over the tunnel).
"""
import asyncio
import base64
import contextlib
import os
import struct

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from tacticalrmm.logger import logger

OP_CONT = 0x0
OP_TEXT = 0x1
OP_BIN = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA


def encode_frame(opcode: int, payload: bytes, mask: bool = True) -> bytes:
    """Encode a WebSocket frame. Client->server frames must be masked."""
    length = len(payload)
    out = bytearray([0x80 | opcode])  # FIN + opcode
    if length < 126:
        b1 = length
    elif length < 65536:
        b1 = 126
    else:
        b1 = 127
    if mask:
        b1 |= 0x80
    out.append(b1)
    if 126 <= length < 65536:
        out += struct.pack("!H", length)
    elif length >= 65536:
        out += struct.pack("!Q", length)
    if mask:
        m = os.urandom(4)
        out += m
        out += bytes(payload[i] ^ m[i % 4] for i in range(length))
    else:
        out += payload
    return bytes(out)


class FrameDecoder:
    """Incrementally decodes server->client WebSocket frames from a byte stream."""

    def __init__(self):
        self.buf = bytearray()
        self._frag = bytearray()
        self._frag_op = None

    def feed(self, data: bytes):
        self.buf += data
        out = []
        while True:
            parsed = self._parse_one()
            if parsed is None:
                break
            fin, opcode, payload = parsed
            if opcode in (OP_CLOSE, OP_PING, OP_PONG):
                out.append((opcode, payload))
            elif opcode == OP_CONT:
                self._frag += payload
                if fin:
                    out.append((self._frag_op or OP_BIN, bytes(self._frag)))
                    self._frag = bytearray()
                    self._frag_op = None
            else:  # text / binary
                if fin:
                    out.append((opcode, payload))
                else:
                    self._frag_op = opcode
                    self._frag = bytearray(payload)
        return out

    def _parse_one(self):
        b = self.buf
        if len(b) < 2:
            return None
        b0, b1 = b[0], b[1]
        fin = (b0 & 0x80) != 0
        opcode = b0 & 0x0F
        masked = (b1 & 0x80) != 0
        ln = b1 & 0x7F
        idx = 2
        if ln == 126:
            if len(b) < 4:
                return None
            ln = struct.unpack("!H", bytes(b[2:4]))[0]
            idx = 4
        elif ln == 127:
            if len(b) < 10:
                return None
            ln = struct.unpack("!Q", bytes(b[2:10]))[0]
            idx = 10
        mask = None
        if masked:
            if len(b) < idx + 4:
                return None
            mask = bytes(b[idx:idx + 4])
            idx += 4
        if len(b) < idx + ln:
            return None
        payload = bytes(b[idx:idx + ln])
        if masked and mask:
            payload = bytes(payload[i] ^ mask[i % 4] for i in range(ln))
        del b[: idx + ln]
        return fin, opcode, payload


class ProxyWebSocketConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tunnel = None
        self.reader_task = None
        self.decoder = FrameDecoder()

    async def connect(self):
        from agents.web_proxy import TunnelStream, TunnelError, get_session
        from core.utils import get_core_settings
        from meshctrl.utils import get_auth_token

        token = self.scope["url_route"]["kwargs"]["token"]
        path = self.scope["url_route"]["kwargs"].get("path", "")

        sess = await sync_to_async(get_session)(token)
        if not sess:
            await self.close()
            return

        core = await sync_to_async(get_core_settings)()
        auth_token = get_auth_token(core.mesh_api_superuser, core.mesh_token)
        use_tls = sess["protocol"] == "https"

        # browser request bits
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in self.scope.get("headers", [])}
        qs = self.scope.get("query_string", b"").decode("latin-1")
        target = "/" + path + (("?" + qs) if qs else "")

        host_hdr = sess["addr"]
        if (use_tls and sess["port"] != 443) or (not use_tls and sess["port"] != 80):
            host_hdr = f"{sess['addr']}:{sess['port']}"

        subprotocols = headers.get("sec-websocket-protocol")
        cookie = headers.get("cookie")
        key = base64.b64encode(os.urandom(16)).decode()

        req = [
            f"GET {target} HTTP/1.1",
            f"Host: {host_hdr}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
        ]
        if subprotocols:
            req.append(f"Sec-WebSocket-Protocol: {subprotocols}")
        if cookie:
            req.append(f"Cookie: {cookie}")
        req.append("\r\n")
        handshake = "\r\n".join(req).encode()

        try:
            self.tunnel = await TunnelStream.open(
                hex_node_id=sess["hex_node_id"], addr=sess["addr"], port=sess["port"],
                use_tls=use_tls, auth_token=auth_token,
            )
            await self.tunnel.write(handshake)

            # read the upgrade response headers
            buf = bytearray()
            while b"\r\n\r\n" not in buf:
                chunk = await asyncio.wait_for(self.tunnel.read(), 25)
                if chunk == b"":
                    raise TunnelError("device closed during ws handshake")
                buf += chunk
                if len(buf) > 65536:
                    raise TunnelError("ws handshake too large")
        except Exception as e:
            logger.error(f"ws proxy handshake failed {sess.get('addr')}:{sess.get('port')} - {e}")
            await self.close()
            return

        head, _, rest = bytes(buf).partition(b"\r\n\r\n")
        status_line = head.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        if " 101" not in status_line:
            logger.error(f"ws proxy device rejected upgrade: {status_line}")
            await self.tunnel.close()
            await self.close()
            return

        # negotiated subprotocol from device response
        negotiated = None
        for line in head.split(b"\r\n")[1:]:
            if line.lower().startswith(b"sec-websocket-protocol:"):
                negotiated = line.split(b":", 1)[1].strip().decode("latin-1")
                break

        await self.accept(subprotocol=negotiated)

        # any bytes after the handshake are the first WS frames
        if rest:
            await self._dispatch(self.decoder.feed(rest))

        self.reader_task = asyncio.create_task(self._reader())

    async def receive(self, text_data=None, bytes_data=None):
        if not self.tunnel:
            return
        try:
            if bytes_data is not None:
                await self.tunnel.write(encode_frame(OP_BIN, bytes_data))
            elif text_data is not None:
                await self.tunnel.write(encode_frame(OP_TEXT, text_data.encode()))
        except Exception:
            await self.close()

    async def _reader(self):
        try:
            while True:
                data = await self.tunnel.read()
                if data == b"":
                    break
                await self._dispatch(self.decoder.feed(data))
        except Exception:
            pass
        finally:
            with contextlib.suppress(Exception):
                await self.close()

    async def _dispatch(self, frames):
        for opcode, payload in frames:
            if opcode == OP_BIN:
                await self.send(bytes_data=payload)
            elif opcode == OP_TEXT:
                await self.send(text_data=payload.decode("utf-8", "replace"))
            elif opcode == OP_PING:
                with contextlib.suppress(Exception):
                    await self.tunnel.write(encode_frame(OP_PONG, payload))
            elif opcode == OP_CLOSE:
                await self.close()
                return

    async def disconnect(self, code):
        with contextlib.suppress(Exception):
            if self.reader_task:
                self.reader_task.cancel()
            if self.tunnel:
                # send a close frame to the device, then tear down
                with contextlib.suppress(Exception):
                    await self.tunnel.write(encode_frame(OP_CLOSE, b""))
                await self.tunnel.close()
