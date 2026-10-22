"""Unit tests for the Transavia fare-ladder parsers (owner, 2026-10-22). Like the
other carrier tests, these SKIP when seo_research/funchal/mobility/ is absent."""
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


def test_parse_availability():
    tv = _load("transavia_ladder")
    body = {"data": {"outboundFlight": {"selectedDate": "2026-11-11", "timeSlots": [
        {"flightNumber": "TO7690", "departureDateTime": "2026-11-11T07:45:00+01:00",
         "price": 143, "availabilityCount": 6, "fareClass": "K"}]}}}
    rows = tv.parse_availability(body, "ORY", today=dt.date(2026, 11, 10))
    assert len(rows) == 1
    r = rows[0]
    assert r["flight_number"] == "TO7690" and r["carrier"] == "TO"
    assert r["price"] == 143 and r["fares_left"] == 6
    assert r["class_of_service"] == "K" and r["lead_days"] == 1
    assert r["units_total"] is None and r["currency"] == "EUR"


def test_parse_availability_empty():
    tv = _load("transavia_ladder")
    assert tv.parse_availability({}, "ORY", today=dt.date(2026, 11, 10)) == []
    assert tv.parse_availability({"data": {"outboundFlight": None}}, "ORY",
                                 today=dt.date(2026, 11, 10)) == []
    # some flight-availability responses carry a LIST payload (seen live 2026-10-22)
    assert tv.parse_availability({"data": [{"x": 1}]}, "ORY",
                                 today=dt.date(2026, 11, 10)) == []


def test_parse_calendar_carrier_by_origin():
    tv = _load("transavia_ladder")
    body = {"data": [{"date": "2026-11-02", "price": 63, "type": "lowFare"},
                     {"date": "2026-11-04", "price": 89, "type": "regularFare"},
                     {"date": "2026-11-05", "price": None, "type": "regularFare"}]}
    ory = tv.parse_calendar(body, "ORY")
    ams = tv.parse_calendar(body, "AMS")
    assert [(r["dep_date"], r["price"]) for r in ory] == [
        ("2026-11-02", 63), ("2026-11-04", 89)]
    assert all(r["carrier"] == "TO" for r in ory)
    assert all(r["carrier"] == "HV" for r in ams)


def test_month_pairs():
    tv = _load("transavia_ladder")
    assert tv.month_pairs(dt.date(2026, 10, 22), 3) == [
        "2026-10/2026-11", "2026-12/2027-01", "2027-02/2027-03"]
    assert tv.month_pairs(dt.date(2026, 12, 1), 2) == [
        "2026-12/2027-01", "2027-02/2027-03"]
