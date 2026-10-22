"""Unit tests for the easyJet fare-ladder pieces (owner, 2026-10-22): the funnel
parser, the calendar parser and the window planner. Like test_ryanair_ladder.py,
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


FUNNEL = {"journeyPairs": [{"outbound": {"flights": {
    "2026-11-08": [
        {"flightNumber": "7621", "iataCarrierCode": "EC", "soldOut": False,
         "departureAirportCode": "LIS", "currency": "EUR",
         "availability": [{"unitsAvailableAtThisPrice": 16, "totalUnitsAvailable": 152}],
         "fares": {"ADT": {"STANDARD": {"unitsAvailableAtThisPrice": 9,
                                        "unitPrice": {"netPrice": 28.99}}}}},
        {"flightNumber": "7633", "iataCarrierCode": "EC", "soldOut": True,
         "departureAirportCode": "LIS", "currency": "EUR",
         "availability": [{"unitsAvailableAtThisPrice": 0, "totalUnitsAvailable": 0}],
         "fares": {}},
    ],
}}}]}


def test_parse_funnel():
    ej = _load("easyjet_ladder")
    rows = ej.parse_funnel(FUNNEL, adt=1, today=dt.date(2026, 11, 7))
    assert len(rows) == 2
    a, b = rows
    assert a["flight_number"] == "EC7621" and a["price"] == 28.99
    assert a["fares_left"] == 9            # seats at the quoted price (the fare bucket)
    assert a["units_total"] == 152         # seats remaining on the flight
    assert a["lead_days"] == 1 and a["currency"] == "EUR"
    assert b["price"] is None and b["units_total"] == 0   # sold out -> NULL price


def test_parse_funnel_empty():
    ej = _load("easyjet_ladder")
    assert ej.parse_funnel({}, adt=1, today=dt.date(2026, 11, 7)) == []


def test_parse_calendar_cheapest_per_day():
    ej = _load("easyjet_ladder")
    body = [{"departureDateTime": "2026-11-08T06:40:00", "outboundPrice": 42.49},
            {"departureDateTime": "2026-11-08T13:00:00", "outboundPrice": 28.99},
            {"departureDateTime": "2026-11-09T06:40:00", "outboundPrice": 31.99},
            {"departureDateTime": "", "outboundPrice": 9.99},        # junk skipped
            {"departureDateTime": "2026-11-10T06:40:00", "outboundPrice": None}]
    rows = ej.parse_calendar(body, "LIS", dt.date(2026, 11, 7))
    assert [(r["dep_date"], r["price"]) for r in rows] == [
        ("2026-11-08", 28.99), ("2026-11-09", 31.99)]
    assert all(r["carrier"] == "U2" and not r["unavailable"] for r in rows)


def test_windows_cover_every_flight_day_and_never_cut_near():
    ej = _load("easyjet_ladder")
    today = dt.date(2026, 11, 7)
    cal = [{"origin": "LIS", "dep_date": (today + dt.timedelta(days=k)).isoformat()}
           for k in range(1, 11)]          # 10 consecutive flight days
    plan = ej.windows_from_calendar(cal, today)
    assert all(o == "LIS" for o, _ in plan)
    covered = set()
    for _, center in plan:
        c = dt.date.fromisoformat(center)
        covered.update(c + dt.timedelta(days=k) for k in (-1, 0, 1))
    for k in range(1, 11):
        assert today + dt.timedelta(days=k) in covered
    # near windows (<= NEAR_DAYS) survive any budget trim
    assert len(plan) <= ej.DAILY_CALLS
