"""Unit tests for the Wizz Air fare-ladder pieces (owner, 2026-10-22): the search
parser, the farechart parser and the day planner. Like the Ryanair/easyJet tests,
these SKIP when git-ignored seo_research/funchal/mobility/ is absent (CI checkout)."""
import datetime as dt
import importlib.util
import os

import pytest

MOB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "seo_research", "funchal", "mobility")
pytestmark = pytest.mark.skipif(not os.path.isdir(MOB), reason="mobility/ not present (CI checkout)")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(MOB, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SEARCH = {"outboundFlights": [
    {"flightNumber": "2397", "carrierCode": "W6", "departureStation": "BUD",
     "departureDateTime": "2026-11-09T14:30:00", "classOfService": "K",
     "fares": [{"basePrice": {"amount": 42155.0, "currencyCode": "HUF"}},
               {"basePrice": {"amount": 55900.0, "currencyCode": "HUF"}}]},
    {"flightNumber": "1029", "carrierCode": "W6", "departureStation": "KTW",
     "departureDateTime": "2026-11-10T06:00:00", "classOfService": None,
     "fares": []},                                     # nothing sellable
    {"flightNumber": "7777", "carrierCode": "W6", "departureStation": "BUD",
     "departureDateTime": "2026-11-09T20:00:00",
     "fares": [{"basePrice": None}]},                  # fare with no price object
]}


def test_parse_search():
    wz = _load("wizzair_ladder")
    rows = wz.parse_search(SEARCH, today=dt.date(2026, 11, 8))
    assert len(rows) == 3
    a, b, c = rows
    assert a["flight_number"] == "W62397" and a["price"] == 42155.0
    assert a["currency"] == "HUF" and a["class_of_service"] == "K"
    assert a["lead_days"] == 1 and a["adt"] == 1
    assert b["price"] is None                           # empty fares -> NULL price
    assert c["price"] is None and c["flight_number"] == "W67777"


def test_parse_search_empty():
    wz = _load("wizzair_ladder")
    assert wz.parse_search({}, today=dt.date(2026, 11, 8)) == []


def test_parse_farechart_skips_nodata():
    wz = _load("wizzair_ladder")
    body = {"outboundFlights": [
        {"date": "2026-11-02T00:00:00", "priceType": "price",
         "price": {"amount": 34490.0, "currencyCode": "HUF"}},
        {"date": "2026-11-03T00:00:00", "priceType": "noData",
         "price": {"amount": 0.0, "currencyCode": "HUF"}},
        {"date": "2026-11-04T00:00:00", "priceType": "price",
         "price": {"amount": 42190.0, "currencyCode": "HUF"}}]}
    rows = wz.parse_farechart(body, "BUD")
    assert [(r["dep_date"], r["price"]) for r in rows] == [
        ("2026-11-02", 34490.0), ("2026-11-04", 42190.0)]
    assert all(r["carrier"] == "W6" and r["currency"] == "HUF" for r in rows)


def test_plan_days_near_daily_far_rotated():
    wz = _load("wizzair_ladder")
    today = dt.date(2026, 11, 7)
    near = [(today + dt.timedelta(days=k)).isoformat() for k in (2, 9, 16, 30)]
    far = [(today + dt.timedelta(days=k)).isoformat() for k in (40, 47, 54, 61, 68)]
    plan = wz.plan_days({"BUD": near + far, "WAW": near}, today)
    planned_near = [p for p in plan if p[1] in near]
    assert len(planned_near) == 8                       # every near day, both routes
    # far days only on their crc32 week slot
    import zlib
    for origin, day in plan:
        if day in far:
            assert zlib.crc32(f"{origin}{day}".encode()) % 7 == today.toordinal() % 7
    assert len(plan) <= wz.DAILY_LOADS
