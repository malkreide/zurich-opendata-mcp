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

Exit code 0 on a completed handshake with a non-empty tool list, 1 otherwise.
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

            tools = await session.list_tools()
            print(f"tools    : {len(tools.tools)}")
            if not tools.tools:
                print("FAIL: server started but advertises no tools", file=sys.stderr)
                return 1

    print("OK: installed artifact starts and completes an MCP handshake")
    # TEMPORARY (reverted in the next commit): forced failure to determine
    # whether `Fresh-resolve install smoke` is actually a *required* check.
    print("TEMP: forcing a non-zero exit to test the merge gate")
    return 1


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
