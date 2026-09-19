from headsup.geo import distance_to_segment_km, haversine_km
from headsup.models import GeoPoint

OAK = GeoPoint(lat=37.8044, lon=-122.2712)
SF = GeoPoint(lat=37.7749, lon=-122.4194)


def test_haversine_oakland_sf():
    assert 13 < haversine_km(OAK, SF) < 14


def test_distance_to_segment_on_midpoint():
    mid = GeoPoint(lat=(OAK.lat + SF.lat) / 2, lon=(OAK.lon + SF.lon) / 2)
    assert distance_to_segment_km(mid, OAK, SF) < 0.2


def test_distance_to_segment_beyond_endpoint_uses_endpoint():
    far = GeoPoint(lat=37.9, lon=-122.2)
    assert abs(distance_to_segment_km(far, OAK, SF) - haversine_km(far, OAK)) < 0.05
