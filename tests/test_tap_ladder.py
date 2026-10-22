"""Unit tests for the TAP fare-calendar parser (owner, 2026-10-22). SKIP when
seo_research/funchal/mobility/ is absent (CI checkout), like the other carriers."""
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


def test_parse_calendar_flags():
    tp = _load("tap_ladder")
    body = {"data": {"bestPriceForDates": [
        {"departureDate": "2026-11-01T00:00:00", "bestTotalPrice": 61.9,
         "currency": "EUR", "soldOut": False, "noFlights": False},
        {"departureDate": "2026-11-02T00:00:00", "bestTotalPrice": 0,
         "currency": "EUR", "soldOut": True, "noFlights": False},
        {"departureDate": "2026-11-03T00:00:00", "bestTotalPrice": 0,
         "currency": "EUR", "soldOut": False, "noFlights": True}]}}
    rows = tp.parse_calendar(body, "OPO")
    assert len(rows) == 2                        # the no-flights day has no row
    a, b = rows
    assert a["price"] == 61.9 and not a["sold_out"]
    assert b["sold_out"] and b["price"] is None  # sold out -> NULL price
    assert all(r["carrier"] == "TP" and r["origin"] == "OPO" for r in rows)


def test_parse_calendar_empty():
    tp = _load("tap_ladder")
    assert tp.parse_calendar({}, "LIS") == []
    assert tp.parse_calendar({"data": {}}, "LIS") == []


def test_months_ahead_wraps_year():
    tp = _load("tap_ladder")
    assert tp.months_ahead(dt.date(2026, 11, 15), 4) == [
        (2026, 11), (2026, 12), (2027, 1), (2027, 2)]
