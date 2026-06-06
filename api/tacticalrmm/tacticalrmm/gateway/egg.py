import asyncio
import logging
import random

from .highscores import _add_highscore, _format_highscores

logger = logging.getLogger("trmm")


class EggGame:
    def __init__(self, handler):
        self._handler = handler
        self._chan = handler._chan
        self._user = handler._user

    async def start(self):
        self._handler._state = "snake"
        self._snake_width = 40
        self._snake_height = 16
        mid_r = self._snake_height // 2
        mid_c = self._snake_width // 2
        self._snake_body = [(mid_r, c) for c in range(mid_c, mid_c - 3, -1)]
        self._snake_dir = (0, 1)
        self._snake_score = 0
        self._snake_buf = ""
        self._snake_food = self._snake_place_food()
        await self._handler._write("\x1b[2J\x1b[H")
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
        lines.append(
            f"Score: {self._snake_score}    (WASD move, Q quit)\r\n"
        )
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
        await self._handler._write("".join(lines))

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
            logger.error("SSH egg loop error: %s", e, exc_info=True)

    async def _game_over(self):
        scores = _add_highscore(self._user.username, self._snake_score, False)
        lines = [
            "\x1b[H\x1b[J",
            "\x1b[31mGame Over!\x1b[0m\r\n",
            f"Score: {self._snake_score}\r\n",
            "\r\n",
            _format_highscores(scores),
            "\r\nPress any key to return to menu...\r\n",
        ]
        await self._handler._write("".join(lines))
        self._handler._state = "snake_gameover"

    async def _win(self):
        scores = _add_highscore(self._user.username, self._snake_score, True)
        lines = [
            "\x1b[H\x1b[J",
            "\x1b[32mYou Win!\x1b[0m\r\n",
            f"Final Score: {self._snake_score}\r\n",
            "\r\n",
            _format_highscores(scores),
            "\r\nPress any key to return to menu...\r\n",
        ]
        await self._handler._write("".join(lines))
        self._handler._state = "snake_gameover"

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
        self._handler._state = "client"
        await self._handler._show_clients()
