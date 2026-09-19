#!/usr/bin/env python3
"""Start the *installed* server and complete a real MCP handshake.

Why this exists, and why importing is not enough:

`0.5.1` shipped with an uncapped `mcp[cli]>=1.28.1`. When `mcp` 2.0.0 removed
`mcp.server.fastmcp`, every fresh `pip install` produced a wheel that died at
import — while CI stayed green, because `uv sync` resolves from `uv.lock` and
the lock still pinned 1.28.1. A frozen resolve cannot observe what a free
resolve does. Nothing in the repo ever ran the artifact a user downloads.

So this script deliberately does what the test suite cannot: it drives the
console entry point as a subprocess over stdio, exactly as an MCP client would,
and asserts the server answers `initialize` and lists tools. Run it against a
venv that was populated by a *free* resolve with `--no-cache-dir` — a warm
wheel cache would re-measure the old artifact, which is the other half of how
this defect stayed invisible.

Usage:
    python scripts/smoke_installed.py <path-to-zurich-opendata-mcp-executable>

Exit code 0 on a completed handshake with a real version and a non-empty
tool list, 1 otherwise.
The `mcp` client used here ships with the package's own dependency, so no
extra install is needed in the target venv.
"""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def handshake(executable: str) -> int:
    params = StdioServerParameters(command=executable, args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            # mcp 2.x snake_cased the model fields; the camelCase names survive
            # only as pydantic serialisation aliases, so attribute access must
            # use the snake_case form.
            print(f"protocol : {init.protocol_version}")
            print(f"server   : {init.server_info.name}")
            print(f"version  : {init.server_info.version!r}")

            # Spec 2026-07-28 stamps `serverInfo` into every result, so an
            # empty version is not a cosmetic blemish but a missing answer on
            # every single response. It can only go wrong in an *installed*
            # venv: `config.PACKAGE_VERSION` reads the distribution metadata
            # and falls back to `0.0.0+local` when that read fails. The test
            # suite runs from an editable install where the read always
            # succeeds, so this is the one place the fallback can surface.
            if not init.server_info.version or init.server_info.version.endswith("+local"):
                print(
                    f"FAIL: installed artifact reports version "
                    f"{init.server_info.version!r} — the distribution metadata "
                    "was not readable, so every result would carry a useless "
                    "serverInfo stamp",
                    file=sys.stderr,
                )
                return 1

            tools = await session.list_tools()
            print(f"tools    : {len(tools.tools)}")
            if not tools.tools:
                print("FAIL: server started but advertises no tools", file=sys.stderr)
                return 1

    print("OK: installed artifact starts and completes an MCP handshake")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        return asyncio.run(handshake(sys.argv[1]))
    except Exception as exc:  # noqa: BLE001 - the failure itself is the signal
        # A broken artifact dies inside the subprocess; the client only sees
        # the stream close, so what surfaces here is an opaque wrapped
        # exception. The real cause is the server's own traceback, which the
        # child inherits stderr for and prints above this line — say so,
        # rather than leaving a reader to trust a message that names nothing.
        print(
            f"FAIL: the installed server did not complete a handshake "
            f"({type(exc).__name__}: {exc}).\n"
            f"      The server's own traceback above this line is the actual "
            f"cause; a broken dependency range shows up there as "
            f"ModuleNotFoundError.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
