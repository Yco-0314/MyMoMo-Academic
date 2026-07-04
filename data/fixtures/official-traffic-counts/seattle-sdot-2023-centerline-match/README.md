# Seattle SDOT 2023 FLOWMAP Centerline Match Fixture

This directory pairs the committed Seattle SDOT 2023 FLOWMAP traffic-count
sample with a bounded Seattle Streets centerline sample.

Road source:
`https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Seattle_Streets_1/FeatureServer/0`

Query:
`OBJECTID IN (9659868,9638977,9645707)`

The three road features correspond to the three committed count stations:

- `sdot-342953` -> `15TH AVE NE`
- `sdot-342077` -> `17TH AVE S`
- `sdot-342019` -> `MARINE VIEW DR SW`

The raw centerline response is stored in EPSG:2926. Tests split ArcGIS polyline
paths into straight two-point segments before building `GeoNetwork`, because
`GeoNetwork` stores edge geometry as node-to-node lines.

This fixture is a deterministic validation harness for official count points
matched to official centerline geometry. It is not Seattle's complete street
network, not production map matching, not traffic-flow validity, and not
congestion calibration.
