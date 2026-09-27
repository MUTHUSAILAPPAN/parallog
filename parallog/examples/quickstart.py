"""End-to-end example: generate sample data, run sequential vs.
multiprocessing, and print a report with the observed speedup."""

from parallog.log_generator import generate_log_file
from parallog.engine import run_sequential, run_multiprocessing
from parallog.report import build_report, format_report_table

LOG_PATH = "sample_logs.jsonl"

if __name__ == "__main__":
    print("Generating synthetic log file...")
    generate_log_file(LOG_PATH, n_lines=200_000, seed=7)

    print("Running sequential baseline...")
    seq = run_sequential(LOG_PATH)
    print(f"  sequential: {seq.elapsed_seconds:.3f}s")

    print("Running multiprocessing (4 workers)...")
    mp_result = run_multiprocessing(LOG_PATH, n_workers=4)
    print(f"  multiprocessing: {mp_result.elapsed_seconds:.3f}s "
          f"(speedup {seq.elapsed_seconds / mp_result.elapsed_seconds:.2f}x)")

    report = build_report(mp_result.result)
    print(format_report_table(report))
