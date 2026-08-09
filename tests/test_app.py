"""
API-level tests. Run with: pytest
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_requires_at_least_two_stops(client):
    response = client.post("/optimize-route", json={"stops": [{"name": "A", "lat": 1, "lon": 1}]})
    assert response.status_code == 400


def test_requires_lat_lon(client):
    response = client.post(
        "/optimize-route",
        json={"stops": [{"name": "A"}, {"name": "B", "lat": 1, "lon": 1}]},
    )
    assert response.status_code == 400


def test_successful_optimization(client):
    stops = [
        {"name": "Warehouse", "lat": 12.9716, "lon": 77.5946},
        {"name": "A", "lat": 12.9352, "lon": 77.6245},
        {"name": "B", "lat": 13.0067, "lon": 77.5667},
    ]
    response = client.post("/optimize-route", json={"stops": stops})
    assert response.status_code == 200

    data = response.get_json()
    assert len(data["ordered_stops"]) == 3
    assert len(data["legs"]) == 2
    assert data["total_distance_km"] > 0


def test_invalid_start_index(client):
    stops = [
        {"name": "A", "lat": 1, "lon": 1},
        {"name": "B", "lat": 2, "lon": 2},
    ]
    response = client.post(
        "/optimize-route", json={"stops": stops, "start_index": 5}
    )
    assert response.status_code == 400
