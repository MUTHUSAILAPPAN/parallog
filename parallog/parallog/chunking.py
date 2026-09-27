"""
Splits a log file into byte-aligned chunks for parallel processing.

Rather than loading the whole file into memory and slicing a Python
list (which duplicates the file across process/network boundaries),
we compute line-aligned byte offsets up front. Each worker then reads
only its own [start, end) slice directly from disk (multiprocessing)
or has that slice shipped to it once (distributed).
"""

import os


def compute_line_aligned_offsets(file_path, n_chunks):
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return [(0, 0)]

    n_chunks = max(1, min(n_chunks, file_size))
    raw_boundaries = [int(file_size * i / n_chunks) for i in range(n_chunks + 1)]
    raw_boundaries[0] = 0
    raw_boundaries[-1] = file_size

    aligned = [0]
    with open(file_path, "rb") as f:
        for b in raw_boundaries[1:-1]:
            f.seek(b)
            f.readline()  # consume the partial line so we land on a boundary
            aligned.append(f.tell())
    aligned.append(file_size)

    offsets = []
    for i in range(len(aligned) - 1):
        start, end = aligned[i], aligned[i + 1]
        if end > start:
            offsets.append((start, end))
    return offsets or [(0, file_size)]


def read_chunk_lines(file_path, start, end):
    with open(file_path, "rb") as f:
        f.seek(start)
        data = f.read(end - start)
    return data.decode("utf-8", errors="replace").splitlines()
