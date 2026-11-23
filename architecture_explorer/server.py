"""Loopback HTTP server and JSON API."""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from .fixtures import MAX_QUERY, FixtureIndex
from .store import Conflict, NotFound, SchemaVersionError, Store, StorageError

BODY_CAP = 16384
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/tokens.css": ("tokens.css", "text/css; charset=utf-8"),
    "/static/app.css": ("app.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
ID_RE = re.compile(r"[0-9a-f]{32}")
PROJECT_FIELDS = ("title", "query", "selected")


class ApiError(Exception):
    def __init__(self, status, code, message, **extra):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra


def _has_control(s: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in s)


def _encodable(s: str) -> bool:
    try:
        s.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def validate_project(body: dict, index: FixtureIndex, *, update: bool):
    """Return (title, query, selected, version) or raise validation_error."""
    allowed = set(PROJECT_FIELDS) | ({"version"} if update else set())
    fields: dict[str, str] = {}
    for key in body:
        if key not in allowed:
            fields[key] = "unknown field"

    title = query = selected = version = None

    if "title" not in body:
        fields.setdefault("title", "required")
    else:
        t = body["title"]
        if not isinstance(t, str):
            fields["title"] = "must be a string"
        elif _has_control(t) or not _encodable(t):
            fields["title"] = "must not contain control characters"
        else:
            title = t.strip()
            if not 1 <= len(title) <= 120:
                fields["title"] = "must be 1 to 120 characters"
                title = None

    if "query" not in body:
        if update:
            fields.setdefault("query", "required")
        else:
            query = ""
    else:
        q = body["query"]
        if not isinstance(q, str):
            fields["query"] = "must be a string"
        elif _has_control(q) or not _encodable(q):
            fields["query"] = "must not contain control characters"
        elif len(q) > MAX_QUERY:
            fields["query"] = "must be at most 200 characters"
        else:
            query = q

    if "selected" not in body:
        if update:
            fields.setdefault("selected", "required")
    else:
        s = body["selected"]
        if s is None:
            selected = None
        elif not isinstance(s, dict):
            fields["selected"] = "must be null or an object with path and line"
        elif set(s) != {"path", "line"}:
            fields["selected"] = "must have exactly path and line"
        else:
            p, ln = s["path"], s["line"]
            if not isinstance(p, str) or not index.has(p):
                fields["selected"] = "path is not an indexed fixture file"
            elif isinstance(ln, bool) or not isinstance(ln, int):
                fields["selected"] = "line must be an integer"
            elif not 1 <= ln <= index.line_count(p):
                fields["selected"] = "line is out of range"
            else:
                selected = {"path": p, "line": ln}

    if update:
        if "version" not in body:
            fields.setdefault("version", "required")
        else:
            v = body["version"]
            if isinstance(v, bool) or not isinstance(v, int):
                fields["version"] = "must be an integer"
            elif not 1 <= v <= 2**62:
                fields["version"] = "out of range"
            else:
                version = v

    if fields:
        raise ApiError(400, "validation_error", "Invalid project data", fields=fields)
    return title, query, selected, version


class ExplorerServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR permits port hijacking; keep it off there.
    allow_reuse_address = os.name != "nt"

    def __init__(self, address, handler, store: Store, index: FixtureIndex):
        self.store = store
        self.index = index
        try:
            super().__init__(address, handler)
        except BaseException:
            store.close()
            raise
        self.port = self.server_address[1]

    def server_close(self) -> None:
        try:
            super().server_close()
        finally:
            self.store.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "ArchitectureExplorer/" + __version__
    sys_version = ""
    protocol_version = "HTTP/1.0"  # one request per connection: no body desync

    def log_message(self, format, *args):  # noqa: A002
        pass

    # -- dispatch ---------------------------------------------------------
    def do_GET(self): self._handle("GET")
    def do_POST(self): self._handle("POST")
    def do_PUT(self): self._handle("PUT")
    def do_DELETE(self): self._handle("DELETE")
    def do_PATCH(self): self._handle("PATCH")
    def do_HEAD(self): self._handle("HEAD")
    def do_OPTIONS(self): self._handle("OPTIONS")

    def _handle(self, method: str) -> None:
        self.close_connection = True
        try:
            self._dispatch(method)
        except ApiError as e:
            self._send_error(e)
        except (BrokenPipeError, ConnectionError):
            pass
        except Exception:
            try:
                self._send_error(
                    ApiError(500, "internal_error", "Internal server error")
                )
            except Exception:
                pass

    def _dispatch(self, method: str) -> None:
        port = self.server.port
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            raise ApiError(403, "forbidden_host", "Host not allowed")
        if method in ("POST", "PUT"):
            origin = self.headers.get("Origin")
            if origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
                raise ApiError(403, "forbidden_origin", "Origin not allowed")

        parts = urlsplit(self.path)
        path = parts.path
        if path in STATIC_FILES:
            self._require(method, ("GET",))
            return self._static(path)

        if path == "/api/v1/health":
            self._require(method, ("GET",))
            return self._json(200, {
                "status": "ok", "version": __version__,
                "fixture_files": len(self.server.index),
                "projects": self.server.store.count(),
            })
        if path == "/api/v1/fixtures/files":
            self._require(method, ("GET",))
            return self._json(200, {"files": self.server.index.listing()})
        if path == "/api/v1/fixtures/file":
            self._require(method, ("GET",))
            return self._fixture_file(parts.query)
        if path == "/api/v1/fixtures/search":
            self._require(method, ("GET",))
            return self._search(parts.query)
        if path == "/api/v1/projects":
            self._require(method, ("GET", "POST"))
            if method == "GET":
                return self._json(200, {"projects": self.server.store.list()})
            return self._create()
        prefix = "/api/v1/projects/"
        if path.startswith(prefix) and "/" not in path[len(prefix):]:
            self._require(method, ("GET", "PUT"))
            pid = unquote(path[len(prefix):])
            if method == "GET":
                if not ID_RE.fullmatch(pid):
                    raise ApiError(404, "not_found", "Not found")
                project = self.server.store.get(pid)
                if project is None:
                    raise ApiError(404, "not_found", "Not found")
                return self._json(200, project)
            return self._update(pid)
        raise ApiError(404, "not_found", "Not found")

    @staticmethod
    def _require(method: str, allowed: tuple) -> None:
        if method not in allowed:
            raise ApiError(
                405, "method_not_allowed", "Method not allowed",
                _headers={"Allow": ", ".join(allowed)},
            )

    # -- handlers ---------------------------------------------------------
    def _static(self, path: str) -> None:
        name, ctype = STATIC_FILES[path]
        try:
            data = (STATIC_DIR / name).read_bytes()
        except OSError:
            raise ApiError(404, "not_found", "Not found") from None
        headers = {"Content-Security-Policy": CSP} if name.endswith(".html") else {}
        self._send(200, data, ctype, headers)

    def _query_params(self, qs: str) -> dict:
        try:
            return parse_qs(qs, keep_blank_values=True, max_num_fields=20)
        except ValueError:
            raise ApiError(400, "bad_request", "Invalid query string") from None

    def _single(self, params: dict, name: str):
        vals = params.get(name)
        if not vals:
            raise ApiError(400, "bad_request", f"Missing query parameter '{name}'")
        if len(vals) != 1:
            raise ApiError(400, "bad_request", f"Repeated query parameter '{name}'")
        return vals[0]

    def _fixture_file(self, qs: str) -> None:
        path = self._single(self._query_params(qs), "path")
        lines = self.server.index.lines(path)
        if lines is None:
            raise ApiError(404, "not_found", "Not found")
        self._json(200, {"path": path, "lines": lines})

    def _search(self, qs: str) -> None:
        q = self._single(self._query_params(qs), "q")
        if len(q) > MAX_QUERY:
            raise ApiError(400, "bad_request", "Query must be at most 200 characters")
        results, truncated = self.server.index.search(q)
        self._json(200, {
            "query": q, "count": len(results),
            "truncated": truncated, "results": results,
        })

    def _discard(self, length: int) -> None:
        """Drain a modest oversize body without keeping it, so closing the
        socket does not reset the connection and lose the 413 response."""
        if length > 1 << 20:
            return
        try:
            self.connection.settimeout(2)
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
        except OSError:
            pass

    def _read_body(self) -> dict:
        ctype = (self.headers.get("Content-Type") or "").strip().lower()
        if not ctype.startswith("application/json"):
            raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
        if self.headers.get("Transfer-Encoding") is not None:
            raise ApiError(400, "bad_request", "Transfer-Encoding is not supported")
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            raise ApiError(411, "bad_request", "Content-Length required")
        raw_len = raw_len.strip()
        if not raw_len.isascii() or not raw_len.isdigit() or len(raw_len) > 9:
            raise ApiError(400, "bad_request", "Invalid Content-Length")
        length = int(raw_len)
        if length > BODY_CAP:
            self._discard(length)
            raise ApiError(413, "payload_too_large", "Request body too large")
        data = self.rfile.read(length) if length else b""
        if len(data) != length:
            raise ApiError(400, "bad_request", "Incomplete request body")
        try:
            body = json.loads(
                data.decode("utf-8"),
                parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)),
            )
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise ApiError(400, "bad_request", "Body must be valid UTF-8 JSON") from None
        if not isinstance(body, dict):
            raise ApiError(400, "bad_request", "Body must be a JSON object")
        return body

    def _create(self) -> None:
        body = self._read_body()
        title, query, selected, _ = validate_project(body, self.server.index, update=False)
        project = self.server.store.create(title, query, selected)
        self._json(201, project, {"Location": f"/api/v1/projects/{project['id']}"})

    def _update(self, pid: str) -> None:
        body = self._read_body()
        if not ID_RE.fullmatch(pid):
            raise ApiError(404, "not_found", "Not found")
        title, query, selected, version = validate_project(
            body, self.server.index, update=True
        )
        try:
            project = self.server.store.update(pid, version, title, query, selected)
        except NotFound:
            raise ApiError(404, "not_found", "Not found") from None
        except Conflict as c:
            raise ApiError(
                409, "conflict",
                "The project was changed elsewhere; load the latest version",
                _current=c.current,
            ) from None
        self._json(200, project)

    # -- responses --------------------------------------------------------
    def _json(self, status: int, payload: dict, headers: dict | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, data, "application/json; charset=utf-8", headers)

    def _send_error(self, e: ApiError) -> None:
        extra = dict(e.extra)
        headers = extra.pop("_headers", None)
        current = extra.pop("_current", None)
        err = {"code": e.code, "message": e.message}
        err.update(extra)
        payload = {"error": err}
        if current is not None:
            payload["current"] = current
        self._json(e.status, payload, headers)

    def _send(self, status: int, data: bytes, ctype: str, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)


def create_server(data_dir, port: int = 0) -> ExplorerServer:
    """Open storage, bind 127.0.0.1:<port>, and return the (unstarted) server."""
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer in 0..65535")
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    index = FixtureIndex()
    store = Store(str(data_dir / "explorer.sqlite3"))  # may raise SchemaVersionError
    return ExplorerServer(("127.0.0.1", port), Handler, store, index)


__all__ = ["create_server", "ExplorerServer", "SchemaVersionError", "StorageError"]
