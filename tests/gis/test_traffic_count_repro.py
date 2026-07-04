import json
from pathlib import Path

import pytest
from shapely.geometry import LineString

import abm_auto.gis._traffic_count_repro as traffic_count_repro
from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._traffic_counts import (
    TrafficCountEdgeMatch,
    TrafficCountStation,
    match_traffic_counts_to_edges,
)
from abm_auto.gis._traffic_count_repro import (
    DEFAULT_TRAFFIC_COUNT_MANIFEST,
    load_traffic_count_manifest,
    traffic_count_repro_gate,
)


def _write_csv(path: Path) -> None:
    path.write_text("station_id,x,y,count\nmain-a,2,0.2,70\n", encoding="utf-8")


def _write_multi_station_csv(path: Path) -> None:
    path.write_text(
        "id_col,easting,northing,vehicles\n"
        "main-a,2,0.2,70\n"
        "main-b,6,-0.3,30\n"
        "north,5,9.6,40\n",
        encoding="utf-8",
    )


def _write_manifest(path: Path, **overrides) -> dict:
    manifest = {
        "csv_path": "traffic_counts.csv",
        "dataset": " local-test-traffic-counts ",
        "source_url": " local://tests/gis/traffic-counts ",
        "license": " local test fixture; not official traffic count data ",
        "crs": " EPSG:3857 ",
        "columns": {
            "id": " station_id ",
            "x": " x ",
            "y": " y ",
            "count": " count ",
        },
        "max_distance_m": 1,
        "aggregation": "sum",
        "expected_edge_values": {
            "(0, 0)|(10, 0)": 100.0,
            "(0, 10)|(10, 10)": 40.0,
        },
        "description": " tiny local traffic count manifest ",
    }
    manifest.update(overrides)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _geonet():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (10, 0)]),
            LineString([(0, 10), (10, 10)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _edge(a, b):
    return tuple(sorted((a, b), key=repr))


def test_load_traffic_count_manifest_resolves_relative_csv_path(tmp_path):
    _write_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(tmp_path / "manifest.json")

    manifest = load_traffic_count_manifest(tmp_path / "manifest.json")

    assert DEFAULT_TRAFFIC_COUNT_MANIFEST == Path(
        "data/fixtures/traffic-counts/test_manifest.json"
    )
    assert manifest["csv_path"] == str((tmp_path / "traffic_counts.csv").resolve())
    assert manifest["dataset"] == "local-test-traffic-counts"
    assert manifest["source_url"] == "local://tests/gis/traffic-counts"
    assert manifest["license"] == "local test fixture; not official traffic count data"
    assert manifest["crs"] == "EPSG:3857"
    assert manifest["columns"] == {
        "id": "station_id",
        "x": "x",
        "y": "y",
        "count": "count",
    }
    assert manifest["max_distance_m"] == 1.0
    assert manifest["aggregation"] == "sum"
    assert manifest["expected_edge_values"] == {
        _edge((0, 0), (10, 0)): 100.0,
        _edge((0, 10), (10, 10)): 40.0,
    }
    assert manifest["description"] == "tiny local traffic count manifest"


def test_load_traffic_count_manifest_keeps_absolute_csv_path(tmp_path):
    csv_path = tmp_path / "absolute_counts.csv"
    _write_csv(csv_path)
    _write_manifest(tmp_path / "manifest.json", csv_path=str(csv_path))

    manifest = load_traffic_count_manifest(tmp_path / "manifest.json")

    assert manifest["csv_path"] == str(csv_path.resolve())


def test_load_traffic_count_manifest_allows_missing_description(tmp_path):
    _write_csv(tmp_path / "traffic_counts.csv")
    manifest = _write_manifest(tmp_path / "manifest.json")
    del manifest["description"]
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    loaded = load_traffic_count_manifest(tmp_path / "manifest.json")

    assert loaded["description"] == ""


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("csv_path", "", "csv_path must be a non-empty string"),
        ("dataset", "", "dataset must be a non-empty string"),
        ("source_url", "", "source_url must be a non-empty string"),
        ("license", "", "license must be a non-empty string"),
        ("crs", "", "crs must be a non-empty string"),
        ("columns", {}, "columns must contain id, x, y, and count"),
        (
            "max_distance_m",
            0,
            "max_distance_m must be a positive finite number",
        ),
        (
            "max_distance_m",
            True,
            "max_distance_m must be a positive finite number",
        ),
        ("aggregation", "median", "aggregation must be 'sum' or 'mean'"),
        (
            "expected_edge_values",
            {},
            "expected_edge_values must be a non-empty dict",
        ),
    ],
)
def test_load_traffic_count_manifest_rejects_malformed_fields(
    tmp_path,
    field,
    value,
    message,
):
    _write_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(tmp_path / "manifest.json", **{field: value})

    with pytest.raises(ValueError, match=message):
        load_traffic_count_manifest(tmp_path / "manifest.json")


def test_load_traffic_count_manifest_rejects_missing_csv(tmp_path):
    _write_manifest(tmp_path / "manifest.json", csv_path="missing.csv")

    with pytest.raises(ValueError, match="csv_path does not exist"):
        load_traffic_count_manifest(tmp_path / "manifest.json")


def test_load_traffic_count_manifest_rejects_bad_expected_edge_key(tmp_path):
    _write_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(
        tmp_path / "manifest.json",
        expected_edge_values={"not-an-edge": 100.0},
    )

    with pytest.raises(ValueError, match="expected_edge_values keys must use"):
        load_traffic_count_manifest(tmp_path / "manifest.json")


def test_load_traffic_count_manifest_rejects_duplicate_normalized_edge_keys(tmp_path):
    _write_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(
        tmp_path / "manifest.json",
        expected_edge_values={
            "(0, 0)|(10, 0)": 100.0,
            "(10, 0)|(0, 0)": 25.0,
        },
    )

    with pytest.raises(ValueError, match="duplicate normalized expected edge key"):
        load_traffic_count_manifest(tmp_path / "manifest.json")


def test_load_traffic_count_manifest_rejects_json_non_object(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest must be a JSON object"):
        load_traffic_count_manifest(path)


def test_fixture_manifest_loads_from_default_path():
    manifest = load_traffic_count_manifest(DEFAULT_TRAFFIC_COUNT_MANIFEST)

    assert manifest["dataset"] == "local-test-traffic-counts"
    assert manifest["csv_path"].endswith("test_counts.csv")


def test_load_traffic_count_stations_from_manifest_uses_manifest_columns(tmp_path):
    _write_multi_station_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(
        tmp_path / "manifest.json",
        columns={
            "id": "id_col",
            "x": "easting",
            "y": "northing",
            "count": "vehicles",
        },
    )

    loaded = traffic_count_repro.load_traffic_count_stations_from_manifest(
        tmp_path / "manifest.json"
    )

    assert loaded["manifest"]["columns"] == {
        "id": "id_col",
        "x": "easting",
        "y": "northing",
        "count": "vehicles",
    }
    assert [station.station_id for station in loaded["stations"]] == [
        "main-a",
        "main-b",
        "north",
    ]
    assert [station.count for station in loaded["stations"]] == [70.0, 30.0, 40.0]
    assert loaded["manifest_dataset"] == "local-test-traffic-counts"
    assert loaded["manifest_source_url"] == "local://tests/gis/traffic-counts"
    assert (
        loaded["manifest_license"]
        == "local test fixture; not official traffic count data"
    )
    assert loaded["manifest_csv_path"] == str(
        (tmp_path / "traffic_counts.csv").resolve()
    )
    assert loaded["manifest_crs"] == "EPSG:3857"


def test_traffic_count_match_diagnostics_reports_distances_and_duplicates(tmp_path):
    _write_multi_station_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(
        tmp_path / "manifest.json",
        columns={
            "id": "id_col",
            "x": "easting",
            "y": "northing",
            "count": "vehicles",
        },
    )
    loaded = traffic_count_repro.load_traffic_count_stations_from_manifest(
        tmp_path / "manifest.json"
    )
    matches = match_traffic_counts_to_edges(
        _geonet(),
        loaded["stations"],
        max_distance_m=1.0,
    )

    diagnostics = traffic_count_repro.traffic_count_match_diagnostics(
        _geonet(),
        loaded["stations"],
        matches,
        max_distance_m=1.0,
    )

    assert diagnostics["n_stations"] == 3
    assert diagnostics["matched_stations"] == 3
    assert diagnostics["unmatched_stations"] == []
    assert diagnostics["coverage"] == 1.0
    assert diagnostics["max_distance_m"] == 1.0
    assert diagnostics["matched_edges"] == 2
    assert diagnostics["max_match_distance_m"] == pytest.approx(0.4)
    assert diagnostics["mean_distance_m"] == pytest.approx(0.3)
    assert diagnostics["duplicate_edge_groups"] == [
        {
            "edge": _edge((0, 0), (10, 0)),
            "station_ids": ["main-a", "main-b"],
            "count": 2,
        }
    ]


def test_traffic_count_match_diagnostics_rejects_foreign_match():
    stations = []
    matches = [
        TrafficCountEdgeMatch(
            "foreign",
            _edge((0, 0), (10, 0)),
            0.0,
            1.0,
        )
    ]

    with pytest.raises(ValueError, match="matches must correspond to stations"):
        traffic_count_repro.traffic_count_match_diagnostics(
            _geonet(),
            stations,
            matches,
            max_distance_m=1.0,
        )


def test_traffic_count_match_diagnostics_rejects_match_on_edge_outside_geonet():
    stations = [TrafficCountStation("known", 2, 0.2, 70)]
    matches = [
        TrafficCountEdgeMatch(
            "known",
            _edge((100, 0), (110, 0)),
            0.2,
            70.0,
        )
    ]

    with pytest.raises(ValueError, match="match edge is not in GeoNetwork"):
        traffic_count_repro.traffic_count_match_diagnostics(
            _geonet(),
            stations,
            matches,
            max_distance_m=1.0,
        )


def test_traffic_count_match_diagnostics_rejects_match_beyond_max_distance():
    stations = [TrafficCountStation("known", 2, 0.2, 70)]
    matches = [
        TrafficCountEdgeMatch(
            "known",
            _edge((0, 0), (10, 0)),
            1.5,
            70.0,
        )
    ]

    with pytest.raises(ValueError, match="match distance exceeds max_distance_m"):
        traffic_count_repro.traffic_count_match_diagnostics(
            _geonet(),
            stations,
            matches,
            max_distance_m=1.0,
        )


def test_observed_network_from_traffic_count_manifest_returns_target_and_diagnostics(
    tmp_path,
):
    _write_multi_station_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(
        tmp_path / "manifest.json",
        columns={
            "id": "id_col",
            "x": "easting",
            "y": "northing",
            "count": "vehicles",
        },
    )

    repro = traffic_count_repro.observed_network_from_traffic_count_manifest(
        _geonet(),
        tmp_path / "manifest.json",
    )

    assert repro["observed"].edge_values == {
        _edge((0, 0), (10, 0)): 100.0,
        _edge((0, 10), (10, 10)): 40.0,
    }
    assert (
        repro["observed"].source
        == "local-test-traffic-counts: local://tests/gis/traffic-counts"
    )
    assert repro["diagnostics"]["coverage"] == 1.0
    assert repro["manifest_dataset"] == "local-test-traffic-counts"
    assert repro["manifest_source_url"] == "local://tests/gis/traffic-counts"
    assert (
        repro["manifest_license"]
        == "local test fixture; not official traffic count data"
    )
    assert repro["manifest_csv_path"] == str(
        (tmp_path / "traffic_counts.csv").resolve()
    )
    assert repro["manifest_crs"] == "EPSG:3857"
    assert repro["manifest"]["dataset"] == "local-test-traffic-counts"
    assert [station.station_id for station in repro["stations"]] == [
        "main-a",
        "main-b",
        "north",
    ]
    assert [match.station_id for match in repro["matches"]] == [
        "main-a",
        "main-b",
        "north",
    ]


def test_observed_network_from_traffic_count_manifest_rejects_crs_mismatch(tmp_path):
    _write_multi_station_csv(tmp_path / "traffic_counts.csv")
    _write_manifest(
        tmp_path / "manifest.json",
        crs="EPSG:4326",
        columns={
            "id": "id_col",
            "x": "easting",
            "y": "northing",
            "count": "vehicles",
        },
    )

    with pytest.raises(
        ValueError,
        match="manifest CRS does not match GeoNetwork CRS",
    ):
        traffic_count_repro.observed_network_from_traffic_count_manifest(
            _geonet(),
            tmp_path / "manifest.json",
        )


def test_traffic_count_repro_gate_passes_with_local_fixture_boundary():
    ok, desc = traffic_count_repro_gate(DEFAULT_TRAFFIC_COUNT_MANIFEST)

    assert ok, desc
    assert "traffic-count repro pack matched manifest stations" in desc
    assert "not official traffic-data download" in desc
    assert "not full map matching" in desc
    assert "not traffic-flow calibration" in desc
