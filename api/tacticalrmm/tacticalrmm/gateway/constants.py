import re

ANSI_ESCAPE = re.compile(
    r'\x1b\[[0-9;]*[a-zA-Z]|\x1b[()][AB012]|\x1b[>=]'
)


def _strip_ansi(data):
    return ANSI_ESCAPE.sub("", data)


TERMINAL_MODES = {
    4: 4,
    3: 3,
    21: 21,
    28: 28,
    17: 17,
    19: 19,
    26: 26,
    0: 0,
    1: 1,
    8: 0,
    8: 0,
    8: 0,
    8: 0,
    8: 0,
    8: 0,
    128: 1,
    16: 1,
    32: 1,
    0: 0,
}

WELCOME_TEMPLATE = (
    "\r\n\x1b[32mWelcome, \x1b[1m{username}\x1b[0m\x1b[32m "
    "[\x1b[1mRole: {role}\x1b[0m\x1b[32m]\x1b[0m\r\n"
    "\x1b[32mSSH session open on \x1b[1m{hostname}\x1b[0m\x1b[32m "
    "({os_info}), shell: {shell}, agent: {agent_ver}, via TRMM proxy\x1b[0m\r\n"
    "\x1b[32mpubip: {pubip}, local IPs: {local_ips}\x1b[0m\r\n\r\n"
)

WELCOME_TEMPLATE_PLAIN = (
    "Welcome, {username} [Role: {role}]\n"
    "SSH session open on {hostname} ({os_info}), shell: {shell}, agent: {agent_ver}, via TRMM proxy\n"
    "pubip: {pubip}, local IPs: {local_ips}\n\n"
)

TRMM_LOGO = """@@@@@@@@@
    @@@@      @@@@
   @@@          @@@
  @@* @@@@@@@@@@ @@@
  @@      @@      @@
  @@    @ @@ @    @@
  @@.  @@ @@ @@  @@@
   @@@ @@ @@ @@ @@@
    @@@@@ @@ @@@@@
      @@@@@@@@@@"""

RATE_LIMITER_DEFAULT_MAX_ENTRIES = 1000
RATE_LIMITER_CLEANUP_INTERVAL = 300