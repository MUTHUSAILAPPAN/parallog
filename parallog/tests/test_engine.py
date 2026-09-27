import os
import tempfile
import unittest

from parallog.log_generator import generate_log_file
from parallog.engine import run_sequential, run_multiprocessing


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.tmpdir, "sample.log")
        generate_log_file(self.log_path, n_lines=2000, seed=42)

    def test_sequential_and_multiprocessing_agree(self):
        seq = run_sequential(self.log_path)
        mp_result = run_multiprocessing(self.log_path, n_workers=4)

        self.assertEqual(seq.result["total_lines"], mp_result.result["total_lines"])
        self.assertEqual(seq.result["level_counts"], mp_result.result["level_counts"])
        self.assertEqual(seq.result["endpoint_counts"], mp_result.result["endpoint_counts"])
        self.assertEqual(seq.result["parse_errors"], mp_result.result["parse_errors"])


if __name__ == "__main__":
    unittest.main()
