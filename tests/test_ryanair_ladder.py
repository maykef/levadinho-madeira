"""Unit tests for the Ryanair fare-ladder pieces (owner, 2026-10-22): the availability parser,
the step-feature extraction and the seats lookup. The modules live in git-ignored
seo_research/funchal/mobility/, so these tests SKIP when that folder is absent (CI checkout)."""
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


AVAILABILITY = {
    "currency": "EUR",
    "trips": [{"dates": [
        {"dateOut": "2026-11-09T00:00:00.000", "flights": [
            {"flightNumber": "FR 2244", "faresLeft": 4,
             "regularFare": {"fares": [{"amount": 28.52}]}},
            {"flightNumber": "FR 2246", "faresLeft": -1, "regularFare": None},
        ]},
        {"dateOut": "2026-11-10T00:00:00.000", "flights": []},
    ]}],
}


def test_parse_availability():
    rl = _load("ryanair_ladder")
    rows = rl.parse_availability(AVAILABILITY, adt=5, today=dt.date(2026, 11, 8))
    assert len(rows) == 2
    a, b = rows
    assert a == {"flight_number": "FR2244", "dep_date": "2026-11-09", "lead_days": 1,
                 "adt": 5, "price": 28.52, "currency": "EUR", "fares_left": 4}
    assert b["price"] is None and b["flight_number"] == "FR2246" and b["fares_left"] == -1


def test_parse_availability_empty():
    rl = _load("ryanair_ladder")
    assert rl.parse_availability({}, adt=1, today=dt.date(2026, 11, 8)) == []


def test_ladder_features_steps():
    cl = _load("calibrate_ladder")
    rows = [{"adt": 1, "price": 30.0, "fares_left": 4},
            {"adt": 2, "price": 30.0, "fares_left": 4},
            {"adt": 3, "price": 30.0, "fares_left": -1},
            {"adt": 5, "price": 35.0, "fares_left": -1},
            {"adt": 8, "price": 35.0, "fares_left": -1},
            {"adt": 12, "price": 41.0, "fares_left": -1},
            {"adt": 25, "price": 55.0, "fares_left": -1}]
    f = cl.ladder_features(rows)
    assert f["floor"] == 30.0
    assert f["price_at_25"] == 55.0
    assert f["steps"] == 3                 # 30 -> 35 -> 41 -> 55
    assert f["adt_first_step"] == 5
    assert f["min_fares_left"] == 4        # -1 (= more than 5) is not a count
    assert f["sold_out_from"] is None


def test_ladder_features_sold_out():
    cl = _load("calibrate_ladder")
    rows = [{"adt": 1, "price": 60.0, "fares_left": 2},
            {"adt": 2, "price": 60.0, "fares_left": 2},
            {"adt": 3, "price": None, "fares_left": None}]
    f = cl.ladder_features(rows)
    assert f["sold_out_from"] == 3 and f["floor"] == 60.0 and f["min_fares_left"] == 2


def test_ladder_features_all_sold_out():
    cl = _load("calibrate_ladder")
    f = cl.ladder_features([{"adt": 1, "price": None, "fares_left": None}])
    assert f["floor"] is None and f["steps"] == 0 and f["sold_out_from"] == 1


def test_seats_lookup():
    ar = _load("arrivals")
    cfg = {"default": {"B738": 189, "B38M": 189, "AT75": 70, "PA34": None},
           "operator_overrides": {"Ryanair": {"B738": 189, "B38M": 197}, "Swiftair": {"AT75": 0}}}
    assert ar.seats_for("Ryanair", "B38M", cfg) == 197      # operator override wins
    assert ar.seats_for("TUI fly", "B38M", cfg) == 189      # falls to the typecode default
    assert ar.seats_for("Swiftair", "AT75", cfg) == 0       # 0 is real (mail freighter), not falsy-missing
    assert ar.seats_for("easyJet", "PA34", cfg) is None     # null stays null, never guessed
    assert ar.seats_for("Ryanair", None, cfg) is None       # no typecode -> no seats
    assert ar.seats_for("Anyone", "E290", cfg) is None      # unknown typecode -> null
