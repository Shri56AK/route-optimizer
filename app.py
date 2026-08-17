"""
Route Optimizer API.

POST /optimize-route
    Body: {"stops": [{"name": "A", "lat": 12.97, "lon": 77.59}, ...]}
    Returns: ordered stop list + per-leg distances + total distance

GET /
    Serves a Leaflet-based map UI for trying it interactively.

GET /metrics, /metrics.json
    Prometheus / JSON telemetry: request counts, latency, and optimize()
    latency bucketed by stop count -- the number that actually matters
    here, since 2-opt is O(n^2) per pass.

GET /healthz
    Liveness probe for load balancers / container orchestrators.
"""

import logging
import sys

from flask import Flask, g, jsonify, request, send_from_directory

import metrics
from optimizer import build_distance_matrix, optimize_route

app = Flask(__name__, static_folder="static")

# Hard cap on stop count. 2-opt is O(n^2) per pass and can run several
# passes to convergence -- past a few hundred stops that stops being
# "a fraction of a second" and starts being a request that ties up a
# worker for real time. A real logistics system would offload large
# requests to an async job queue instead of doing this synchronously;
# for this API the simplest safe answer is to cap input size and say so.
MAX_STOPS = 300

logger = logging.getLogger("optimizer")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)


@app.before_request
def _start_timer():
    g._start = metrics.timer()


@app.after_request
def _log_and_record(response):
    duration_ms = metrics.elapsed_ms(getattr(g, "_start", metrics.timer()))
    # Route pattern, not literal path -- see the URL Shortener's app.py
    # for why (avoids unbounded metric cardinality per unique request).
    endpoint = request.url_rule.rule if request.url_rule else request.path
    metrics.record_request(endpoint, request.method, response.status_code, duration_ms)

    logger.info(
        '{"method": "%s", "path": "%s", "status": %d, "duration_ms": %.2f, "ip": "%s"}',
        request.method,
        endpoint,
        response.status_code,
        duration_ms,
        request.remote_addr,
    )
    return response


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.get("/metrics")
def metrics_endpoint():
    return metrics.prometheus_text(), 200, {"Content-Type": "text/plain; version=0.0.4"}


@app.get("/metrics.json")
def metrics_json():
    return jsonify(metrics.snapshot())


def _validate_stop(stop) -> str:
    """Return an error message, or '' if the stop is valid."""
    if "lat" not in stop or "lon" not in stop:
        return "Each stop needs 'lat' and 'lon'"
    try:
        lat, lon = float(stop["lat"]), float(stop["lon"])
    except (TypeError, ValueError):
        return "'lat' and 'lon' must be numbers"
    if not (-90 <= lat <= 90):
        return "'lat' must be between -90 and 90"
    if not (-180 <= lon <= 180):
        return "'lon' must be between -180 and 180"
    return ""


@app.post("/optimize-route")
def optimize_route_endpoint():
    data = request.get_json(silent=True) or {}
    stops = data.get("stops", [])

    if len(stops) < 2:
        return jsonify({"error": "Provide at least 2 stops"}), 400
    if len(stops) > MAX_STOPS:
        return jsonify(
            {"error": f"Too many stops (max {MAX_STOPS}). Split into multiple routes."}
        ), 400

    for stop in stops:
        error = _validate_stop(stop)
        if error:
            return jsonify({"error": error}), 400

    start_index = data.get("start_index", 0)
    if not (0 <= start_index < len(stops)):
        return jsonify({"error": "start_index out of range"}), 400

    optimize_start = metrics.timer()
    route_indices, total_distance_km = optimize_route(stops, start=start_index)
    metrics.record_optimize(len(stops), metrics.elapsed_ms(optimize_start))

    ordered_stops = [stops[i] for i in route_indices]

    # Also return per-leg distances, useful for displaying on the map/UI
    distance_matrix = build_distance_matrix(stops)
    legs = [
        {
            "from": stops[route_indices[i]]["name"],
            "to": stops[route_indices[i + 1]]["name"],
            "distance_km": round(distance_matrix[route_indices[i]][route_indices[i + 1]], 2),
        }
        for i in range(len(route_indices) - 1)
    ]

    return jsonify(
        {
            "ordered_stops": ordered_stops,
            "legs": legs,
            "total_distance_km": round(total_distance_km, 2),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
