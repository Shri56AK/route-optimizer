"""
Route Optimizer API.

POST /optimize-route
    Body: {"stops": [{"name": "A", "lat": 12.97, "lon": 77.59}, ...]}
    Returns: ordered stop list + per-leg distances + total distance

GET /
    Serves a simple Leaflet-based map UI for trying it interactively.
"""

from flask import Flask, jsonify, request, send_from_directory

from optimizer import build_distance_matrix, optimize_route

app = Flask(__name__, static_folder="static")


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/optimize-route")
def optimize_route_endpoint():
    data = request.get_json(silent=True) or {}
    stops = data.get("stops", [])

    if len(stops) < 2:
        return jsonify({"error": "Provide at least 2 stops"}), 400

    for stop in stops:
        if "lat" not in stop or "lon" not in stop:
            return jsonify({"error": "Each stop needs 'lat' and 'lon'"}), 400

    start_index = data.get("start_index", 0)
    if not (0 <= start_index < len(stops)):
        return jsonify({"error": "start_index out of range"}), 400

    route_indices, total_distance_km = optimize_route(stops, start=start_index)

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
