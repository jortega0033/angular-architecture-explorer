"""Entry point: python -m architecture_explorer --data-dir DIR --port PORT"""

from __future__ import annotations

import argparse
import signal
import sys

from .server import create_server
from .store import SchemaVersionError


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer") from None
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be in 0..65535")
    return port


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="architecture_explorer")
    parser.add_argument("--data-dir", required=True, help="directory for explorer.sqlite3")
    parser.add_argument("--port", type=_port, default=8765, help="port (0 = ephemeral)")
    args = parser.parse_args(argv)

    try:
        server = create_server(args.data_dir, args.port)
    except SchemaVersionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: cannot start: {exc}", file=sys.stderr)
        return 1

    def _stop(signum, frame):
        raise KeyboardInterrupt

    for name in ("SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _stop)
            except (ValueError, OSError):
                pass

    try:
        print(f"Serving on http://127.0.0.1:{server.port}", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
