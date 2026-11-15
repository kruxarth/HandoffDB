"""Allow-list HTTPS proxy for the Level 2 sandbox.

The sandboxed agent runs with no network of its own (bwrap --unshare-net).
Its only way out is this CONNECT proxy, reached through a unix socket bound
into the sandbox. Only the model provider's hosts are allowed, so the agent
cannot search the web or download the upstream fix. Every request is logged.

  python scripts/netproxy.py <unix-socket> <log.jsonl> [allowed-suffix ...]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

SOCK, LOG = sys.argv[1], sys.argv[2]
ALLOW = tuple(sys.argv[3:]) or ("opencode.ai", "models.dev")


def allowed(host: str) -> bool:
    return any(host == a or host.endswith("." + a) for a in ALLOW)


def log(**kw) -> None:
    with open(LOG, "a") as f:
        f.write(json.dumps({"t": round(time.time(), 3), **kw}) + "\n")


async def pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


async def handle(cr: asyncio.StreamReader, cw: asyncio.StreamWriter) -> None:
    try:
        head = await cr.readuntil(b"\r\n\r\n")
    except Exception:
        cw.close()
        return
    line = head.split(b"\r\n", 1)[0].decode("latin-1")
    parts = line.split()
    if len(parts) < 2 or parts[0] != "CONNECT":
        log(allowed=False, request=line[:200])
        cw.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        await cw.drain()
        cw.close()
        return
    host, _, port = parts[1].rpartition(":")
    ok = allowed(host) and port == "443"
    log(allowed=ok, host=host, port=port)
    if not ok:
        cw.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        await cw.drain()
        cw.close()
        return
    try:
        ur, uw = await asyncio.open_connection(host, int(port))
    except Exception as e:
        log(allowed=True, host=host, error=str(e)[:200])
        cw.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
        await cw.drain()
        cw.close()
        return
    cw.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await cw.drain()
    await asyncio.gather(pipe(cr, uw), pipe(ur, cw))


async def main() -> None:
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    srv = await asyncio.start_unix_server(handle, path=SOCK)
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
