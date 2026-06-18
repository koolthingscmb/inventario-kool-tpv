from datetime import datetime, timezone


def now_utc_str():
    """Return current UTC time as 'YYYY-MM-DD HH:MM:SS' string."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def utc_str_to_local_str(ts: str, out_fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Convert a UTC timestamp string to local timezone string.

    - If `ts` is None or empty, returns empty string.
    - Accepts timestamps like 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.
    - If `ts` already contains timezone info, it's respected.
    """
    if not ts:
        return ''
    try:
        # Handle naive timestamps (assume UTC)
        if ts.endswith('Z'):
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            # Try parse; if no tzinfo, attach UTC
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone()  # convert to local timezone
        return local.strftime(out_fmt)
    except Exception:
        try:
            # Fallback: simple split and return original
            if ' ' in ts:
                return ts
            return ts
        except Exception:
            return ''


def format_ddmmyyyy(ts: str, include_time: bool = True) -> str:
    """Format a SQLite-like timestamp to DD-MM-YYYY [HH:MM] using dashes.

    - Accepts 'YYYY-MM-DD HH:MM:SS', 'YYYY-MM-DD HH:MM', ISO with T, or date only.
    - Strips fractional seconds and 'Z'.
    - If include_time=False or no time part, returns only date.
    - Returns original string on failure (safe fallback).
    """
    if not ts:
        return ""
    s = str(ts).strip()
    if not s:
        return ""
    # Normalize: drop micros and Z
    s = s.split('.')[0].rstrip('Z').replace('T', ' ')
    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for fmt_in in candidates:
        try:
            dt = datetime.strptime(s, fmt_in)
            if include_time and "%H" in fmt_in:
                return dt.strftime("%d-%m-%Y %H:%M")
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue
    # fallback: return as-is (won't crash UI)
    return str(ts)
