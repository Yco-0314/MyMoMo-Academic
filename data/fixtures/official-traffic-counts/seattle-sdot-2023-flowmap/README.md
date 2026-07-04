# Seattle SDOT 2023 FLOWMAP Traffic Count Fixture

This directory contains a bounded public sample from Seattle Department of
Transportation Traffic Study Flow Counts.

Source item:
`https://data-seattlecitygis.opendata.arcgis.com/api/search/v1/collections/dataset/items/0f8fcff4d1e04ae7abbda101b6013a52`

Feature Service:
`https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Traffic_Study_Flow_Counts/FeatureServer`

Layer:
`https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Traffic_Study_Flow_Counts/FeatureServer/0`

The sample was selected from 2023 records with `FLOWMAP = 'Y'`. The prepared
CSV keeps the official point coordinates in EPSG:2926 and maps `STUDY_ADT` into
the generic `count` column expected by the traffic-count intake helpers.

This fixture is a deterministic validation harness for official-data intake,
checksum verification, and edge-match diagnostics. It is not Seattle's complete
traffic-count dataset, not a centerline map-matching benchmark, and not evidence
of traffic-flow or congestion-model validity.
