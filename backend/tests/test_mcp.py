"""End-to-end test of the MCP server over streamable HTTP: starts it on a spare port, lists the tools, calls each one,
checks errors and the Host-header guard. Needs levadinho-db with the kb schema loaded.

  backend/.venv/bin/python backend/tests/test_mcp.py
"""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from mcp.client import Client

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "mcp_server.py")
PORT = 5041
URL = f"http://127.0.0.1:{PORT}/mcp"
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def data(res):
    if res.structured_content is not None:
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


CALLS = [
    ("trail_status", {"code": "pr 1"}, lambda d: d["code"] == "PR1" and d["status"] in ("OPEN", "PARTIAL", "CLOSED") and d["source"]["url"]),
    ("trail_status", {}, lambda d: sum(d["counts"].values()) == len(d["trails"]) >= 30),
    ("trail_facts", {"code": "caldeirao verde", "lang": "pt"}, lambda d: d["code"] == "PR9" and "/pt/" in d["page"]),
    ("find_trails", {"no_vertigo": True}, lambda d: all(t["exposure"] == "low" and t["status"] == "OPEN" for t in d["trails"])),
    ("fees_and_rules", {"topic": "fees"}, lambda d: any(f["item"] == "pr1_full" and f["eur"] == 10.5 for f in d["fees"])),
    ("bus", {"trail": "PR8", "day": "sat"}, lambda d: len(d["trips"]) > 5 and all(t["days"] in ("daily", "sat", "sat_sun", "sat_sun_hol") for t in d["trips"])),
    ("transport", {"trail": "PR1.2"}, lambda d: any(t["name"] == "Táxis Santana" for t in d["taxis"])),
    ("weather_now", {"region": "summit"}, lambda d: len(d["readings"]) >= 1),
    ("forecast_tomorrow", {"trail": "PR1"}, lambda d: "note" in d),
    ("closures", {}, lambda d: "not_open_now" in d and "changes" in d),
    ("places", {"category": "viewpoint"}, lambda d: "places" in d),
    ("notices", {}, lambda d: "notices" in d),
    ("search", {"text": "refund if it rains", "lang": "en"}, lambda d: len(d["results"]) >= 1),
]


async def main():
    async with Client(URL) as c:
        tools = (await c.list_tools()).tools
        names = {t.name for t in tools}
        check(len(tools) == 13, f"13 tools listed ({sorted(names)})")
        check(all(t.annotations and t.annotations.read_only_hint for t in tools), "every tool is annotated read-only")
        check(bool(c.instructions), "server instructions present")
        for name, args, test in CALLS:
            res = await c.call_tool(name, args)
            try:
                ok = not res.is_error and bool(test(data(res)))
            except Exception as e:  # noqa: BLE001
                ok = False
                print("     ", e, str(res)[:300])
            check(ok, f"{name}({args})")
        res = await c.call_tool("trail_facts", {"code": "PR99"})
        check(res.is_error and "Unknown trail" in res.content[0].text, "unknown trail → readable tool error")
        res = await c.call_tool("bus", {})
        check(res.is_error, "bus without arguments → tool error")


def host_guard():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Host": "evil.example", "Content-Type": "application/json",
                                                          "Accept": "application/json, text/event-stream"})
    try:
        urllib.request.urlopen(req, timeout=5)
        check(False, "foreign Host header rejected")
    except urllib.error.HTTPError as e:
        check(e.code in (403, 421), f"foreign Host header rejected (HTTP {e.code})")


if __name__ == "__main__":
    env = dict(os.environ, MCP_PORT=str(PORT))
    p = subprocess.Popen([sys.executable, SERVER], env=env, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            except urllib.error.HTTPError:
                break
            except OSError:
                time.sleep(0.2)
        asyncio.run(main())
        host_guard()
    finally:
        p.terminate()
        err = p.communicate(timeout=10)[1]
        calls = [l for l in err.splitlines() if "levadinho.mcp" in l]
        check(len(calls) >= len(CALLS), f"calls logged ({len(calls)})")
    print(f"\n{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)
