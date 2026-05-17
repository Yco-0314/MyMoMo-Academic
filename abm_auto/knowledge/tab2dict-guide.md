# tab2dict Guide

> Internal reference for LLM code generation agents.
> Original: tab2dict-guide.md from ABM4ALL/melodie-skills (MIT).
> NOTE: tab2dict is an optional dependency. Check if installed before using.
>       If not available, use pandas DataFrames in Scenario.load_data() instead.

## What is tab2dict?

tab2dict transforms tabular data (CSV files) into dictionary structures optimised for
rapid multi-dimensional lookups. It addresses datasets with 3+ lookup dimensions
accessed frequently per-agent per-timestep.

**When to use**: 3+ lookup dimensions, accessed per-agent per-timestep.
**When to skip**: Simple models with 1-2 parameters; when pandas is sufficient.

## Core Components

### TabKey — Universal Lookup Key

Subclass `TabKey`; declare dimensions as optional attributes prefixed `id_` or `time_`:

```python
from tab2dict import TabKey

class MyKey(TabKey):
    def __init__(self, id_region=None, id_sector=None, time_year=None):
        self.id_region = id_region
        self.id_sector = id_sector
        self.time_year = time_year
```

Key methods:
- `key.from_dict(d)` — build key from dict
- `key.filter_dataframe(df)` — filter DataFrame by key attributes
- `key.make_copy()` — shallow copy

### TabDict — Multi-Dimensional Dictionary

Three types, auto-detected by filename prefix:

| Prefix | Type | Maps |
|---|---|---|
| `ID_` | ID table | id → name string |
| `Relation_` | Relation table | parent_id → [child_ids] |
| `Data_` | Data table | multi-dim key → scalar value |

**Loading:**
```python
from tab2dict import TabDict

td = TabDict.from_file("Data_TechnologyCost.csv", value_column_name="capex")
td = TabDict.from_dataframe(df, tdict_type="Data")
```

**Access:**
```python
key = MyKey(id_region=0, id_sector=1, time_year=2025)
value = td.get_item(key, not_found_default=0.0)
td.set_item(key, 42.0)
td.accumulate_item(key, delta)             # thread-safe += delta
```

**Export:**
```python
df = td.to_dataframe()
for key_tuple, value in td.items():
    ...
```

## Usage Pattern in Scenario

```python
class MyScenario(Scenario):
    def load_data(self):
        self.cost_data = TabDict.from_file(
            self.input_folder / "Data_Cost.csv",
            value_column_name="cost"
        )

    def setup_data(self):
        pass  # optional preprocessing
```

Then in Environment or Agent:
```python
key = MyKey(id_sector=agent.sector_id, time_year=self.model.t)
cost = self.scenario.cost_data.get_item(key, not_found_default=0.0)
```

## Fallback (when tab2dict not installed)

```python
# In Scenario.load_data():
import pandas as pd
self.cost_df = pd.read_csv(self.input_folder / "Data_Cost.csv")

# In agent step (slower but works):
row = self.scenario.cost_df[
    (self.scenario.cost_df.id_sector == self.sector_id) &
    (self.scenario.cost_df.time_year == current_year)
]
cost = row["cost"].values[0] if len(row) else 0.0
```
