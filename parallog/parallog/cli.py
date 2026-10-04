"""Command-line interface for Parallog."""

import json
import sys

from .engine import run_sequential, run_multiprocessing, run_distributed
from .report import build_report, format_report_table, save_report_json
from .benchmark import run_benchmark, format_benchmark_table, save_benchmark_json, plot_benchmark
from .log_generator import generate_log_file


def cmd_run(args):
    if args.mode == "sequential":
        exec_result = run_sequential(args.input)
    elif args.mode == "multiprocessing":
        exec_result = run_multiprocessing(args.input, n_workers=args.workers)
    elif args.mode == "distributed":
        urls = [u.strip() for u in args.worker_urls.split(",")] if args.worker_urls else []
        exec_result = run_distributed(args.input, urls)
    else:
        raise ValueError(f"Unknown mode: {args.mode}")

    report = build_report(exec_result.result, top_n=args.top)
    print(f"[{exec_result.mode}] workers={exec_result.workers} "
          f"elapsed={exec_result.elapsed_seconds:.4f}s\n")

    if args.format == "table":
        print(format_report_table(report))
    elif args.format == "json":
        print(json.dumps(report, indent=2))

    if args.output:
        save_report_json(report, args.output)
        print(f"\nSaved JSON report to {args.output}")


def cmd_benchmark(args):
    worker_counts = [int(w) for w in args.workers_list.split(",")] if args.workers_list else [2, 4]
    urls = [u.strip() for u in args.worker_urls.split(",")] if args.worker_urls else None

    comparison = run_benchmark(args.input, worker_counts=worker_counts, worker_urls=urls)
    print(format_benchmark_table(comparison))

    if args.output:
        save_benchmark_json(comparison, args.output)
        print(f"\nSaved benchmark JSON to {args.output}")
    if args.chart:
        path = plot_benchmark(comparison, args.chart)
        print(f"Saved chart to {path}")


def cmd_generate_sample(args):
    generate_log_file(args.output, n_lines=args.lines, seed=args.seed)
    print(f"Wrote {args.lines} synthetic log lines to {args.output}")


def cmd_serve_worker(args):
    from .distributed.worker import serve
    print(f"Starting Parallog worker on {args.host}:{args.port}")
    serve(host=args.host, port=args.port)


def cmd_dashboard(args):
    from .ui import serve_dashboard
    serve_dashboard(host=args.host, port=args.port)


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="parallog", description="Map-reduce log analytics.")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Analyze a log file.")
    run_p.add_argument("input", help="Path to the log file.")
    run_p.add_argument("--mode", choices=["sequential", "multiprocessing", "distributed"], default="multiprocessing")
    run_p.add_argument("--workers", type=int, default=None, help="Worker processes (multiprocessing mode).")
    run_p.add_argument("--worker-urls", type=str, default=None, help="Comma-separated worker node URLs (distributed mode).")
    run_p.add_argument("--format", choices=["table", "json", "none"], default="table")
    run_p.add_argument("--output", type=str, default=None, help="Save JSON report to this path.")
    run_p.add_argument("--top", type=int, default=10)
    run_p.set_defaults(func=cmd_run)

    bench_p = sub.add_parser("benchmark", help="Compare sequential / multiprocessing / distributed performance.")
    bench_p.add_argument("input", help="Path to the log file.")
    bench_p.add_argument("--workers-list", type=str, default="2,4", help="Comma-separated worker counts to test.")
    bench_p.add_argument("--worker-urls", type=str, default=None, help="Comma-separated worker node URLs to include a distributed run.")
    bench_p.add_argument("--output", type=str, default=None)
    bench_p.add_argument("--chart", type=str, default=None, help="Save a PNG bar chart to this path.")
    bench_p.set_defaults(func=cmd_benchmark)

    gen_p = sub.add_parser("generate-sample", help="Generate a synthetic log file.")
    gen_p.add_argument("output", help="Path to write the sample log file.")
    gen_p.add_argument("--lines", type=int, default=100_000)
    gen_p.add_argument("--seed", type=int, default=None)
    gen_p.set_defaults(func=cmd_generate_sample)

    worker_p = sub.add_parser("serve-worker", help="Start a Parallog worker node (HTTP).")
    worker_p.add_argument("--host", type=str, default="0.0.0.0")
    worker_p.add_argument("--port", type=int, default=5000)
    worker_p.set_defaults(func=cmd_serve_worker)

    dashboard_p = sub.add_parser("dashboard", help="Open the local browser dashboard.")
    dashboard_p.add_argument("--host", type=str, default="127.0.0.1")
    dashboard_p.add_argument("--port", type=int, default=8000)
    dashboard_p.set_defaults(func=cmd_dashboard)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
