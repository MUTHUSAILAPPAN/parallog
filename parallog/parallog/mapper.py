"""
The MAP phase.

map_chunk() consumes a list of raw log lines belonging to one chunk and
emits a partial, JSON-serializable summary (counts + latency samples).
It is executed independently and concurrently for every chunk -- in a
local worker process (multiprocessing) or on a remote worker node
(distributed HTTP), which is why its output must be plain
dict/list/number data rather than live Python objects like Counter.
"""

from collections import Counter

from .parser import parse_line
from .stats import ReservoirSample

RESERVOIR_CAPACITY = 1000


def _empty_endpoint_stat():
    return {
        "count": 0,
        "sum_ms": 0.0,
        "min_ms": None,
        "max_ms": None,
        "reservoir": ReservoirSample(RESERVOIR_CAPACITY),
    }


def map_chunk(lines, config=None):
    config = config or {}

    total_lines = 0
    parse_errors = 0
    level_counts = Counter()
    status_class_counts = Counter()
    endpoint_counts = Counter()
    method_counts = Counter()
    endpoint_stats = {}

    for raw_line in lines:
        total_lines += 1
        record = parse_line(raw_line)
        if record is None:
            parse_errors += 1
            continue

        level = record.get("level") or "UNKNOWN"
        level_counts[level] += 1

        status = record.get("status")
        if status is not None:
            try:
                status_class = f"{int(status) // 100}xx"
                status_class_counts[status_class] += 1
            except (ValueError, TypeError):
                pass

        endpoint = record.get("endpoint")
        if endpoint:
            endpoint_counts[endpoint] += 1

        method = record.get("method")
        if method:
            method_counts[method] += 1

        rt = record.get("response_time_ms")
        if endpoint and rt is not None:
            try:
                rt = float(rt)
            except (ValueError, TypeError):
                rt = None
            if rt is not None:
                stat = endpoint_stats.setdefault(endpoint, _empty_endpoint_stat())
                stat["count"] += 1
                stat["sum_ms"] += rt
                stat["min_ms"] = rt if stat["min_ms"] is None else min(stat["min_ms"], rt)
                stat["max_ms"] = rt if stat["max_ms"] is None else max(stat["max_ms"], rt)
                stat["reservoir"].add(rt)

    serializable_endpoint_stats = {
        ep: {
            "count": s["count"],
            "sum_ms": s["sum_ms"],
            "min_ms": s["min_ms"],
            "max_ms": s["max_ms"],
            "reservoir": s["reservoir"].to_dict(),
        }
        for ep, s in endpoint_stats.items()
    }

    return {
        "total_lines": total_lines,
        "parse_errors": parse_errors,
        "level_counts": dict(level_counts),
        "status_class_counts": dict(status_class_counts),
        "endpoint_counts": dict(endpoint_counts),
        "method_counts": dict(method_counts),
        "endpoint_stats": serializable_endpoint_stats,
    }


def map_file_range(file_path, start_offset, end_offset, config=None):
    """
    Reads exactly the byte range [start_offset, end_offset) from disk and
    runs map_chunk on it. Used by local multiprocessing workers so the
    raw file is never fully duplicated into worker argument lists --
    each process seeks and reads only its own slice.
    """
    with open(file_path, "rb") as f:
        f.seek(start_offset)
        data = f.read(end_offset - start_offset)
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return map_chunk(lines, config)
