# Delivery Route Optimizer

A route optimization API and interactive map UI that computes an
efficient visiting order for a set of delivery stops — built to
demonstrate real algorithmic problem-solving (not just CRUD), the kind
of "optimization under constraints" thinking that shows up in logistics
systems at companies like Amazon.

## The problem

Given N delivery stops, find the visiting order that minimizes total
travel distance. This is a variant of the **Traveling Salesman Problem
(TSP)** — a classic NP-hard problem. The exact brute-force solution is
O(n!), which is only feasible for a handful of stops (10! ≈ 3.6
million, 15! ≈ 1.3 trillion — completely infeasible). Real-world
logistics systems don't solve TSP exactly; they use polynomial-time
heuristics that get close to optimal, fast.

## Algorithm

This project implements the two standard building blocks for that:

1. **Nearest-neighbor construction** — O(n²) time.
   Starting from a chosen stop, greedily visit the closest unvisited
   stop next. Fast and simple, but can fall into a "greedy trap":
   early good-looking choices can force a long, inefficient jump later
   in the route.

2. **2-opt local search** — O(n²) per improvement pass.
   Repeatedly looks for two edges in the route that, if reversed,
   would shorten the total distance, and applies the improvement until
   no further gains are found. This is the standard technique for
   improving a greedy route without needing an exact solver.

Together: build a distance matrix once (O(n²)), construct an initial
route (O(n²)), then improve it with 2-opt (O(n²) per pass) — all
polynomial time, producing a route typically within 5-10% of optimal
for realistic stop counts, computed in milliseconds.

## Why Haversine distance, not Euclidean?

Straight-line distance between two lat/lon coordinates isn't simple
Euclidean distance, because the Earth is a sphere. The Haversine
formula accounts for that curvature — the right building block for any
real geographic routing calculation.

## API

**POST /optimize-route**
```json
{
  "stops": [
    {"name": "Warehouse", "lat": 12.9716, "lon": 77.5946},
    {"name": "Stop A", "lat": 12.9352, "lon": 77.6245}
  ],
  "start_index": 0
}
```
Returns the optimized stop order, per-leg distances, and total distance.

**GET /**
Serves an interactive Leaflet map UI — paste in stops as JSON, click
"Optimize Route", and see the computed route drawn on the map.

## Running locally

```bash
pip install -r requirements.txt
python app.py
```
Then open `http://localhost:5001` in your browser for the map UI, or
call `/optimize-route` directly with curl/Postman.

## Running tests

```bash
pytest
```
Covers: Haversine correctness, distance matrix symmetry, that
nearest-neighbor visits every stop exactly once, that 2-opt never makes
a route worse, and that the full pipeline beats a naive unoptimized
route.

## Scaling this further (things I'd add next)

- **Vehicle Routing Problem (VRP)**: extend to multiple delivery
  vehicles with capacity constraints, not just one route.
  - Time-window constraints (deliver between 9am-12pm, etc.)
- Swap the straight-line Haversine distance for a real road-network
  distance/time using a routing API (e.g. OSRM), since real delivery
  routes follow roads, not straight lines.
- Add simulated annealing or a genetic algorithm as an alternative to
  2-opt for larger stop counts, where 2-opt alone plateaus.
- Persist stop sets and past routes in a database instead of taking
  raw JSON per request.

## Tech stack

Python, Flask, Leaflet.js (OpenStreetMap), pytest
