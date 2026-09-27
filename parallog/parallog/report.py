"""
Turns a reduced map-reduce result into a human/report-friendly form:
summary stats, top endpoints by traffic, and per-endpoint latency
percentiles (computed from the merged reservoir samples).
"""

import json

from .stats import percentile


def _endpoint_percentiles(stat):
    values = sorted(stat["reservoir"]["values"])
    return {
        "p50_ms": percentile(values, 50),
        "p90_ms": percentile(values, 90),
        "p99_ms": percentile(values, 99),
    }


def build_report(result, top_n=10):
    total = result["total_lines"] or 1
    errors = result["level_counts"].get("ERROR", 0) + result["level_counts"].get("CRITICAL", 0)

    top_endpoints = sorted(
        result["endpoint_counts"].items(), key=lambda kv: kv[1], reverse=True
    )[:top_n]

    endpoint_latency = []
    for ep, count in top_endpoints:
        stat = result["endpoint_stats"].get(ep)
        if not stat:
            continue
        avg_ms = stat["sum_ms"] / stat["count"] if stat["count"] else None
        pct = _endpoint_percentiles(stat)
        endpoint_latency.append({
            "endpoint": ep,
            "requests": count,
            "avg_ms": round(avg_ms, 2) if avg_ms is not None else None,
            "min_ms": stat["min_ms"],
            "max_ms": stat["max_ms"],
            **{k: (round(v, 2) if v is not None else None) for k, v in pct.items()},
        })

    return {
        "summary": {
            "total_lines": result["total_lines"],
            "parse_errors": result["parse_errors"],
            "parse_error_rate": round(result["parse_errors"] / total, 4),
            "error_rate": round(errors / total, 4),
        },
        "level_counts": result["level_counts"],
        "status_class_counts": result["status_class_counts"],
        "method_counts": result["method_counts"],
        "top_endpoints": [{"endpoint": ep, "requests": c} for ep, c in top_endpoints],
        "endpoint_latency": endpoint_latency,
    }


def _fmt(v):
    return "-" if v is None else f"{v:.1f}"


def format_report_table(report):
    lines = []
    s = report["summary"]
    lines.append("=" * 60)
    lines.append("PARALLOG REPORT")
    lines.append("=" * 60)
    lines.append(f"Total lines processed : {s['total_lines']}")
    lines.append(f"Parse errors          : {s['parse_errors']} ({s['parse_error_rate']*100:.2f}%)")
    lines.append(f"Error rate            : {s['error_rate']*100:.2f}%")
    lines.append("")
    lines.append("Log level breakdown:")
    for level, count in sorted(report["level_counts"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {level:<10} {count}")
    lines.append("")
    lines.append("HTTP status class breakdown:")
    for cls, count in sorted(report["status_class_counts"].items()):
        lines.append(f"  {cls:<6} {count}")
    lines.append("")
    lines.append(f"Top {len(report['top_endpoints'])} endpoints by traffic:")
    lines.append(f"  {'ENDPOINT':<30}{'REQUESTS':>10}")
    for row in report["top_endpoints"]:
        lines.append(f"  {row['endpoint']:<30}{row['requests']:>10}")
    lines.append("")
    lines.append("Endpoint latency (ms):")
    lines.append(f"  {'ENDPOINT':<28}{'AVG':>8}{'P50':>8}{'P90':>8}{'P99':>8}{'MAX':>8}")
    for row in report["endpoint_latency"]:
        lines.append(
            f"  {row['endpoint']:<28}"
            f"{_fmt(row['avg_ms']):>8}{_fmt(row['p50_ms']):>8}"
            f"{_fmt(row['p90_ms']):>8}{_fmt(row['p99_ms']):>8}{_fmt(row['max_ms']):>8}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def save_report_json(report, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
