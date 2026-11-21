"""Entry-point test: python -m architecture_explorer, restart on the same data dir. AE-C16/AE-C18."""
import json
import subprocess
import sys
import tempfile
import unittest
import http.client
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def start(data_dir):
    proc = subprocess.Popen(
        [sys.executable, "-m", "architecture_explorer", "--data-dir", str(data_dir), "--port", "0"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = proc.stdout.readline().strip()
    prefix = "Serving on http://127.0.0.1:"
    if not line.startswith(prefix):
        proc.kill()
        raise AssertionError(f"unexpected startup output: {line!r} {proc.stderr.read()!r}")
    return proc, int(line[len(prefix):])


def call(port, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body)
        headers = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"}
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    out = json.loads(resp.read())
    conn.close()
    return resp.status, out


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    proc.stdout.close()
    proc.stderr.close()


class CliRestart(unittest.TestCase):
    def test_process_restart_preserves_exploration(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "nested" / "data"
            proc, port = start(data)
            try:
                status, p = call(port, "POST", "/api/v1/projects", {
                    "title": "Jobs tour", "query": "JobCardComponent",
                    "selected": {"path": "src/app/jobs.ts", "line": 2}})
                self.assertEqual(status, 201)
            finally:
                stop(proc)
            proc, port = start(data)
            try:
                status, again = call(port, "GET", "/api/v1/projects/" + p["id"])
                self.assertEqual((status, again), (200, p))
            finally:
                stop(proc)

    def test_invalid_port_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-m", "architecture_explorer", "--data-dir", tmp, "--port", "70000"],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
