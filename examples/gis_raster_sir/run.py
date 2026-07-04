"""End-to-end demo: load the GHSL clip -> RasterSpace -> raster-SIR -> gate -> map.

Run after generating the fixture (data/fixtures/fetch_clip.py):
    python examples/gis_raster_sir/run.py
"""
from abm_auto.gis._io import load_raster
from abm_auto.gis._raster_space import RasterSpace
from abm_auto.gis._sir import run_raster_sir
from abm_auto.gis._gate import spatial_spread_gate
from abm_auto.gis._viz import render_map


def main():
    sp = RasterSpace(load_raster("data/fixtures/ghsl_city.tif"))
    res = run_raster_sir(sp, seed=1, steps=60)
    ok, desc = spatial_spread_gate(res, sp.field.data)
    print(("PASS" if ok else "FAIL") + ": " + desc)
    render_map(sp, res.final_infected_field, "examples/gis_raster_sir/map.png")
    print("map -> examples/gis_raster_sir/map.png")


if __name__ == "__main__":
    main()
