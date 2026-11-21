"""Shared helpers: real loopback HTTP on ephemeral ports with disposable data."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from architecture_explorer.server import create_server


class Running:
    """A server on an ephemeral port serving one data directory."""

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.server = create_server(self.data_dir, port=0)
        self.port = self.server.port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.port}"

    def request(self, method, path, body=None, headers=None, raw=None, origin=True):
        hdrs = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        if method in ("POST", "PUT") and origin and "Origin" not in hdrs:
            hdrs["Origin"] = self.origin
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=data, headers=hdrs)
            resp = conn.getresponse()
            payload = resp.read()
            return resp.status, resp, payload
        finally:
            conn.close()

    def json(self, method, path, body=None, **kw):
        status, resp, payload = self.request(method, path, body, **kw)
        return status, (json.loads(payload) if payload else None)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=10)


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "data"
        self.srv = self.start()

    def start(self):
        running = Running(self.data_dir)
        self.addCleanup(lambda: running.stop() if running.thread.is_alive() else None)
        return running

    def restart(self):
        self.srv.stop()
        self.srv = self.start()
        return self.srv
