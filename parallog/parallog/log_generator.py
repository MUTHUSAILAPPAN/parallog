"""Generates synthetic JSON-lines log files, useful for testing and
for benchmarking without needing real production log data."""

import json
import random
import time

ENDPOINTS = [
    "/api/users", "/api/orders", "/api/products", "/api/login",
    "/api/checkout", "/api/search", "/api/reviews", "/api/inventory",
]
METHODS = ["GET", "POST", "PUT", "DELETE"]
LEVEL_WEIGHTS = [("INFO", 82), ("WARN", 12), ("ERROR", 5), ("DEBUG", 1)]
STATUS_BY_LEVEL = {
    "INFO": [200, 200, 201, 204],
    "WARN": [400, 404, 429],
    "ERROR": [500, 502, 503],
    "DEBUG": [200],
}


def _weighted_choice(weighted):
    total = sum(w for _, w in weighted)
    r = random.uniform(0, total)
    upto = 0
    for item, w in weighted:
        upto += w
        if upto >= r:
            return item
    return weighted[-1][0]


def generate_log_file(path, n_lines=100_000, seed=None):
    if seed is not None:
        random.seed(seed)
    start_ts = time.time() - n_lines
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n_lines):
            level = _weighted_choice(LEVEL_WEIGHTS)
            status = random.choice(STATUS_BY_LEVEL[level])
            base_latency = 20 if status < 400 else 150
            response_time_ms = round(max(1.0, random.gauss(base_latency, base_latency / 3)), 2)
            record = {
                "timestamp": start_ts + i,
                "level": level,
                "method": random.choice(METHODS),
                "endpoint": random.choice(ENDPOINTS),
                "status": status,
                "response_time_ms": response_time_ms,
                "message": f"{level} handling request #{i}",
            }
            f.write(json.dumps(record) + "\n")
