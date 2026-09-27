import os
import tempfile
import unittest

from parallog.chunking import compute_line_aligned_offsets, read_chunk_lines


class TestChunking(unittest.TestCase):
    def test_offsets_cover_whole_file_without_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.txt")
            lines = [f"line-{i}" for i in range(500)]
            with open(path, "w") as f:
                f.write("\n".join(lines) + "\n")

            offsets = compute_line_aligned_offsets(path, 5)
            recovered = []
            for s, e in offsets:
                recovered.extend(read_chunk_lines(path, s, e))

            self.assertEqual(recovered, lines)


if __name__ == "__main__":
    unittest.main()
