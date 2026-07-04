# Official Traffic Count Intake Fixtures

This directory contains a tiny synthetic Caltrans-style fixture for testing the
official traffic-count intake contract. It is not official Caltrans data.

It also contains bounded Seattle public-data fixtures:

- `seattle-sdot-2023-flowmap/`: three official Seattle SDOT 2023 FLOWMAP count
  records, prepared into the generic `station_id,x,y,count` shape.
- `seattle-sdot-2023-centerline-match/`: the same three count records matched
  against three official Seattle Streets centerline features.

To use a real Caltrans AADT slice:

1. Download AADT or AADT GIS data from
   `https://dot.ca.gov/programs/traffic-operations/census` outside this
   repository.
2. Prepare a small local CSV with at least `station_id,x,y,count`.
3. Make sure `x` and `y` are in the same CRS as the target `GeoNetwork`.
4. Compute checksums with `shasum -a 256 <file>`.
5. Copy `manifest.example.json`, fill in source/provenance/checksum fields, and
   point `prepared_csv_path` at the local CSV.
6. Run the official intake gate from Python tests or a short local script.

The intake gate validates provenance, checksums, CRS declarations, station
loading, edge matching, and diagnostic thresholds. It does not download data,
reproject coordinates, perform route/postmile geocoding, or prove traffic-flow
validity.

The Seattle centerline match gate adds official street geometry to the same
diagnostic path. It is still a bounded reproducibility fixture, not the full
Seattle street network and not production map matching.
