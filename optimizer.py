"""
Route optimization.

The core problem here is a variant of the Traveling Salesman Problem
(TSP): given N stops, find the order that minimizes total travel
distance. TSP is NP-hard -- the brute-force exact solution is O(n!),
which is only feasible for a handful of stops (10! = 3.6 million,
15! = 1.3 trillion). Real logistics systems don't solve TSP exactly;
they use heuristics that get close to optimal in polynomial time.

This module implements the two most standard building blocks:

1. Nearest-neighbor construction: O(n^2) time, O(n) space.
   Greedily visit the closest unvisited stop at each step. Fast, but
   can produce noticeably suboptimal routes (a "greedy trap" where an
   early good-looking choice forces a bad long jump later).

2. 2-opt local search: O(n^2) per pass.
   Repeatedly looks for two edges in the route that, if reversed,
   would shorten the total distance -- and applies the improvement.
   This is the standard technique for improving a nearest-neighbor
   route without needing an exact solver.

Together these give a route that's typically within 5-10% of optimal
for realistic stop counts, computed in a fraction of a second, instead
of an exact solution that would never finish for anything but a tiny
number of stops.
"""

from typing import List, Tuple

from geo import haversine_distance

Stop = dict  # {"name": str, "lat": float, "lon": float}


def build_distance_matrix(stops: List[Stop]) -> List[List[float]]:
    """Precompute pairwise distances once, so the optimization steps
    below do O(1) lookups instead of recomputing Haversine distance
    repeatedly. Trades O(n^2) space for avoiding O(n^2) redundant work
    across multiple algorithm passes -- a deliberate, common tradeoff.
    """
    n = len(stops)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist = haversine_distance(
                stops[i]["lat"], stops[i]["lon"], stops[j]["lat"], stops[j]["lon"]
            )
            matrix[i][j] = dist
            matrix[j][i] = dist  # distance is symmetric
    return matrix


def nearest_neighbor_route(distance_matrix: List[List[float]], start: int = 0) -> List[int]:
    """Greedy construction: from the current stop, always go to the
    nearest unvisited stop next. Returns a list of stop indices
    representing visit order.
    """
    n = len(distance_matrix)
    if n == 0:
        return []

    visited = [False] * n
    route = [start]
    visited[start] = True
    current = start

    for _ in range(n - 1):
        nearest_idx = None
        nearest_dist = float("inf")
        for candidate in range(n):
            if not visited[candidate] and distance_matrix[current][candidate] < nearest_dist:
                nearest_dist = distance_matrix[current][candidate]
                nearest_idx = candidate
        route.append(nearest_idx)
        visited[nearest_idx] = True
        current = nearest_idx

    return route


def total_route_distance(route: List[int], distance_matrix: List[List[float]]) -> float:
    """Sum of consecutive-leg distances along the route (not a loop
    back to the start -- this models a one-way delivery run).
    """
    return sum(
        distance_matrix[route[i]][route[i + 1]] for i in range(len(route) - 1)
    )


def two_opt(route: List[int], distance_matrix: List[List[float]]) -> List[int]:
    """Improve a route via 2-opt: repeatedly try reversing a segment
    between two positions, and keep the reversal if it shortens the
    total route distance. Stops when a full pass finds no improvement.

    Time complexity: O(n^2) per pass, and this can run multiple passes
    until convergence -- still polynomial, unlike the O(n!) exact
    solution.
    """
    best = route[:]
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue  # adjacent edges -- reversing does nothing

                new_route = best[:i] + best[i:j][::-1] + best[j:]
                if total_route_distance(new_route, distance_matrix) < total_route_distance(
                    best, distance_matrix
                ):
                    best = new_route
                    improved = True

    return best


def optimize_route(stops: List[Stop], start: int = 0) -> Tuple[List[int], float]:
    """Full pipeline: build distance matrix -> nearest-neighbor
    construction -> 2-opt improvement. Returns (route as stop indices,
    total distance in km).
    """
    distance_matrix = build_distance_matrix(stops)
    route = nearest_neighbor_route(distance_matrix, start=start)
    route = two_opt(route, distance_matrix)
    distance = total_route_distance(route, distance_matrix)
    return route, distance
