"""
Terminal bridging for the Remote Terminal feature (SSH / Telnet to a device on
an agent's LAN, through the MeshCentral relay).

Reuses agents.web_proxy.TunnelStream for the raw-TCP-over-relay transport.
  * Telnet -> raw byte bridge + minimal IAC option negotiation.
  * SSH    -> asyncssh client bridged to the tunnel via a loopback TCP socketpair
              (asyncssh terminates SSH server-side and gives us a clean PTY).
"""
import asyncio
import socket

# ---------------------------------------------------------------------------
# Telnet (RFC854) minimal client-side option negotiation
# ---------------------------------------------------------------------------
IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251
SB = 250
SE = 240
OPT_ECHO = 1
OPT_SGA = 3
OPT_TTYPE = 24


class TelnetFilter:
    """Strips/answers IAC sequences from a telnet stream.

    feed(data) -> (clean_output_bytes, reply_bytes_to_send_to_server)
    Handles sequences split across reads.
    """

    def __init__(self, term_type: bytes = b"xterm"):
        self.term_type = term_type
        self._buf = bytearray()
        self._state = "data"  # data | iac | opt | sb | sb_iac
        self._cmd = 0
        self._sb = bytearray()

    def feed(self, data: bytes):
        out = bytearray()
        reply = bytearray()
        for byte in data:
            if self._state == "data":
                if byte == IAC:
                    self._state = "iac"
                else:
                    out.append(byte)
            elif self._state == "iac":
                if byte == IAC:  # escaped 0xFF
                    out.append(IAC)
                    self._state = "data"
                elif byte in (DO, DONT, WILL, WONT):
                    self._cmd = byte
                    self._state = "opt"
                elif byte == SB:
                    self._sb = bytearray()
                    self._state = "sb"
                else:
                    # standalone command (GA, NOP, etc.) - ignore
                    self._state = "data"
            elif self._state == "opt":
                self._negotiate(self._cmd, byte, reply)
                self._state = "data"
            elif self._state == "sb":
                if byte == IAC:
                    self._state = "sb_iac"
                else:
                    self._sb.append(byte)
            elif self._state == "sb_iac":
                if byte == SE:
                    self._handle_sb(bytes(self._sb), reply)
                    self._state = "data"
                else:
                    self._sb.append(byte)
                    self._state = "sb"
        return bytes(out), bytes(reply)

    def _negotiate(self, cmd, opt, reply):
        if cmd == DO:
            if opt == OPT_SGA:
                reply += bytes([IAC, WILL, opt])
            elif opt == OPT_TTYPE:
                reply += bytes([IAC, WILL, opt])
            else:
                reply += bytes([IAC, WONT, opt])
        elif cmd == WILL:
            if opt in (OPT_ECHO, OPT_SGA):
                reply += bytes([IAC, DO, opt])
            else:
                reply += bytes([IAC, DONT, opt])
        elif cmd == WONT:
            reply += bytes([IAC, DONT, opt])
        elif cmd == DONT:
            reply += bytes([IAC, WONT, opt])

    def _handle_sb(self, sb: bytes, reply):
        # respond to TTYPE SEND with our terminal type
        if len(sb) >= 2 and sb[0] == OPT_TTYPE and sb[1] == 1:  # SEND
            reply += bytes([IAC, SB, OPT_TTYPE, 0]) + self.term_type + bytes([IAC, SE])


def tcp_socketpair():
    """A connected pair of loopback TCP sockets (asyncssh needs a real peername)."""
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.bind(("127.0.0.1", 0))
    ls.listen(1)
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.connect(ls.getsockname())
    s, _ = ls.accept()
    ls.close()
    return c, s


async def bridge_socket_to_tunnel(tunnel, sock, loop):
    """Pipe a raw socket <-> TunnelStream. Returns a gather() task."""
    sock.setblocking(False)

    async def s2t():
        try:
            while True:
                d = await loop.sock_recv(sock, 65536)
                if not d:
                    break
                await tunnel.write(d)
        except Exception:
            pass

    async def t2s():
        try:
            while True:
                d = await tunnel.read()
                if d == b"":
                    break
                await loop.sock_sendall(sock, d)
        except Exception:
            pass

    return asyncio.gather(s2t(), t2s())
