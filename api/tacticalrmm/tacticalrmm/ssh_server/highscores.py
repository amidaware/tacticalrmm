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
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_highscores(scores):
    try:
        os.makedirs(os.path.dirname(_HIGHSCORES_PATH), exist_ok=True)
        with open(_HIGHSCORES_PATH, "w") as f:
            json.dump(scores, f, indent=2)
    except OSError as e:
        logger.debug("Failed to save highscores: %s", e)


def _add_highscore(username, score, won):
    scores = _load_highscores()
    scores.append({
        "username": username,
        "score": score,
        "won": won,
        "date": djangotime.now().isoformat(),
    })
    scores.sort(key=lambda s: (-s["score"], s["date"]))
    scores = scores[:20]
    _save_highscores(scores)
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
