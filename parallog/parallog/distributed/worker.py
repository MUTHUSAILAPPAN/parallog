"""
A Parallog worker node: a minimal HTTP service that exposes the MAP
phase so it can run inside its own container, independently from the
coordinator process. Start with `parallog serve-worker --port 5000`,
or via the provided Dockerfile.
"""


def create_app():
    try:
        from flask import Flask, request, jsonify
    except ImportError as e:
        raise RuntimeError(
            "The 'distributed' extra is required to run a worker. "
            "Install with: pip install parallog[distributed]"
        ) from e

    from ..mapper import map_chunk

    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/map")
    def map_endpoint():
        payload = request.get_json(force=True)
        lines = payload.get("lines", [])
        config = payload.get("config", {})
        result = map_chunk(lines, config)
        return jsonify({"result": result})

    return app


def serve(host="0.0.0.0", port=5000):
    app = create_app()
    app.run(host=host, port=port)
