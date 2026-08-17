"""
Unit + integration tests. Run with: pytest
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo import haversine_distance
from optimizer import (
    build_distance_matrix,
    nearest_neighbor_route,
    optimize_route,
    total_route_distance,
    two_opt,
)


# ---------- geo.py ----------

def test_haversine_same_point_is_zero():
    assert haversine_distance(12.97, 77.59, 12.97, 77.59) == 0


def test_haversine_known_distance():
    # Bengaluru to Chennai is roughly 290 km as the crow flies
    dist = haversine_distance(12.9716, 77.5946, 13.0827, 80.2707)
    assert 280 < dist < 300


def test_haversine_symmetric():
    d1 = haversine_distance(12.97, 77.59, 13.08, 80.27)
    d2 = haversine_distance(13.08, 80.27, 12.97, 77.59)
    assert abs(d1 - d2) < 1e-9


# ---------- optimizer.py ----------

SAMPLE_STOPS = [
    {"name": "Warehouse", "lat": 12.9716, "lon": 77.5946},
    {"name": "A", "lat": 12.9352, "lon": 77.6245},
    {"name": "B", "lat": 13.0067, "lon": 77.5667},
    {"name": "C", "lat": 12.9081, "lon": 77.6476},
    {"name": "D", "lat": 12.9784, "lon": 77.6408},
]


def test_distance_matrix_is_symmetric_and_zero_diagonal():
    matrix = build_distance_matrix(SAMPLE_STOPS)
    n = len(SAMPLE_STOPS)
    for i in range(n):
        assert matrix[i][i] == 0
        for j in range(n):
            assert abs(matrix[i][j] - matrix[j][i]) < 1e-9


def test_nearest_neighbor_visits_every_stop_exactly_once():
    matrix = build_distance_matrix(SAMPLE_STOPS)
    route = nearest_neighbor_route(matrix, start=0)
    assert sorted(route) == list(range(len(SAMPLE_STOPS)))
    assert route[0] == 0  # starts where we told it to


def test_two_opt_never_makes_the_route_worse():
    matrix = build_distance_matrix(SAMPLE_STOPS)
    nn_route = nearest_neighbor_route(matrix, start=0)
    nn_distance = total_route_distance(nn_route, matrix)

    improved_route = two_opt(nn_route, matrix)
    improved_distance = total_route_distance(improved_route, matrix)

    assert improved_distance <= nn_distance + 1e-9
    assert sorted(improved_route) == sorted(nn_route)  # still visits all stops


def test_optimize_route_end_to_end():
    route, distance = optimize_route(SAMPLE_STOPS, start=0)
    assert sorted(route) == list(range(len(SAMPLE_STOPS)))
    assert distance > 0


def test_optimize_route_beats_or_matches_naive_order():
    """The optimized route should never be longer than simply visiting
    stops in the order they were given.
    """
    matrix = build_distance_matrix(SAMPLE_STOPS)
    naive_route = list(range(len(SAMPLE_STOPS)))
    naive_distance = total_route_distance(naive_route, matrix)

    _, optimized_distance = optimize_route(SAMPLE_STOPS, start=0)

    assert optimized_distance <= naive_distance + 1e-9
