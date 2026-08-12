"""
Remote Web Proxy / Tunnel feature.

Lets an authenticated TRMM user reach the HTTP/HTTPS admin UI of a device on an
agent's LAN (e.g. a firewall at https://192.168.200.254:8443) without any local
client, extra ports, or manual port-forwarding.

Mechanism (validated end-to-end):
  * A short-lived "proxy session" is created server-side and stored in redis,
    binding a random token -> {agent, target addr, target port, protocol, user}.
  * The browser loads an iframe pointed at  /agentproxy/<token>/<path...>  which
    nginx routes to the ASGI (uvicorn) server.
  * For every request we open a raw TCP tunnel to the target through MeshCentral's
    relay  (ws://127.0.0.1:4430/meshrelay.ashx?nodeid&tcpaddr&tcpport&auth),
    optionally wrap it in TLS (MemoryBIO) for https targets, speak HTTP/1.1 with
    h11, then rewrite the response so it renders inside the iframe (strip
    X-Frame-Options/CSP, fix redirects + root-relative URLs).
"""

import asyncio
import contextlib
import re
import secrets
import ssl
import urllib.parse
from typing import Any, Optional

import h11
import websockets
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

from tacticalrmm.logger import logger


class TunnelError(Exception):
    """Raised when the agent cannot establish the tunnel to the target."""

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MESH_PORT = 4430
RELAY_HOST = "127.0.0.1"
SESSION_PREFIX = "webproxy:"
SESSION_TTL = 60 * 60 * 4  # 4 hours
HANDSHAKE_TIMEOUT = 25
IO_TIMEOUT = 60
MAX_BODY = 64 * 1024 * 1024  # 64MB hard cap per response

# Hop-by-hop headers that must never be forwarded
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


# ---------------------------------------------------------------------------
# Session store (redis via django cache)
# ---------------------------------------------------------------------------
def create_session(
    *, agent_id: str, hex_node_id: str, protocol: str, addr: str, port: int,
    username: str, hostname: str,
) -> str:
    token = secrets.token_urlsafe(32)
    cache.set(
        f"{SESSION_PREFIX}{token}",
        {
            "agent_id": agent_id,
            "hex_node_id": hex_node_id,
            "protocol": protocol,  # "http" | "https"
            "addr": addr,
            "port": int(port),
            "username": username,
            "hostname": hostname,
        },
        SESSION_TTL,
    )
    return token


def get_session(token: str) -> Optional[dict[str, Any]]:
    return cache.get(f"{SESSION_PREFIX}{token}")


# Per-session set of cookie names the device itself has set. We only forward
# these back to the device, so RMM's own cookies and other proxied devices'
# cookies are never sent to it (they bloat the header -> small embedded web
# servers like Ricoh reject it with 400, and it's an isolation/security win).
def _cookie_allow_key(token: str) -> str:
    return f"webproxyck:{token}"


def get_allowed_cookie_names(token: str) -> set:
    return cache.get(_cookie_allow_key(token)) or set()


def add_allowed_cookie_names(token: str, names) -> None:
    names = {n for n in names if n}
    if not names:
        return
    cur = cache.get(_cookie_allow_key(token)) or set()
    new = cur | names
    if new != cur:
        cache.set(_cookie_allow_key(token), new, SESSION_TTL)


# ---------------------------------------------------------------------------
# Tunnel stream (raw TCP over MeshCentral relay, with optional TLS)
# ---------------------------------------------------------------------------
class TunnelStream:
    """Async byte stream to <addr>:<port> reached *through the agent*."""

    def __init__(self, ws, use_tls: bool, server_hostname: str):
        self.ws = ws
        self.use_tls = use_tls
        self._handshake_timeout = HANDSHAKE_TIMEOUT
        self._tls = None
        self._inbio = None
        self._outbio = None
        if use_tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE  # device certs are self-signed
            # LAN appliances (printer/MFP web UIs like Toshiba TopAccess, IPMI/
            # iLO/iDRAC, older firewalls/switches) commonly only offer legacy TLS
            # (1.0/1.1) and weak ciphers or SHA1 certs that modern OpenSSL
            # defaults reject. We already don't verify the cert (self-signed) and
            # the link rides the agent's trusted LAN, so lower the TLS floor and
            # cipher security level instead of failing the handshake outright.
            with contextlib.suppress(Exception):
                ctx.minimum_version = ssl.TLSVersion.TLSv1
            with contextlib.suppress(Exception):
                ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
            self._inbio, self._outbio = ssl.MemoryBIO(), ssl.MemoryBIO()
            self._tls = ctx.wrap_bio(
                self._inbio, self._outbio, server_hostname=server_hostname or "device"
            )

    @classmethod
    async def open(cls, *, hex_node_id: str, addr: str, port: int, use_tls: bool,
                   auth_token: str, connect_timeout: int = HANDSHAKE_TIMEOUT) -> "TunnelStream":
        nodeid = f"node//{hex_node_id}"
        q = urllib.parse.urlencode(
            {"auth": auth_token, "nodeid": nodeid, "tcpport": str(port), "tcpaddr": addr}
        )
        uri = f"ws://{RELAY_HOST}:{MESH_PORT}/meshrelay.ashx?{q}"
        ws = await websockets.connect(uri, max_size=None, open_timeout=connect_timeout)

        # Wait for the 'c'/'cr' connect handshake. The relay only sends this once
        # the AGENT has actually established the TCP connection to addr:port, so a
        # timeout here means the chosen agent cannot reach the target.
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), connect_timeout)
                if isinstance(msg, bytes):
                    continue  # unexpected pre-connect binary, ignore
                if msg in ("c", "cr"):
                    break
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            with contextlib.suppress(Exception):
                await ws.close()
            raise TunnelError(
                f"The selected agent could not reach {addr}:{port}. The host may be "
                f"unreachable from that agent's network, blocked by a firewall, or the "
                f"port is closed. Try a different agent."
            )

        self = cls(ws, use_tls, addr)
        self._handshake_timeout = connect_timeout
        if use_tls:
            try:
                await self._do_handshake()
            except TunnelError:
                raise
            except Exception as e:
                logger.warning(
                    f"web proxy TLS handshake to {addr}:{port} failed: {e!r}"
                )
                with contextlib.suppress(Exception):
                    await ws.close()
                raise TunnelError(
                    f"Could not establish a secure connection to {addr}:{port} through "
                    f"this agent. The host is likely unreachable from that agent's "
                    f"network, blocked by a firewall, or not serving HTTPS on that port. "
                    f"Try a different agent."
                )
        return self

    async def _flush_out(self):
        data = self._outbio.read()
        if data:
            await self.ws.send(data)

    async def _do_handshake(self):
        while True:
            try:
                self._tls.do_handshake()
                break
            except ssl.SSLWantReadError:
                await self._flush_out()
                d = await asyncio.wait_for(self.ws.recv(), self._handshake_timeout)
                if isinstance(d, bytes):
                    self._inbio.write(d)
        await self._flush_out()

    async def write(self, data: bytes):
        if not self.use_tls:
            await self.ws.send(data)
            return
        self._tls.write(data)
        await self._flush_out()

    async def read(self) -> bytes:
        """Return next chunk of plaintext, or b'' on EOF."""
        if not self.use_tls:
            try:
                d = await asyncio.wait_for(self.ws.recv(), IO_TIMEOUT)
            except websockets.ConnectionClosed:
                return b""
            if isinstance(d, str):
                return await self.read()  # skip late control frames
            return d
        while True:
            try:
                out = self._tls.read(65536)
                return out  # may be b'' at clean EOF
            except ssl.SSLWantReadError:
                await self._flush_out()
                try:
                    d = await asyncio.wait_for(self.ws.recv(), IO_TIMEOUT)
                except (websockets.ConnectionClosed, asyncio.TimeoutError):
                    return b""
                if isinstance(d, bytes):
                    self._inbio.write(d)
            except (ssl.SSLEOFError, ssl.SSLError):
                return b""

    async def close(self):
        try:
            await self.ws.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Reachability probe: can <agent> actually reach <addr:port>?  (used to pick the
# best agent for a network device). Receiving the relay 'c' handshake means the
# agent successfully opened the TCP connection to the target.
# ---------------------------------------------------------------------------
async def _probe(hex_node_id, addr, port, protocol, auth_token, timeout):
    # The relay sends 'c' as soon as the agent reconnects, BEFORE the target TCP
    # is known-good, so we must actually exchange data to confirm reachability:
    #   https  -> a successful TLS handshake proves it
    #   http   -> send a request and require a response
    #   ssh/telnet -> the server speaks first (banner/negotiation)
    use_tls = protocol == "https"
    ts = None
    try:
        ts = await asyncio.wait_for(
            TunnelStream.open(
                hex_node_id=hex_node_id, addr=addr, port=int(port),
                use_tls=use_tls, auth_token=auth_token, connect_timeout=timeout,
            ),
            timeout + 3,
        )
        if use_tls:
            return True  # TLS handshake completing means the target is reachable
        if protocol == "http":
            await ts.write(
                b"HEAD / HTTP/1.0\r\nHost: " + addr.encode() + b"\r\n\r\n"
            )
        data = await asyncio.wait_for(ts.read(), timeout)
        return bool(data)
    except Exception:
        return False
    finally:
        if ts:
            with contextlib.suppress(Exception):
                await ts.close()


def agent_can_reach(hex_node_id, addr, port, protocol="https", timeout=6) -> bool:
    """Synchronous helper: True if the agent can actually talk to addr:port."""
    from core.utils import get_core_settings
    from meshctrl.utils import get_auth_token

    core = get_core_settings()
    token = get_auth_token(core.mesh_api_superuser, core.mesh_token)
    return asyncio.run(_probe(hex_node_id, addr, port, protocol, token, timeout))


# ---------------------------------------------------------------------------
# HTTP/1.1 round-trip over the tunnel using h11
# ---------------------------------------------------------------------------
async def http_request_via_tunnel(
    *, stream: TunnelStream, method: str, target: str, headers: list[tuple[str, str]],
    body: bytes,
) -> tuple[int, str, list[tuple[bytes, bytes]], bytes]:
    conn = h11.Connection(our_role=h11.CLIENT)

    to_send = conn.send(h11.Request(method=method, target=target, headers=headers))
    if body:
        to_send += conn.send(h11.Data(data=body))
    to_send += conn.send(h11.EndOfMessage())
    await stream.write(to_send)

    status = 502
    reason = "Bad Gateway"
    resp_headers: list[tuple[bytes, bytes]] = []
    chunks: list[bytes] = []
    total = 0
    got_response = False

    while True:
        event = conn.next_event()
        if event is h11.NEED_DATA:
            data = await stream.read()
            conn.receive_data(data)
            if data == b"":
                # peer closed; let h11 surface remaining events / end
                if conn.their_state in (h11.CLOSED, h11.DONE):
                    break
            continue
        if isinstance(event, h11.Response):
            got_response = True
            status = event.status_code
            reason = (event.reason or b"").decode("latin-1") if isinstance(event.reason, bytes) else str(event.reason or "")
            resp_headers = list(event.headers)
        elif isinstance(event, h11.Data):
            chunks.append(bytes(event.data))
            total += len(event.data)
            if total > MAX_BODY:
                break
        elif isinstance(event, (h11.EndOfMessage, h11.PAUSED)):
            break
        elif event is h11.ConnectionClosed or isinstance(event, h11.ConnectionClosed):
            break

    if not got_response:
        raise RuntimeError("no HTTP response from target")
    return status, reason, resp_headers, b"".join(chunks)


# ---------------------------------------------------------------------------
# Response rewriting so the page renders inside the TRMM iframe
# ---------------------------------------------------------------------------
def _prefix(token: str) -> str:
    return f"/agentproxy/{token}/"


def _service_worker_js() -> bytes:
    """Client-side request interceptor. Registered by the injected runtime at
    scope '/' so it can catch requests that escape the /agentproxy/<token>/
    prefix (root-relative or absolute same-origin URLs the app builds in JS, CSS
    url(), <img src>, etc. -- everything the network sees, not just hooked APIs).

    SAFETY: it only re-prefixes a request when that request ORIGINATES from a
    proxied page (its referrer is under /agentproxy/<token>/). Every other
    request -- i.e. the whole TacticalRMM app -- is left completely untouched.
    """
    js = r"""
var PFX = /\/agentproxy\/([A-Za-z0-9_\-]+)(?:\/|$)/;
self.addEventListener('install', function(e){ self.skipWaiting(); });
self.addEventListener('activate', function(e){ e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function(event){
  var req = event.request;
  var url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (url.origin !== self.location.origin) return;       // cross-origin: leave
  if (PFX.test(url.pathname)) return;                    // already prefixed: normal
  var ref = req.referrer || '';
  var m = ref.match(PFX);
  if (!m) return;                                        // not from a proxied page -> passthrough (RMM app)
  var target = url.origin + '/agentproxy/' + m[1] + url.pathname + url.search;
  if (req.mode === 'navigate') {
    // A link/form GET inside a proxied page navigated out of the prefix (e.g.
    // Ricoh login -> /web/.../authForm.cgi). Redirect to the prefixed URL so
    // the address bar keeps the prefix and relative resolution stays correct.
    // POST navigations are left alone (a redirect would drop the form body;
    // static form actions are already prefixed by the body rewrite).
    if (req.method === 'GET' || req.method === 'HEAD') {
      event.respondWith(Response.redirect(target, 302));
    }
    return;
  }
  event.respondWith((async function(){
    try {
      var init = { method: req.method, headers: req.headers, credentials: 'include', redirect: 'follow' };
      if (req.method !== 'GET' && req.method !== 'HEAD') { init.body = await req.clone().arrayBuffer(); }
      return await fetch(target, init);
    } catch (e) { try { return await fetch(req); } catch (e2) { return new Response('', {status: 502}); } }
  })());
});
"""
    return js.encode()


def rewrite_location(value: str, sess: dict, token: str) -> str:
    base = _prefix(token)
    # absolute URL pointing back at the device -> route through proxy
    for scheme in ("http://", "https://"):
        host = f"{scheme}{sess['addr']}"
        if value.startswith(host):
            rest = value[len(host):]
            # strip optional :port
            if rest.startswith(f":{sess['port']}"):
                rest = rest[len(f":{sess['port']}"):]
            if rest.startswith("/"):
                rest = rest[1:]
            return base + rest
    # root-relative
    if value.startswith("/"):
        return base + value[1:]
    return value


_ROOT_REL_RE = re.compile(
    rb'''(\b(?:href|src|action|formaction|data-url|background)\s*=\s*["'])/(?!/)''',
    re.IGNORECASE,
)
_CSS_URL_RE = re.compile(rb'''(url\(\s*["']?)/(?!/)''', re.IGNORECASE)
# ES-module specifiers: import X from "/path", import "/path", import("/path").
# These ignore <base> and resolve against the origin root, so rewrite them too.
_MODULE_IMPORT_RE = re.compile(rb'''((?:\bfrom|\bimport)\s*\(?\s*["'])/(?!/)''')


def _client_shim(token: str) -> bytes:
    """JS injected into HTML pages that patches XHR/fetch/WebSocket so URLs the
    app builds dynamically in JavaScript (e.g. Proxmox/ExtJS calling
    /api2/json/access/domains) are routed back through the proxy prefix."""
    import json as _json

    p = _prefix(token).rstrip("/")  # /agentproxy/<token>
    pj = _json.dumps(p)
    js = (
        "(function(){var P=" + pj + ";"
        "function fix(u){try{if(typeof u!=='string')return u;"
        "if(u.slice(0,P.length+1)===P+'/')return u;"  # already prefixed
        "if(u.charAt(0)==='/'&&u.charAt(1)!=='/')return P+u;"  # root-relative
        # absolute URL to our own origin (apps that build protocol+'//'+host+'/path',
        # e.g. Toshiba TopAccess gblTAUrl) -> insert the proxy prefix
        "var o=location.origin;"
        "if(u.slice(0,o.length+1)===o+'/'){var r=u.slice(o.length);"
        "if(r.slice(0,P.length+1)!==P+'/')return o+P+r;return u;}"
        "return u;}catch(e){return u;}}"
        "var O=XMLHttpRequest.prototype.open;"
        "XMLHttpRequest.prototype.open=function(){"
        "if(arguments.length>1){arguments[1]=fix(arguments[1]);}"
        "return O.apply(this,arguments);};"
        "if(window.fetch){var F=window.fetch;window.fetch=function(i,n){"
        "try{if(typeof i==='string'){i=fix(i);}}catch(e){}return F.call(this,i,n);};}"
        # Some appliance UIs (TopAccess) inject <script src=...>/<link href=...>
        # via document.write using absolute same-origin URLs that bypass <base>.
        # Rewrite src/href attributes in written markup through fix().
        "function fixhtml(s){try{return (''+s).replace("
        "/((?:src|href)\\s*=\\s*[\"'])([^\"']+)([\"'])/gi,"
        "function(m,a,u,b){return a+fix(u)+b;});}catch(e){return s;}}"
        "var DW=document.write,DWL=document.writeln;"
        "document.write=function(){return DW.apply(document,[].slice.call(arguments).map(fixhtml));};"
        "document.writeln=function(){return DWL.apply(document,[].slice.call(arguments).map(fixhtml));};"
        # WebSocket URLs are absolute (ws(s)://host/path); if they point at our own
        # host, re-route the path through the proxy prefix.
        "function fixws(u){try{if(typeof u!=='string')return u;"
        "var a=document.createElement('a');a.href=u;"
        "if(a.host===location.host&&a.pathname.indexOf(P+'/')!==0){"
        "var pr=(location.protocol==='https:')?'wss:':'ws:';"
        "return pr+'//'+location.host+P+a.pathname+a.search;}return u;}catch(e){return u;}}"
        "if(window.WebSocket){var W=window.WebSocket;var NW=function(u,pr){"
        "try{u=fixws(u);}catch(e){}return pr?new W(u,pr):new W(u);};"
        "NW.prototype=W.prototype;NW.CONNECTING=W.CONNECTING;NW.OPEN=W.OPEN;"
        "NW.CLOSING=W.CLOSING;NW.CLOSED=W.CLOSED;window.WebSocket=NW;}"
        # window.open() child windows/popups (e.g. Toshiba TopAccess opens
        # externalWindow/firstLevelWindow). Route their root-relative/absolute
        # same-origin URLs back through the proxy prefix so they aren't blank.
        "if(window.open){var OP=window.open;window.open=function(u,n,f){"
        "try{if(typeof u==='string'&&u){u=fix(u);}}catch(e){}"
        "return OP.call(window,u,n,f);};}"
        # Register the root-scoped request-interception service worker. It catches
        # every escaping sub-resource request generically (img/css/script/etc.),
        # not just the JS APIs hooked above. Reload once it takes control so the
        # initial page's resources go through it too.
        "try{if('serviceWorker' in navigator){"
        "navigator.serviceWorker.register(P+'/__apxsw.js',{scope:'/'}).then(function(reg){"
        "if(!navigator.serviceWorker.controller){"
        "navigator.serviceWorker.addEventListener('controllerchange',function(){location.reload();});}"
        "}).catch(function(){});}}catch(e){}"
        "})();"
    )
    return b"<script>" + js.encode() + b"</script>"


def _parse_set_cookie(header: str):
    """Parse a Set-Cookie header preserving the raw value. Returns
    (name, raw_value, attrs) with Domain intentionally dropped."""
    parts = header.split(";")
    nv = parts[0].strip()
    if "=" not in nv:
        return None, None, {}
    name, value = nv.split("=", 1)
    attrs: dict[str, Any] = {}
    for p in parts[1:]:
        p = p.strip()
        if not p:
            continue
        if "=" in p:
            k, v = p.split("=", 1)
            k = k.strip().lower()
            if k == "domain":  # scope to our origin
                continue
            attrs[k] = v.strip()
        else:
            attrs[p.lower()] = True
    return name.strip(), value, attrs


def rewrite_body(
    body: bytes, content_type: str, token: str, inject_shim: bool = True
) -> bytes:
    ct = (content_type or "").lower()
    prefix = _prefix(token).encode()

    # Only top-level document/iframe navigations get the HTML shim + <base>.
    # XHR/fetch responses are often text/html too (e.g. Toshiba TopAccess
    # contentwebserver); injecting <script>/<base> into those corrupts the
    # payload the app's AJAX handler parses, which makes it throw and call
    # fnClearAllSessionCookiesAndRedirect() in a loop. Leave them byte-exact.
    if "text/html" in ct and inject_shim:
        # static root-relative attribute URLs: ="/x" -> "/agentproxy/<token>/x"
        body = _ROOT_REL_RE.sub(rb"\1" + prefix[:-1] + b"/", body)
        # root-absolute ES-module imports: from "/x" -> from "/agentproxy/<token>/x"
        body = _MODULE_IMPORT_RE.sub(rb"\1" + prefix[:-1] + b"/", body)
        # Inject the runtime shim only. We deliberately do NOT add our own <base>:
        # relative URLs resolve correctly against the document's own path by
        # default (works for both root and sub-path documents, e.g. Ricoh's
        # /web/.../mainFrame.cgi referencing header.cgi), and root-relative/
        # absolute URLs are handled by the body rewrite + service worker. Forcing
        # a prefix-root <base> broke relative URLs in sub-path documents
        # (e.g. Ricoh frames -> /header.cgi 404). A device's OWN <base> is left
        # in place (already rewritten to the prefix by _ROOT_REL_RE).
        m = re.search(rb"<head[^>]*>", body, re.IGNORECASE)
        inject = _client_shim(token)
        if m:
            body = body[: m.end()] + inject + body[m.end():]
        else:
            body = inject + body
        return body

    if "text/css" in ct:
        return _CSS_URL_RE.sub(rb"\1" + prefix[:-1] + b"/", body)

    # leave JS/JSON/XML/binary untouched - the runtime shim handles dynamic URLs
    return body


# ---------------------------------------------------------------------------
# Main ASGI proxy view  (served by uvicorn via nginx /agentproxy/ -> daphne.sock)
# ---------------------------------------------------------------------------
async def agent_web_proxy(request, token: str, path: str = ""):
    sess = await sync_to_async(get_session)(token)
    if not sess:
        r = HttpResponse("Proxy session expired or invalid.", status=410)
        r.xframe_options_exempt = True
        return r

    # Serve the request-interception service worker (registered by the injected
    # runtime). Served by the proxy itself, NOT tunneled to the device.
    if path == "__apxsw.js":
        r = HttpResponse(
            _service_worker_js(), content_type="application/javascript"
        )
        r["Service-Worker-Allowed"] = "/"
        r["Cache-Control"] = "no-cache"
        r.xframe_options_exempt = True
        return r

    from core.utils import get_core_settings
    from meshctrl.utils import get_auth_token

    core = await sync_to_async(get_core_settings)()
    auth_token = get_auth_token(core.mesh_api_superuser, core.mesh_token)

    use_tls = sess["protocol"] == "https"

    # Build upstream target (path + query)
    target = "/" + path
    qs = request.META.get("QUERY_STRING", "")
    if qs:
        target += "?" + qs

    # Build upstream headers
    host_hdr = sess["addr"]
    if (use_tls and sess["port"] != 443) or (not use_tls and sess["port"] != 80):
        host_hdr = f"{sess['addr']}:{sess['port']}"

    allowed_cookies = await sync_to_async(get_allowed_cookie_names)(token)
    up_headers: list[tuple[str, str]] = [("host", host_hdr)]
    for key, val in request.headers.items():
        lk = key.lower()
        if lk in HOP_BY_HOP or lk in ("host", "accept-encoding"):
            continue
        if lk == "referer" or lk == "origin":
            continue  # avoid leaking the proxy origin to the device
        if lk == "cookie":
            # only forward cookies this device set (drop RMM's + other devices')
            kept = [
                part.strip()
                for part in val.split(";")
                if part.strip().split("=", 1)[0].strip() in allowed_cookies
            ]
            if kept:
                up_headers.append(("cookie", "; ".join(kept)))
            continue
        up_headers.append((lk, val))
    up_headers.append(("accept-encoding", "identity"))  # no compression -> easy rewrite
    up_headers.append(("connection", "close"))

    body = request.body or b""

    stream = None
    try:
        stream = await TunnelStream.open(
            hex_node_id=sess["hex_node_id"], addr=sess["addr"], port=sess["port"],
            use_tls=use_tls, auth_token=auth_token,
        )
        status, reason, resp_headers, resp_body = await http_request_via_tunnel(
            stream=stream, method=request.method, target=target,
            headers=up_headers, body=body,
        )
    except TunnelError as e:
        logger.error(f"web proxy unreachable {sess.get('addr')}:{sess.get('port')} - {e}")
        r = HttpResponse(str(e), status=502, content_type="text/plain")
        r.xframe_options_exempt = True
        return r
    except Exception as e:
        logger.error(f"web proxy error {sess.get('addr')}:{sess.get('port')} - {e!r}")
        r = HttpResponse(f"Proxy error: {e}", status=502, content_type="text/plain")
        r.xframe_options_exempt = True
        return r
    finally:
        if stream:
            await stream.close()

    # Find content type
    content_type = "application/octet-stream"
    out_headers: dict[str, str] = {}
    set_cookies: list[str] = []
    for hk, hv in resp_headers:
        k = hk.decode("latin-1").lower()
        v = hv.decode("latin-1")
        if k in HOP_BY_HOP or k == "content-length":
            continue
        if k in ("x-frame-options",):
            continue  # allow iframing
        if k == "content-security-policy":
            # drop frame-ancestors restrictions
            continue
        if k == "content-type":
            content_type = v
            out_headers["Content-Type"] = v
            continue
        if k == "location":
            v = rewrite_location(v, sess, token)
            out_headers["Location"] = v
            continue
        if k == "set-cookie":
            set_cookies.append(v)  # parsed byte-exact below (Domain dropped there)
            continue
        out_headers[hk.decode("latin-1")] = v

    # Decide whether this response is a document/iframe navigation (inject the
    # client shim) or an XHR/fetch/sub-resource (leave body untouched). Prefer
    # the Fetch Metadata header; fall back to X-Requested-With for old clients.
    _sfd = request.headers.get("Sec-Fetch-Dest", "").lower()
    if _sfd:
        _inject = _sfd in ("document", "iframe", "frame", "object", "embed")
    else:
        _inject = (
            request.headers.get("X-Requested-With", "").lower() != "xmlhttprequest"
        )
    resp_body = rewrite_body(resp_body, content_type, token, inject_shim=_inject)

    resp = HttpResponse(resp_body, status=status, content_type=content_type)
    for hk, hv in out_headers.items():
        if hk.lower() == "content-type":
            continue
        resp[hk] = hv
    # Pass through device cookies BYTE-EXACT. We must not reserialize the value
    # via SimpleCookie, which quotes values containing '='/'%'/':' etc. and would
    # corrupt tickets (e.g. Proxmox/PBS __Host-PBSAuthCookie -> 401 right after
    # login). We only strip Domain; Path=/ and Secure are preserved so __Host-*
    # prefixed cookies remain valid.
    _set_cookie_names: list[str] = []
    for c in set_cookies:
        name, value, attrs = _parse_set_cookie(c)
        if not name:
            continue
        _set_cookie_names.append(name)
        resp.cookies[name] = ""
        # set raw value as both value and coded_value -> emitted exactly, no quoting
        try:
            resp.cookies[name].set(name, value, value)
        except Exception:
            resp.cookies[name] = value  # fallback (will quote, but better than drop)
        # Scope cookies to THIS session's path so devices proxied on the same
        # origin don't clobber each other. Multiple appliances (e.g. two Toshiba
        # TopAccess printers) all set `Session` at Path=/, which overwrite each
        # other on rmm.blueuc.com and make the device report INVALID_SESSION_ID.
        # __Host-/__Secure- prefixed cookies must keep Path=/ to stay valid, so
        # leave those as-is.
        if name[:7].lower() == "__host-" or name[:9].lower() == "__secure-":
            resp.cookies[name]["path"] = "/"
        else:
            resp.cookies[name]["path"] = _prefix(token)
        if "expires" in attrs:
            resp.cookies[name]["expires"] = attrs["expires"]
        if "max-age" in attrs:
            resp.cookies[name]["max-age"] = attrs["max-age"]
        if "samesite" in attrs:
            resp.cookies[name]["samesite"] = attrs["samesite"]
        if attrs.get("secure"):
            resp.cookies[name]["secure"] = True
        if attrs.get("httponly"):
            resp.cookies[name]["httponly"] = True
    if _set_cookie_names:
        await sync_to_async(add_allowed_cookie_names)(token, _set_cookie_names)
    resp["X-Robots-Tag"] = "noindex"
    resp.xframe_options_exempt = True
    return resp


# This view only forwards requests to the proxied device, which performs its own
# CSRF protection. Exempt it from Django's CsrfViewMiddleware so POSTs (e.g. the
# pfSense login form) aren't rejected with a Django 403 before reaching the device.
agent_web_proxy.csrf_exempt = True
