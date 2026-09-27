"""
Benchmarking utilities: run sequential, multiprocessing, and (optionally)
distributed execution over the same file and compare wall-clock time,
producing measurable evidence of the speedup from parallelization.
"""

import json

from .engine import run_sequential, run_multiprocessing, run_distributed


def run_benchmark(file_path, worker_counts=(2, 4), worker_urls=None, config=None):
    runs = [run_sequential(file_path, config)]

    for n in worker_counts:
        runs.append(run_multiprocessing(file_path, n_workers=n, config=config))

    if worker_urls:
        runs.append(run_distributed(file_path, worker_urls, config=config))

    baseline = runs[0].elapsed_seconds or 1e-9
    comparison = []
    for r in runs:
        comparison.append({
            "mode": r.mode,
            "workers": r.workers,
            "elapsed_seconds": round(r.elapsed_seconds, 4),
            "speedup_vs_sequential": round(baseline / r.elapsed_seconds, 2) if r.elapsed_seconds else None,
            "total_lines": r.result["total_lines"],
        })
    return comparison


def format_benchmark_table(comparison):
    lines = []
    header = f"{'MODE':<16}{'WORKERS':>9}{'TIME (s)':>12}{'SPEEDUP':>10}{'LINES':>12}"
    lines.append(header)
    lines.append("-" * len(header))
    for row in comparison:
        speedup = row["speedup_vs_sequential"]
        speedup_str = f"{speedup:.2f}x" if speedup is not None else "-"
        lines.append(
            f"{row['mode']:<16}{row['workers']:>9}{row['elapsed_seconds']:>12.4f}"
            f"{speedup_str:>10}{row['total_lines']:>12}"
        )
    return "\n".join(lines)


def save_benchmark_json(comparison, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)


def plot_benchmark(comparison, output_path="benchmark.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError(
            "The 'benchmark' extra is required for plotting. "
            "Install with: pip install parallog[benchmark]"
        ) from e

    labels = [f"{r['mode']}\n({r['workers']}w)" for r in comparison]
    times = [r["elapsed_seconds"] for r in comparison]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, times, color="#4C72B0")
    ax.set_ylabel("Elapsed time (seconds)")
    ax.set_title("Parallog execution time by mode")
    for bar, r in zip(bars, comparison):
        if r["speedup_vs_sequential"] is not None:
            ax.annotate(
                f"{r['speedup_vs_sequential']:.2f}x",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
