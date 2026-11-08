"""Local Gnani request counter + daily ceiling. These are NOT official Gnani credits."""
from __future__ import annotations

from app.core.config import get_settings
from app.db.database import db, today_local


class UsageLimitExceeded(RuntimeError):
    pass


def check_allowed() -> None:
    limit = get_settings().daily_gnani_request_limit
    if limit <= 0:
        return
    with db() as c:
        row = c.execute("SELECT COALESCE(SUM(calls),0) AS n FROM usage_counters WHERE day=?",
                        (today_local().isoformat(),)).fetchone()
    if row["n"] >= limit:
        raise UsageLimitExceeded(f"Daily Gnani request limit ({limit}) reached. Raise DAILY_GNANI_REQUEST_LIMIT to continue.")


def record(kind: str, *, calls: int = 0, audio_seconds: float = 0.0, chars: int = 0,
           cache_hits: int = 0, errors: int = 0) -> None:
    day = today_local().isoformat()
    with db() as c:
        c.execute("INSERT OR IGNORE INTO usage_counters (day, kind) VALUES (?,?)", (day, kind))
        c.execute(
            "UPDATE usage_counters SET calls=calls+?, audio_seconds=audio_seconds+?, chars=chars+?,"
            " cache_hits=cache_hits+?, errors=errors+? WHERE day=? AND kind=?",
            (calls, audio_seconds, chars, cache_hits, errors, day, kind),
        )


def summary() -> dict:
    s = get_settings()
    with db() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM usage_counters ORDER BY day DESC, kind")]
    today = today_local().isoformat()
    today_calls = sum(r["calls"] for r in rows if r["day"] == today)
    return {
        "label": "Local request count (not official Gnani credits)",
        "official_balance_available": False,
        "official_balance_note": "Gnani's documented API returns no credit or usage data; check app.gnani.ai for the official balance.",
        "today": today,
        "today_calls": today_calls,
        "daily_limit": s.daily_gnani_request_limit,
        "fixture_mode": s.gnani_fixture_mode,
        "rows": rows,
    }
