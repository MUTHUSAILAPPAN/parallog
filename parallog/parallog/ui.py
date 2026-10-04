"""Local HTTP dashboard for running Parallog analyses from a browser."""

import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .engine import run_distributed, run_multiprocessing, run_sequential
from .log_generator import generate_log_file
from .report import build_report


_MAX_REQUEST_BYTES = 50 * 1024 * 1024
_DASHBOARD = Path(__file__).with_name("dashboard.html")


class _DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/":
            try:
                content = _DASHBOARD.read_bytes()
            except OSError:
                self.send_error(500, "Dashboard assets are missing")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_error(404)

    def do_POST(self):
        route = urlparse(self.path).path
        if route == "/api/sample":
            self._create_sample()
            return
        if route != "/api/analyze":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > _MAX_REQUEST_BYTES:
                self._send_json({"error": "Upload must be between 1 byte and 50 MB."}, 413)
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            content = payload.get("content")
            if not isinstance(content, str) or not content.strip():
                self._send_json({"error": "The selected log file is empty."}, 400)
                return

            mode = payload.get("mode", "sequential")
            worker_count = int(payload.get("workers", 4))
            if not 1 <= worker_count <= 64:
                self._send_json({"error": "Worker count must be between 1 and 64."}, 400)
                return
            worker_urls = [url.strip() for url in payload.get("worker_urls", "").split(",") if url.strip()]

            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".log", delete=False) as log_file:
                    log_file.write(content)
                    temp_path = log_file.name
                if mode == "sequential":
                    result = run_sequential(temp_path)
                elif mode == "multiprocessing":
                    result = run_multiprocessing(temp_path, n_workers=worker_count)
                elif mode == "distributed":
                    if not worker_urls:
                        self._send_json({"error": "Add at least one distributed worker URL."}, 400)
                        return
                    result = run_distributed(temp_path, worker_urls)
                else:
                    self._send_json({"error": "Choose a supported execution mode."}, 400)
                    return
            finally:
                if temp_path is not None:
                    Path(temp_path).unlink(missing_ok=True)

            self._send_json({
                "filename": Path(payload.get("filename", "uploaded.log")).name,
                "mode": result.mode,
                "workers": result.workers,
                "elapsed_seconds": result.elapsed_seconds,
                "report": build_report(result.result),
            })
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, 400)
        except RuntimeError as error:
            self._send_json({"error": str(error)}, 400)
        except Exception:
            self._send_json({"error": "Analysis failed. Check the selected mode and worker configuration."}, 500)

    def _create_sample(self):
        temp_path = None
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024:
                self._send_json({"error": "Invalid sample size request."}, 400)
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            line_count = int(payload.get("lines", 1000))
            if not 1 <= line_count <= 50000:
                self._send_json({"error": "Sample size must be between 1 and 50,000 lines."}, 400)
                return

            with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as sample_file:
                temp_path = sample_file.name
            generate_log_file(temp_path, n_lines=line_count)
            content = Path(temp_path).read_text(encoding="utf-8")
            self._send_json({"filename": "sample_logs.jsonl", "content": content})
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, 400)
        except Exception:
            self._send_json({"error": "Could not generate the sample log."}, 500)
        finally:
            if temp_path is not None:
                Path(temp_path).unlink(missing_ok=True)

    def _send_json(self, payload, status=200):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format_string, *args):
        return


def serve_dashboard(host="127.0.0.1", port=8000):
    """Serve the local dashboard and its analysis API."""
    server = ThreadingHTTPServer((host, port), _DashboardHandler)
    print(f"Parallog dashboard running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Parallog dashboard.")
    finally:
        server.server_close()