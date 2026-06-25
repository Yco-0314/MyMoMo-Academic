import importlib

import pytest


def test_subpackage_imports_without_gis_deps():
    # Importing the package must NOT hard-fail even if rasterio/pyproj are absent.
    mod = importlib.import_module("abm_auto.gis")
    assert hasattr(mod, "require_gis")


def test_require_gis_raises_clear_error_when_missing(monkeypatch):
    import abm_auto.gis as gis
    monkeypatch.setattr(gis, "_HAS_GIS", False)
    with pytest.raises(ImportError, match=r"pip install .*\[gis\]"):
        gis.require_gis()
