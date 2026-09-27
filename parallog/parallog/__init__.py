"""
Parallog
========

A lightweight Python package for parallel and distributed log analytics
using the map-reduce paradigm.
"""

__version__ = "0.1.0"

from .engine import run_sequential, run_multiprocessing, run_distributed
from .report import build_report, format_report_table, save_report_json

__all__ = [
    "run_sequential",
    "run_multiprocessing",
    "run_distributed",
    "build_report",
    "format_report_table",
    "save_report_json",
]
