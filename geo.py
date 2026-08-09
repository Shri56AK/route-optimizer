"""
Geographic distance utilities.

Straight-line distance between two lat/lon points isn't simple Euclidean
distance, because the Earth is a sphere, not a flat plane. The Haversine
formula accounts for this curvature and is the standard approach used
in real routing/logistics systems for reasonably short distances
(it's an approximation -- real map routing engines also account for
roads, but this is the right building block for a routing algorithm).
"""

import math

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two points in kilometers.

    Time complexity: O(1) -- a handful of trig operations regardless of
    input size. This matters because it gets called O(n^2) times when
    building a full distance matrix for n stops, so keeping this O(1)
    is what keeps the matrix build at O(n^2) rather than worse.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c
