#!/usr/bin/env python3
"""Levadinho MCP server: the knowledge tools in kbtools.py, read-only, over MCP streamable HTTP (or stdio).

  backend/.venv/bin/python backend/mcp_server.py              # http://127.0.0.1:5040/mcp
  backend/.venv/bin/python backend/mcp_server.py --stdio      # for local MCP clients
  MCP_HOST / MCP_PORT / MCP_ALLOWED_HOSTS (comma-separated, for the public Funnel host) override the defaults.

It connects to levadinho-db as kb_reader (read-only, kb schema only). Every call is logged to stderr: tool name and
arguments, nothing about the caller.
"""
import functools
import logging
import os
import sys
import time

import uvicorn

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbtools  # noqa: E402

log = logging.getLogger("levadinho.mcp")

INSTRUCTIONS = """Levadinho: sourced, free answers about Madeira's official PR walking trails (status today from \
IFCN's official warnings list, fees, booking rules, buses, taxis, weather) and, as it grows, places around Funchal.
Every result carries its source; cite it. Answer only from tool results: if no tool has the answer, say Levadinho \
doesn't know. Status comes from IFCN's warnings list, which IFCN does not update every day. Fees are exact; \
never round or estimate them. Website: https://levadinho-madeira.com"""

mcp = MCPServer(name="levadinho", title="Levadinho: Madeira trails", instructions=INSTRUCTIONS,
                website_url="https://levadinho-madeira.com", version="0.1.0")
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


def _wrap(fn):
    @functools.wraps(fn)
    def tool(*args, **kwargs):
        t = time.monotonic()
        try:
            return fn(*args, **kwargs)
        except ValueError as e:  # bad input (unknown trail, bad day…): the caller can correct it
            raise ToolError(str(e)) from e
        finally:
            log.info("%s %s %.0f ms", fn.__name__, kwargs, (time.monotonic() - t) * 1000)
    return tool


for f in kbtools.TOOLS:
    mcp.tool(annotations=READ_ONLY)(_wrap(f))


def main():
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)
    log.propagate = False
    if "--stdio" in sys.argv:
        mcp.run("stdio")
        return
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "5040"))
    allowed = [h for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h]
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                         allowed_hosts=[f"127.0.0.1:{port}", f"localhost:{port}"] + allowed,
                                         allowed_origins=[])
    app = mcp.streamable_http_app(stateless_http=True, json_response=True, transport_security=security, host=host)
    # access_log=False: uvicorn's access log would record callers' IP addresses
    uvicorn.run(app, host=host, port=port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
