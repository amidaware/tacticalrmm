# SSH Gateway Functions

Drop a `.py` file here with an `asyncssh.SSHServerSession` subclass named `Handler` (or any subclass with `name` attribute). It auto-registers as `{name}@host` SSH destinations, callable from the menu by typing its name.

## Interface

- **`Handler`** — must be an `asyncssh.SSHServerSession` subclass with a class-level `name` attribute (e.g. `name = "egg"`)
- **`launch(menu_handler)`** — optional coroutine for deep menu integration. If absent, the menu creates a standalone Handler instance and wraps its channel so `exit()` returns to the menu instead of closing the session.

## Example

```python
import asyncssh

class Handler(asyncssh.SSHServerSession):
    name = "hello"

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self):
        self._chan.write("Hello, world!\r\n")
        self._chan.exit(0)
        return True
```

Typing `hello` in the menu (or `ssh hello@host`) runs it.
