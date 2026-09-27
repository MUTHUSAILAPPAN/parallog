"""
Parsing layer: turns a single raw log line into a normalized dict, or
None if the line cannot be interpreted. Two formats are supported out
of the box:

  1. JSON Lines - one JSON object per line (recommended; used by
     `parallog generate-sample`), e.g.:
       {"level": "ERROR", "endpoint": "/api/x", "status": 500,
        "response_time_ms": 240}

  2. Combined/Common Log Format (Apache/Nginx style), optionally with
     a trailing response-time field, e.g.:
       127.0.0.1 - - [10/Oct/2023:13:55:36 -0700] "GET /api/x HTTP/1.1" 500 512 240

Lines that match neither format but still contain a recognizable log
level keyword are recorded with that level only (endpoint/status/
response time left blank). Anything else is treated as a parse error
by the mapper.
"""

import json
import re

CLF_PATTERN = re.compile(
    r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<endpoint>\S+)\s+\S+"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)(?:\s+(?P<response_time>[\d.]+))?'
)

LEVEL_PATTERN = re.compile(r'\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b', re.IGNORECASE)

_LEVEL_ALIASES = {
    "WARNING": "WARN",
}

_JSON_KEY_ALIASES = {
    "level": ["level", "lvl", "severity", "loglevel"],
    "endpoint": ["endpoint", "path", "url", "route"],
    "status": ["status", "status_code", "http_status", "code"],
    "response_time_ms": ["response_time_ms", "response_time", "latency_ms", "duration_ms", "elapsed_ms"],
    "method": ["method", "http_method", "verb"],
    "timestamp": ["timestamp", "time", "ts"],
    "message": ["message", "msg"],
}


def _first_present(d, keys):
    for k in keys:
        if k in d:
            return d[k]
    return None


def _normalize_level(level):
    if level is None:
        return None
    level = str(level).upper()
    return _LEVEL_ALIASES.get(level, level)


def _normalize_json_record(d):
    record = {}
    for field, aliases in _JSON_KEY_ALIASES.items():
        record[field] = _first_present(d, aliases)
    record["level"] = _normalize_level(record["level"])
    return record


def _status_to_level(status):
    try:
        status = int(status)
    except (TypeError, ValueError):
        return None
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARN"
    return "INFO"


def _parse_json_line(line):
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    record = _normalize_json_record(data)
    if record["level"] is None:
        record["level"] = _status_to_level(record["status"]) or "INFO"
    return record


def _parse_clf_line(line):
    m = CLF_PATTERN.match(line)
    if not m:
        return None
    status = int(m.group("status"))
    return {
        "timestamp": m.group("timestamp"),
        "method": m.group("method"),
        "endpoint": m.group("endpoint"),
        "status": status,
        "response_time_ms": float(m.group("response_time")) if m.group("response_time") else None,
        "level": _status_to_level(status),
        "message": None,
    }


def _parse_generic_line(line):
    m = LEVEL_PATTERN.search(line)
    if not m:
        return None
    return {
        "timestamp": None,
        "method": None,
        "endpoint": None,
        "status": None,
        "response_time_ms": None,
        "level": _normalize_level(m.group(1)),
        "message": line,
    }


def parse_line(line):
    if line is None:
        return None
    line = line.strip()
    if not line:
        return None

    if line[0] in "{[":
        record = _parse_json_line(line)
        if record is not None:
            return record

    record = _parse_clf_line(line)
    if record is not None:
        return record

    return _parse_generic_line(line)
