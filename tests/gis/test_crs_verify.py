from abm_auto.gis._crs import wgs84_to_gcj02, looks_like_gcj02_mislabeled


def test_detects_mislabeled_gcj02():
    true_wgs = [(116.39, 39.90), (116.41, 39.92), (116.40, 39.91)]
    # a layer that DECLARES wgs84 but actually holds gcj02 coordinates:
    declared = [wgs84_to_gcj02(lon, lat) for lon, lat in true_wgs]
    suspected, info = looks_like_gcj02_mislabeled(declared, true_wgs)
    assert suspected is True
    assert info["raw_offset_m"] > 100
    assert info["corrected_offset_m"] < info["raw_offset_m"] * 0.5


def test_true_wgs84_not_flagged():
    true_wgs = [(116.39, 39.90), (116.41, 39.92)]
    suspected, info = looks_like_gcj02_mislabeled(true_wgs, true_wgs)
    assert suspected is False
