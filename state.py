"""Tracks which paper IDs have already been notified, so re-running the
digest (or overlapping lookback windows) never emails the same paper twice."""
import json
import os

_STATE_DIR = os.path.join(os.path.dirname(__file__), ".state")
_STATE_FILE = os.path.join(_STATE_DIR, "seen_papers.json")
_MAX_HISTORY = 5000


def load_seen_ids():
    if not os.path.exists(_STATE_FILE):
        return set()
    with open(_STATE_FILE, "r") as f:
        try:
            return set(json.load(f))
        except json.JSONDecodeError:
            return set()


def save_seen_ids(seen_ids):
    os.makedirs(_STATE_DIR, exist_ok=True)
    trimmed = list(seen_ids)[-_MAX_HISTORY:]
    with open(_STATE_FILE, "w") as f:
        json.dump(trimmed, f)


def filter_unseen(papers, seen_ids):
    return [p for p in papers if p.get("id") not in seen_ids]
