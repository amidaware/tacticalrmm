import fcntl
import json
import logging
import os

from django.utils import timezone as djangotime

logger = logging.getLogger("trmm")

_HIGHSCORES_PATH = "/etc/trmm/snake_highscores.json"


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


def _save_highscores(scores):
    try:
        os.makedirs(os.path.dirname(_HIGHSCORES_PATH), exist_ok=True)
        with open(_HIGHSCORES_PATH, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(scores, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        logger.debug("Failed to save highscores: %s", e)


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
                existing = next((i for i, s in enumerate(scores) if s["username"] == username), None)
                if existing is not None:
                    if score > scores[existing]["score"]:
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
        logger.debug("Failed to update highscores: %s", e)
        return []
    return scores


def _format_highscores(scores):
    if not scores:
        return ""
    lines = [
        "\x1b[1m\xe2\x94\x80 High Scores " +
        "\xe2\x94\x80" * 42 + "\x1b[0m\r\n",
    ]
    for i, entry in enumerate(scores[:10], 1):
        star = " \xe2\x98\x85" if entry.get("won") else "   "
        lines.append(
            f"  {i:>2}. {entry['username']:<20} {entry['score']:>4}{star}\r\n"
        )
    lines.append(
        "\x1b[2m" + "\xe2\x94\x80" * 52 + "\x1b[0m\r\n"
    )
    return "".join(lines)
