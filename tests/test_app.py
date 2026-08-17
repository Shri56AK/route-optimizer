"""
API-level tests. Run with: pytest
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import metrics
from app import MAX_STOPS, app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    metrics.reset()
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


def test_rejects_out_of_range_latitude(client):
    response = client.post(
        "/optimize-route",
        json={"stops": [{"name": "A", "lat": 999, "lon": 1}, {"name": "B", "lat": 1, "lon": 1}]},
    )
    assert response.status_code == 400


def test_rejects_non_numeric_coordinates(client):
    response = client.post(
        "/optimize-route",
        json={"stops": [{"name": "A", "lat": "north", "lon": 1}, {"name": "B", "lat": 1, "lon": 1}]},
    )
    assert response.status_code == 400


def test_rejects_too_many_stops(client):
    stops = [{"name": f"S{i}", "lat": i * 0.001, "lon": i * 0.001} for i in range(MAX_STOPS + 1)]
    response = client.post("/optimize-route", json={"stops": stops})
    assert response.status_code == 400
    assert "Too many stops" in response.get_json()["error"]


def test_accepts_exactly_max_stops(client):
    stops = [{"name": f"S{i}", "lat": i * 0.001, "lon": i * 0.001} for i in range(MAX_STOPS)]
    response = client.post("/optimize-route", json={"stops": stops})
    assert response.status_code == 200


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


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_metrics_json_reports_optimize_latency(client):
    stops = [
        {"name": "Warehouse", "lat": 12.9716, "lon": 77.5946},
        {"name": "A", "lat": 12.9352, "lon": 77.6245},
        {"name": "B", "lat": 13.0067, "lon": 77.5667},
    ]
    client.post("/optimize-route", json={"stops": stops})

    response = client.get("/metrics.json")
    assert response.status_code == 200
    data = response.get_json()
    assert data["optimize_latency_by_stop_count"]["1-10"]["count"] == 1


def test_metrics_prometheus_format(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "optimizer_requests_total" in response.get_data(as_text=True)


def test_index_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dispatch" in response.data
