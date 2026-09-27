import unittest

from parallog.parser import parse_line


class TestParser(unittest.TestCase):
    def test_json_line(self):
        line = '{"level": "ERROR", "endpoint": "/api/x", "status": 500, "response_time_ms": 120}'
        record = parse_line(line)
        self.assertEqual(record["level"], "ERROR")
        self.assertEqual(record["endpoint"], "/api/x")
        self.assertEqual(record["status"], 500)
        self.assertEqual(record["response_time_ms"], 120)

    def test_json_line_infers_level_from_status(self):
        line = '{"endpoint": "/api/y", "status": 503}'
        record = parse_line(line)
        self.assertEqual(record["level"], "ERROR")

    def test_clf_line(self):
        line = '127.0.0.1 - - [10/Oct/2023:13:55:36 -0700] "GET /api/users HTTP/1.1" 200 2326 45'
        record = parse_line(line)
        self.assertEqual(record["endpoint"], "/api/users")
        self.assertEqual(record["status"], 200)
        self.assertEqual(record["method"], "GET")
        self.assertEqual(record["response_time_ms"], 45.0)

    def test_generic_level_only_line(self):
        record = parse_line("2023-10-10 ERROR something broke without structure")
        self.assertEqual(record["level"], "ERROR")
        self.assertIsNone(record["endpoint"])

    def test_unparseable_line(self):
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   "))
        self.assertIsNone(parse_line("just some ordinary text"))


if __name__ == "__main__":
    unittest.main()
