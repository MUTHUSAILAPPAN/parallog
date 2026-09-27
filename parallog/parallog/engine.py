"""
Execution engine: three ways to run the same map-reduce job.

  - run_sequential        baseline, single process
  - run_multiprocessing   local parallelism via multiprocessing.Pool
  - run_distributed       remote parallelism over HTTP across
                           containerized worker nodes
"""

import multiprocessing as mp
import time
from concurrent.futures import ThreadPoolExecutor

from .mapper import map_chunk, map_file_range
from .reducer import reduce_all
from .chunking import compute_line_aligned_offsets, read_chunk_lines


class ExecutionResult:
    def __init__(self, mode, result, elapsed_seconds, workers):
        self.mode = mode
        self.result = result
        self.elapsed_seconds = elapsed_seconds
        self.workers = workers

    def to_dict(self):
        return {
            "mode": self.mode,
            "workers": self.workers,
            "elapsed_seconds": self.elapsed_seconds,
            "result": self.result,
        }


def run_sequential(file_path, config=None):
    """Baseline: parse and map the entire file in a single process."""
    start = time.perf_counter()
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    partial = map_chunk(lines, config)
    result = reduce_all([partial])
    elapsed = time.perf_counter() - start
    return ExecutionResult("sequential", result, elapsed, 1)


def run_multiprocessing(file_path, n_workers=None, config=None):
    """Splits the file into byte-aligned chunks and processes them
    concurrently across local CPU cores using multiprocessing.Pool."""
    n_workers = n_workers or mp.cpu_count()
    start = time.perf_counter()

    offsets = compute_line_aligned_offsets(file_path, n_workers)
    tasks = [(file_path, s, e, config) for s, e in offsets]

    with mp.Pool(processes=min(n_workers, len(tasks))) as pool:
        partials = pool.starmap(map_file_range, tasks)

    result = reduce_all(partials)
    elapsed = time.perf_counter() - start
    return ExecutionResult("multiprocessing", result, elapsed, len(tasks))


def run_distributed(file_path, worker_urls, config=None, timeout=30):
    """
    Splits the file into one chunk per worker node and dispatches each
    chunk over HTTP, in parallel, to a `parallog serve-worker` instance
    (e.g. one running in each of several Docker containers), simulating
    a multi-node cluster. Requires the `distributed` extra (requests).
    """
    try:
        import requests
    except ImportError as e:
        raise RuntimeError(
            "The 'distributed' extra is required for run_distributed(). "
            "Install with: pip install parallog[distributed]"
        ) from e

    if not worker_urls:
        raise ValueError("run_distributed() requires at least one worker URL")

    start = time.perf_counter()
    offsets = compute_line_aligned_offsets(file_path, len(worker_urls))
    jobs = list(zip(offsets, worker_urls))

    def dispatch(job):
        (s, e), url = job
        lines = read_chunk_lines(file_path, s, e)
        resp = requests.post(
            url.rstrip("/") + "/map",
            json={"lines": lines, "config": config or {}},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["result"]

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        partials = list(pool.map(dispatch, jobs))

    result = reduce_all(partials)
    elapsed = time.perf_counter() - start
    return ExecutionResult("distributed", result, elapsed, len(jobs))
