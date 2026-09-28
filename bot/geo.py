"""Distances and guide routes, shared by the bot (location replies) and the guide server.

Routes live in one folder each, built by build_route.py:
  routes/<id>/route.json          public (e.g. PR1)
  routes_private/<id>/route.json  git-ignored test routes (e.g. the owner's walk); served
                                  only with a valid guide token
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTE_DIRS = {False: os.path.join(HERE, "routes"), True: os.path.join(HERE, "routes_private")}


def distance_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def route_dir(rid):
    """(folder, is_private) for a route id, or (None, None) if it doesn't exist."""
    for private, base in ROUTE_DIRS.items():
        d = os.path.join(base, rid)
        if os.path.exists(os.path.join(d, "route.json")):
            return d, private
    return None, None


def load_route(rid):
    folder, private = route_dir(rid)
    if not folder:
        return None
    r = json.load(open(os.path.join(folder, "route.json"), encoding="utf-8"))
    r["private"] = private
    return r


def load_routes():
    routes = []
    for private, base in ROUTE_DIRS.items():
        if not os.path.isdir(base):
            continue
        for rid in sorted(os.listdir(base)):
            path = os.path.join(base, rid, "route.json")
            if os.path.exists(path):
                r = json.load(open(path, encoding="utf-8"))
                r["private"] = private
                routes.append(r)
    return routes


def nearest_route(lat, lon):
    """The route whose start is closest to the point → (route, distance to its start in m)."""
    best = None
    for r in load_routes():
        s = r["stops"][0]
        d = distance_m(lat, lon, s["lat"], s["lon"])
        if best is None or d < best[1]:
            best = (r, d)
    return best or (None, None)
