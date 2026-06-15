import asyncio
import fcntl
import json
import os
import random

import asyncssh
from django.utils import timezone as djangotime

from ..logger import gw_log

_HIGHSCORES_PATH = "/etc/trmm/snake_highscores.json"


class EggGame:
    def __init__(self, handler):
        self._handler = handler
        self._chan = handler._chan
        self._user = handler._user
        self._snake_width = 40
        self._snake_height = 16
        self._snake_body = []
        self._snake_dir = (0, 1)
        self._snake_score = 0
        self._snake_buf = ""
        self._snake_food = None

    async def start(self):
        self._handler._state = "snake"
        mid_r = self._snake_height // 2
        mid_c = self._snake_width // 2
        self._snake_body = [(mid_r, c) for c in range(mid_c, mid_c - 3, -1)]
        self._snake_food = self._snake_place_food()
        await self._write("\x1b[2J\x1b[H")
        await self._draw()
        asyncio.create_task(self._loop())

    def _snake_place_food(self):
        occupied = set(self._snake_body)
        free = self._snake_height * self._snake_width - len(occupied)
        if free <= 0:
            return None
        for _ in range(100):
            r = random.randrange(self._snake_height)
            c = random.randrange(self._snake_width)
            if (r, c) not in occupied:
                return (r, c)
        for r in range(self._snake_height):
            for c in range(self._snake_width):
                if (r, c) not in occupied:
                    return (r, c)
        return None

    async def _draw(self):
        lines = ["\x1b[H"]
        lines.append(f"Score: {self._snake_score}    (WASD move, Q quit)\r\n")
        for r in range(self._snake_height):
            for c in range(self._snake_width):
                if (r, c) == self._snake_body[0]:
                    lines.append("\x1b[32mO\x1b[0m")
                elif (r, c) in self._snake_body:
                    lines.append("o")
                elif self._snake_food and (r, c) == self._snake_food:
                    lines.append("\x1b[33m@\x1b[0m")
                else:
                    lines.append(".")
            lines.append("\r\n")
        lines.append("\x1b[J")
        await self._write("".join(lines))

    async def _loop(self):
        try:
            while self._handler._state == "snake":
                await asyncio.sleep(0.15)
                if self._handler._state != "snake":
                    return
                head = self._snake_body[0]
                dr, dc = self._snake_dir
                new_head = (head[0] + dr, head[1] + dc)
                if not (0 <= new_head[0] < self._snake_height and 0 <= new_head[1] < self._snake_width):
                    await self._game_over()
                    return
                if new_head in self._snake_body:
                    await self._game_over()
                    return
                self._snake_body.insert(0, new_head)
                if new_head == self._snake_food:
                    self._snake_score += 1
                    self._snake_food = self._snake_place_food()
                    if self._snake_food is None:
                        await self._win()
                        return
                else:
                    self._snake_body.pop()
                await self._draw()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            gw_log.error("SSH egg loop error: %s", e, exc_info=True)

    async def _game_over(self):
        scores = _add_highscore(self._user.username, self._snake_score, False)
        lines = [
            "\x1b[H\x1b[J",
            "\x1b[31mGame Over!\x1b[0m\r\n",
            f"Score: {self._snake_score}\r\n",
            "\r\n",
            _format_highscores(scores),
            "\r\nPress any key to exit...\r\n",
        ]
        await self._write("".join(lines))
        self._handler._state = "exit"

    async def _win(self):
        scores = _add_highscore(self._user.username, self._snake_score, True)
        lines = [
            "\x1b[H\x1b[J",
            "\x1b[32mYou Win!\x1b[0m\r\n",
            f"Final Score: {self._snake_score}\r\n",
            "\r\n",
            _format_highscores(scores),
            "\r\nPress any key to exit...\r\n",
        ]
        await self._write("".join(lines))
        self._handler._state = "exit"

    def handle_input(self, ch):
        if ch.lower() == "q" or ch == "\x03":
            asyncio.create_task(self._quit())
            return
        dirs = {"w": (-1, 0), "s": (1, 0), "a": (0, -1), "d": (0, 1)}
        if ch.lower() in dirs:
            dr, dc = dirs[ch.lower()]
            if (dr, dc) != (-self._snake_dir[0], -self._snake_dir[1]):
                self._snake_dir = (dr, dc)
            return
        self._snake_buf += ch
        if len(self._snake_buf) > 10:
            self._snake_buf = self._snake_buf[-5:]
        for seq, dr, dc in [
            ("\x1b[A", -1, 0), ("\x1b[B", 1, 0),
            ("\x1b[C", 0, 1), ("\x1b[D", 0, -1),
        ]:
            if seq in self._snake_buf:
                self._snake_buf = ""
                if (dr, dc) != (-self._snake_dir[0], -self._snake_dir[1]):
                    self._snake_dir = (dr, dc)
                return

    async def _quit(self):
        self._handler._state = "exit"
        self._chan.exit(0)

    async def _write(self, text=""):
        if self._chan and not self._chan.is_closing():
            self._chan.write(text)


class Handler(asyncssh.SSHServerSession):
    name = "egg"

    def __init__(self, user, session_id, remote_ip,
                 client_version="", ssh_key_name="", ssh_key_type="",
                 ssh_key_fingerprint=""):
        super().__init__()
        self._user = user
        self._session_id = session_id
        self._remote_ip = remote_ip
        self._client_version = client_version
        self._ssh_key_name = ssh_key_name
        self._ssh_key_type = ssh_key_type
        self._ssh_key_fingerprint = ssh_key_fingerprint
        self._chan = None
        self._state = "init"
        self._game = None

    def connection_made(self, chan):
        self._chan = chan

    def pty_requested(self, term_type, term_size, term_modes):
        return True

    def shell_requested(self):
        self._state = "started"
        asyncio.create_task(self._run())
        return True

    async def _run(self):
        self._game = EggGame(self)
        await self._game.start()

    def data_received(self, data, datatype):
        if self._state == "exit":
            self._chan.exit(0)
            return
        if self._state == "snake_gameover":
            self._state = "exit"
            self._chan.exit(0)
            return
        if self._game and self._state == "snake":
            if isinstance(data, bytes):
                text = data.decode("utf-8", errors="replace")
            else:
                text = data
            for ch in text:
                self._game.handle_input(ch)

    def eof_received(self):
        return False

    def connection_lost(self, exc):
        pass

    def closed(self):
        pass


def _load_highscores():
    if not os.path.exists(_HIGHSCORES_PATH):
        return []
    try:
        with open(_HIGHSCORES_PATH, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                data = f.read()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            if not data:
                return []
            return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return []


def _add_highscore(username, score, won):
    try:
        with open(_HIGHSCORES_PATH, "a+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                try:
                    scores = json.load(f)
                except json.JSONDecodeError:
                    scores = []
                existing = next(
                    (i for i, s in enumerate(scores) if s["username"] == username),
                    None,
                )
                if existing is not None:
                    if score >= scores[existing]["score"]:
                        scores[existing] = {
                            "username": username,
                            "score": score,
                            "won": won,
                            "date": djangotime.now().isoformat(),
                        }
                else:
                    scores.append({
                        "username": username,
                        "score": score,
                        "won": won,
                        "date": djangotime.now().isoformat(),
                    })
                scores.sort(key=lambda s: (-s["score"], s["date"]))
                scores = scores[:20]
                f.seek(0)
                f.truncate()
                json.dump(scores, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        gw_log.debug("Failed to update highscores: %s", e)
        return []
    return scores


def _format_highscores(scores):
    if not scores:
        return ""
    lines = [
        "\x1b[1m\u2500 High Scores " + "\u2500" * 42 + "\x1b[0m\r\n",
    ]
    for i, entry in enumerate(scores[:10], 1):
        star = " \u2605" if entry.get("won") else "   "
        lines.append(f"  {i:>2}. {entry['username']:<20} {entry['score']:>4}{star}\r\n")
    lines.append("\x1b[2m" + "\u2500" * 52 + "\x1b[0m\r\n")
    return "".join(lines)
