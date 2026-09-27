import unittest

from parallog.mapper import map_chunk
from parallog.reducer import reduce_all

LINES_A = [
    '{"level": "INFO", "endpoint": "/a", "status": 200, "response_time_ms": 10}',
    '{"level": "ERROR", "endpoint": "/b", "status": 500, "response_time_ms": 300}',
]
LINES_B = [
    '{"level": "INFO", "endpoint": "/a", "status": 200, "response_time_ms": 20}',
    'not a valid line',
]


class TestMapReduce(unittest.TestCase):
    def test_map_chunk_counts(self):
        result = map_chunk(LINES_A)
        self.assertEqual(result["total_lines"], 2)
        self.assertEqual(result["level_counts"]["ERROR"], 1)
        self.assertEqual(result["endpoint_counts"]["/a"], 1)

    def test_reduce_merges_correctly(self):
        pa = map_chunk(LINES_A)
        pb = map_chunk(LINES_B)
        merged = reduce_all([pa, pb])
        self.assertEqual(merged["total_lines"], 4)
        self.assertEqual(merged["parse_errors"], 1)
        self.assertEqual(merged["endpoint_counts"]["/a"], 2)
        self.assertEqual(merged["endpoint_stats"]["/a"]["count"], 2)
        self.assertAlmostEqual(merged["endpoint_stats"]["/a"]["sum_ms"], 30)

    def test_reduce_is_order_independent(self):
        pa = map_chunk(LINES_A)
        pb = map_chunk(LINES_B)
        merged1 = reduce_all([pa, pb])
        merged2 = reduce_all([pb, pa])
        self.assertEqual(merged1["total_lines"], merged2["total_lines"])
        self.assertEqual(merged1["endpoint_counts"], merged2["endpoint_counts"])


if __name__ == "__main__":
    unittest.main()
