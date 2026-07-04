"""Regenerate the GHSL GHS-POP fixture clip.

GHS-POP (EU Commission JRC, free reuse with attribution) is in World Mollweide
(ESRI:54009, metres, equal-area). Steps:

  1. Download a GHS-POP tile from https://ghsl.jrc.ec.europa.eu/download.php
     (pick the 100 m or 1 km product, the tile covering your city).
  2. Set SRC below to the downloaded .tif and choose the window (col/row offset
     + width/height) covering the city of interest — any global city is a window
     swap; no city is hardcoded into the runtime.
  3. Run:  python data/fixtures/fetch_clip.py
     -> writes data/fixtures/ghsl_city.tif (commit that small clip only).
"""
from __future__ import annotations

from pathlib import Path

from abm_auto.gis._fixtures import clip_window

SRC = "GHS_POP_TILE.tif"          # <- the downloaded GHS-POP tile
OUT = Path(__file__).parent / "ghsl_city.tif"
COL_OFF, ROW_OFF, WIDTH, HEIGHT = 0, 0, 100, 100   # <- window over the city


if __name__ == "__main__":
    clip_window(SRC, OUT, COL_OFF, ROW_OFF, WIDTH, HEIGHT)
    print(f"wrote {OUT}")
