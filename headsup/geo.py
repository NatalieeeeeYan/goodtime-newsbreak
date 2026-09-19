from __future__ import annotations

import math

from headsup.models import GeoPoint

EARTH_KM = 6371.0


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_KM * math.asin(math.sqrt(h))


def _xy(p: GeoPoint, ref_lat: float) -> tuple[float, float]:
    return (math.radians(p.lon) * math.cos(math.radians(ref_lat)) * EARTH_KM, math.radians(p.lat) * EARTH_KM)


def distance_to_segment_km(p: GeoPoint, a: GeoPoint, b: GeoPoint) -> float:
    ref = (a.lat + b.lat) / 2
    px, py = _xy(p, ref)
    ax, ay = _xy(a, ref)
    bx, by = _xy(b, ref)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return haversine_km(p, a)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)
