"""
The REDUCE phase.

reduce_two() combines two partial MAP results into one; it is
associative, so partial results from any number of chunks/nodes can be
folded together in any order (sequential fold, tree reduction, etc.)
and always produce the same final answer.
"""

from collections import Counter

from .stats import ReservoirSample


def _merge_endpoint_stats(a, b):
    merged = {}
    for ep in set(a) | set(b):
        sa, sb = a.get(ep), b.get(ep)
        if sa is None:
            merged[ep] = sb
            continue
        if sb is None:
            merged[ep] = sa
            continue

        res_a = ReservoirSample.from_dict(sa["reservoir"])
        res_b = ReservoirSample.from_dict(sb["reservoir"])
        merged_res = res_a.merge(res_b)

        min_vals = [v for v in (sa["min_ms"], sb["min_ms"]) if v is not None]
        max_vals = [v for v in (sa["max_ms"], sb["max_ms"]) if v is not None]

        merged[ep] = {
            "count": sa["count"] + sb["count"],
            "sum_ms": sa["sum_ms"] + sb["sum_ms"],
            "min_ms": min(min_vals) if min_vals else None,
            "max_ms": max(max_vals) if max_vals else None,
            "reservoir": merged_res.to_dict(),
        }
    return merged


def reduce_two(a, b):
    return {
        "total_lines": a["total_lines"] + b["total_lines"],
        "parse_errors": a["parse_errors"] + b["parse_errors"],
        "level_counts": dict(Counter(a["level_counts"]) + Counter(b["level_counts"])),
        "status_class_counts": dict(Counter(a["status_class_counts"]) + Counter(b["status_class_counts"])),
        "endpoint_counts": dict(Counter(a["endpoint_counts"]) + Counter(b["endpoint_counts"])),
        "method_counts": dict(Counter(a["method_counts"]) + Counter(b["method_counts"])),
        "endpoint_stats": _merge_endpoint_stats(a["endpoint_stats"], b["endpoint_stats"]),
    }


EMPTY_RESULT = {
    "total_lines": 0,
    "parse_errors": 0,
    "level_counts": {},
    "status_class_counts": {},
    "endpoint_counts": {},
    "method_counts": {},
    "endpoint_stats": {},
}


def reduce_all(partial_results):
    result = EMPTY_RESULT
    for partial in partial_results:
        result = reduce_two(result, partial)
    return result
