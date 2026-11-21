"""API tests. Check IDs (AE-C*) refer to docs/PRD.md."""
import json
import socket
from urllib.parse import quote

from tests.helpers import ServerTestCase


class HealthAndStatic(ServerTestCase):
    def test_health(self):  # AE-C01
        status, body = self.srv.json("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["fixture_files"], 4)

    def test_static_assets_and_csp(self):  # AE-C02
        status, resp, payload = self.srv.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", resp.getheader("Content-Type"))
        self.assertIn("script-src 'self'", resp.getheader("Content-Security-Policy"))
        self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")
        text = payload.decode("utf-8")
        for needle in ("Exploration title", "Search query", "Save exploration"):
            self.assertIn(needle, text)
        for path in ("/static/app.js", "/static/app.css"):
            self.assertEqual(self.srv.request("GET", path)[0], 200)
        self.assertEqual(self.srv.request("GET", "/static/../store.py")[0], 404)
        self.assertEqual(self.srv.request("GET", "/static/%2e%2e/store.py")[0], 404)

    def test_binds_loopback_only(self):  # AE-C03
        host, port = self.srv.server.server_address[:2]
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, self.srv.port)


class Guards(ServerTestCase):
    def test_bad_host_rejected(self):  # AE-C04
        for host in ("evil.example", f"127.0.0.1:{self.srv.port + 1}", "localhost"):
            status, resp, payload = self.srv.request(
                "GET", "/api/v1/health", headers={"Host": host})
            self.assertEqual(status, 403, host)
            self.assertEqual(json.loads(payload)["error"]["code"], "forbidden_host")

    def test_localhost_host_accepted(self):  # AE-C04
        status, _, _ = self.srv.request(
            "GET", "/api/v1/health", headers={"Host": f"localhost:{self.srv.port}"})
        self.assertEqual(status, 200)

    def test_write_origin_required_and_same_origin(self):  # AE-C05
        body = {"title": "t"}
        status, err = self.srv.json("POST", "/api/v1/projects", body, origin=False)
        self.assertEqual((status, err["error"]["code"]), (403, "forbidden_origin"))
        status, err = self.srv.json(
            "POST", "/api/v1/projects", body, headers={"Origin": "http://evil.example"})
        self.assertEqual((status, err["error"]["code"]), (403, "forbidden_origin"))
        status, _ = self.srv.json("POST", "/api/v1/projects", body)
        self.assertEqual(status, 201)

    def test_content_type_and_body_cap(self):  # AE-C06
        status, err = self.srv.json(
            "POST", "/api/v1/projects", raw=b'{"title":"t"}',
            headers={"Content-Type": "text/plain", "Origin": self.srv.origin})
        self.assertEqual((status, err["error"]["code"]), (415, "unsupported_media_type"))
        big = {"title": "t", "query": "x" * 20000}
        status, err = self.srv.json("POST", "/api/v1/projects", big)
        self.assertEqual((status, err["error"]["code"]), (413, "payload_too_large"))

    def test_malformed_json(self):  # AE-C06
        for raw in (b"{", b"[]", b"\xff\xfe"):
            status, err = self.srv.json(
                "POST", "/api/v1/projects", raw=raw,
                headers={"Content-Type": "application/json", "Origin": self.srv.origin})
            self.assertEqual((status, err["error"]["code"]), (400, "bad_request"), raw)

    def test_routes_and_methods(self):  # AE-C06
        self.assertEqual(self.srv.json("GET", "/api/v1/nope")[0], 404)
        status, resp, _ = self.srv.request("DELETE", "/api/v1/projects/" + "0" * 32)
        self.assertEqual(status, 405)

    def test_raw_oversize_content_length_not_read(self):  # AE-C06
        sock = socket.create_connection(("127.0.0.1", self.srv.port), timeout=10)
        try:
            sock.sendall((
                "POST /api/v1/projects HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.srv.port}\r\n"
                f"Origin: {self.srv.origin}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 99999999\r\nConnection: close\r\n\r\n").encode())
            self.assertIn(b" 413 ", sock.recv(4096).split(b"\r\n", 1)[0])
        finally:
            sock.close()


class Fixtures(ServerTestCase):
    def test_file_list(self):  # AE-C07
        _, body = self.srv.json("GET", "/api/v1/fixtures/files")
        self.assertEqual(body["files"], [
            {"path": "src/app/home.ts", "lines": 3},
            {"path": "src/app/jobs.ts", "lines": 5},
            {"path": "src/app/routes.ts", "lines": 5},
            {"path": "src/app/shared/widget.ts", "lines": 3},
        ])

    def test_seeded_unique_symbol(self):  # AE-C08
        _, body = self.srv.json("GET", "/api/v1/fixtures/search?q=JobCardComponent")
        self.assertEqual(body["results"], [{
            "path": "src/app/jobs.ts", "line": 2,
            "excerpt": "export class JobCardComponent {"}])
        self.assertEqual((body["count"], body["truncated"]), (1, False))

    def test_search_ordering_one_result_per_line(self):  # AE-C09
        _, body = self.srv.json("GET", "/api/v1/fixtures/search?q=Component")
        self.assertEqual([(r["path"], r["line"]) for r in body["results"]], [
            ("src/app/home.ts", 1), ("src/app/jobs.ts", 2),
            ("src/app/routes.ts", 1), ("src/app/routes.ts", 3)])
        _, body = self.srv.json("GET", "/api/v1/fixtures/search?q=Widget")
        self.assertEqual([(r["path"], r["line"]) for r in body["results"]], [
            ("src/app/jobs.ts", 1), ("src/app/jobs.ts", 3),
            ("src/app/shared/widget.ts", 1)])

    def test_search_is_literal_and_case_sensitive(self):  # AE-C10
        for q, count in (("jobcardcomponent", 0), (".*", 0), ("%", 0), ("", 0),
                         ("'", 7), ("() =>", 1)):
            _, body = self.srv.json(
                "GET", "/api/v1/fixtures/search?q=" + quote(q))
            self.assertEqual(body["count"], count, q)

    def test_search_query_limit(self):  # AE-C10
        status, err = self.srv.json("GET", "/api/v1/fixtures/search?q=" + "a" * 201)
        self.assertEqual((status, err["error"]["code"]), (400, "bad_request"))

    def test_file_read_and_traversal(self):  # AE-C11
        _, body = self.srv.json("GET", "/api/v1/fixtures/file?path=src/app/jobs.ts")
        self.assertEqual(body["lines"][1], "export class JobCardComponent {")
        for bad in ("../store.py", "/etc/passwd", "src\\app\\jobs.ts",
                    "src/app/missing.ts", "src/app/../app/jobs.ts"):
            status, _ = self.srv.json(
                "GET", "/api/v1/fixtures/file?path=" + quote(bad))
            self.assertEqual(status, 404, bad)
        self.assertEqual(self.srv.json("GET", "/api/v1/fixtures/file")[0], 400)


class Projects(ServerTestCase):
    SELECTED = {"path": "src/app/jobs.ts", "line": 2}

    def create(self, **over):
        body = {"title": "Jobs tour", "query": "JobCardComponent", "selected": self.SELECTED}
        body.update(over)
        return self.srv.json("POST", "/api/v1/projects", body)

    def test_create_get_list(self):  # AE-C12
        status, p = self.create()
        self.assertEqual(status, 201)
        self.assertEqual((p["version"], p["selected"]), (1, self.SELECTED))
        self.assertRegex(p["id"], r"^[0-9a-f]{32}$")
        self.assertEqual(self.srv.json("GET", "/api/v1/projects/" + p["id"])[1], p)
        _, listing = self.srv.json("GET", "/api/v1/projects")
        self.assertEqual([x["id"] for x in listing["projects"]], [p["id"]])

    def test_defaults(self):  # AE-C12
        status, p = self.srv.json("POST", "/api/v1/projects", {"title": "  Only title  "})
        self.assertEqual((status, p["title"], p["query"], p["selected"]),
                         (201, "Only title", "", None))

    def test_validation(self):  # AE-C13
        cases = [
            {"title": ""}, {"title": "   "}, {"title": "x" * 121}, {"title": 5},
            {"title": "a\x00b"}, {"query": "x"}, {"title": "t", "query": "x" * 201},
            {"title": "t", "query": "bad\nline"},
            {"title": "t", "selected": {"path": "src/app/jobs.ts", "line": 6}},
            {"title": "t", "selected": {"path": "src/app/jobs.ts", "line": 0}},
            {"title": "t", "selected": {"path": "../x.ts", "line": 1}},
            {"title": "t", "selected": {"path": "src/app/jobs.ts", "line": True}},
            {"title": "t", "selected": "src/app/jobs.ts"},
            {"title": "t", "extra": 1},
        ]
        for body in cases:
            status, err = self.srv.json("POST", "/api/v1/projects", body)
            self.assertEqual((status, err["error"]["code"]), (400, "validation_error"), body)
            self.assertTrue(err["error"]["fields"], body)
        self.assertEqual(self.srv.json("GET", "/api/v1/projects")[1]["projects"], [])

    def test_update_and_version_conflict(self):  # AE-C14
        _, p = self.create()
        upd = {"title": "Renamed", "query": "Widget", "selected": None, "version": 1}
        status, p2 = self.srv.json("PUT", "/api/v1/projects/" + p["id"], upd)
        self.assertEqual((status, p2["version"], p2["title"], p2["selected"]),
                         (200, 2, "Renamed", None))
        self.assertEqual(p2["created_at"], p["created_at"])
        status, err = self.srv.json("PUT", "/api/v1/projects/" + p["id"], upd)
        self.assertEqual((status, err["error"]["code"]), (409, "conflict"))
        self.assertEqual(err["current"], p2)
        for bad in ("1", True, None, 1.5):
            status, err = self.srv.json(
                "PUT", "/api/v1/projects/" + p["id"], dict(upd, version=bad))
            self.assertEqual((status, err["error"]["code"]), (400, "validation_error"), bad)
        self.assertEqual(self.srv.json("GET", "/api/v1/projects/" + p["id"])[1], p2)

    def test_missing_project(self):  # AE-C14
        for pid in ("0" * 32, "not-an-id", "%27%3B--"):
            self.assertEqual(self.srv.json("GET", "/api/v1/projects/" + pid)[0], 404)
        upd = {"title": "t", "query": "", "selected": None, "version": 1}
        self.assertEqual(self.srv.json("PUT", "/api/v1/projects/" + "0" * 32, upd)[0], 404)

    def test_hostile_text_stored_verbatim_and_json_escaped(self):  # AE-C15
        hostile = "<img src=x onerror=alert(1)>"
        _, p = self.create(title=hostile, query=hostile)
        status, resp, payload = self.srv.request("GET", "/api/v1/projects/" + p["id"])
        self.assertIn("application/json", resp.getheader("Content-Type"))
        self.assertEqual(json.loads(payload)["title"], hostile)
        self.assertEqual(self.srv.json("GET", "/api/v1/fixtures/search?q=" + "%3Cimg")[1]["count"], 0)

    def test_sql_metacharacters_are_data(self):  # AE-C15
        title = "x'); DROP TABLE projects;--"
        _, p = self.create(title=title)
        self.assertEqual(p["title"], title)
        self.assertEqual(len(self.srv.json("GET", "/api/v1/projects")[1]["projects"]), 1)

    def test_list_order_most_recent_first(self):  # AE-C12
        _, a = self.create(title="A")
        _, b = self.create(title="B")
        self.srv.json("PUT", "/api/v1/projects/" + a["id"],
                      {"title": "A2", "query": "", "selected": None, "version": 1})
        titles = [x["title"] for x in self.srv.json("GET", "/api/v1/projects")[1]["projects"]]
        self.assertEqual(titles, ["A2", "B"])


class Restart(ServerTestCase):
    def test_saved_exploration_survives_restart(self):  # AE-C16
        _, p = self.srv.json("POST", "/api/v1/projects", {
            "title": "Jobs tour", "query": "JobCardComponent",
            "selected": {"path": "src/app/jobs.ts", "line": 2}})
        _, p2 = self.srv.json("PUT", "/api/v1/projects/" + p["id"], {
            "title": "Jobs tour v2", "query": "  JobCardComponent ",
            "selected": {"path": "src/app/jobs.ts", "line": 2}, "version": 1})
        self.restart()
        _, again = self.srv.json("GET", "/api/v1/projects/" + p["id"])
        self.assertEqual(again, p2)
        self.assertEqual(again["query"], "  JobCardComponent ")
        _, hits = self.srv.json("GET", "/api/v1/fixtures/search?q=JobCardComponent")
        self.assertEqual((hits["results"][0]["path"], hits["results"][0]["line"]),
                         (again["selected"]["path"], again["selected"]["line"]))
        status, p3 = self.srv.json("PUT", "/api/v1/projects/" + p["id"], {
            "title": "after restart", "query": "", "selected": None, "version": 2})
        self.assertEqual((status, p3["version"]), (200, 3))

    def test_newer_schema_refused(self):  # AE-C17
        import sqlite3
        self.srv.stop()
        con = sqlite3.connect(self.data_dir / "explorer.sqlite3")
        con.execute("PRAGMA user_version = 99")
        con.commit()
        con.close()
        from architecture_explorer.server import create_server
        with self.assertRaises(Exception):
            create_server(self.data_dir, port=0)
