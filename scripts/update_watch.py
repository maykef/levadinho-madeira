#!/usr/bin/env python3
"""Alarm for the site's status update (owner, 2026-11-08: the update failed on 7 and 8 Nov and nobody knew).
Reads the latest run of the GitHub Action "Update trail status" (update.yml). Exit 2 (red dot on the dashboard's Data
collection tab) when it failed, with its time and a link; exit 0 when it succeeded or is still running.
"""
import json
import subprocess
import sys

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
r = subprocess.run(["gh", "run", "list", "--workflow", "update.yml", "-L", "1", "--json",
                    "conclusion,status,createdAt,event,url"], cwd=ROOT, capture_output=True, text=True, timeout=60)
if r.returncode:
    sys.exit(f"gh run list failed: {r.stderr.strip()}")
run = json.loads(r.stdout)[0]
if run["status"] != "completed":
    print(f"update {run['status']} (started {run['createdAt']}, {run['event']})")
elif run["conclusion"] == "success":
    print(f"update ok ({run['createdAt']}, {run['event']})")
else:
    print(f"UPDATE FAILED ({run['conclusion']}) at {run['createdAt']} ({run['event']}): {run['url']}")
    sys.exit(2)
