# ABM Auto Runtime — Data File Guide

> Internal reference for LLM code generation agents.
> Original: melodie-data-guide.md from ABM4ALL/melodie-skills (MIT).

## Core Principle

> "Data table design is a core part of model design."

Establishing ID dimensions, their relationships, and value ranges clarifies the entire
model structure before writing agent behavior code.

All data files belong in `data/input/`. The runtime auto-identifies file type via prefix.

---

## File Types

### 1. SimulatorScenarios.csv ✅ REQUIRED

Specifies which scenarios run and all scalar parameters that vary across them.

| Column | Type | Description |
|---|---|---|
| `id` | int | Scenario ID, starts at 0 |
| `run_num` | int | Replications per scenario (usually 1) |
| `periods` | int | Simulation time steps |
| `agent_num` | int | Number of agents |
| `...` | int/float | All other scenario parameters |

**Minimum viable file (ONE row for default scenario):**
```csv
id,run_num,periods,agent_num,param_x
0,1,100,500,0.3
```

Grid models must also include `grid_width` and `grid_height`.

---

### 2. AgentParams.csv (optional)

Per-agent initial attribute values. Loaded before `agent.setup()` — so `setup()`
MUST use `getattr(self, attr, default)` to avoid overwriting CSV values.

```csv
id,state,energy
0,1,0.8
1,0,1.0
```

---

### 3. ID Tables — `ID_*.csv`

Enumerate categorical dimensions (technologies, regions, sectors, etc.).
Foundation of hierarchical data architecture.

```csv
id,name
0,Sector_A
1,Sector_B
```

---

### 4. Relation Tables — `Relation_*.csv`

Valid combinations between two dimensions ("which options pair with which").

```csv
id_parent,id_child
0,0
0,1
1,2
```

---

### 5. Fixed Parameter Tables — `Data_*.csv`

Unchanging system attributes organised by one or more ID dimensions.

```csv
id_sector,id_technology,cost
0,0,100.0
0,1,150.0
```

---

### 6. Time-Varying Data — `Data_*.csv`

Parameters that change over time. Two formats:

**Wide format** (year columns):
```csv
id_sector,year_2020,year_2025,year_2030
0,0.5,0.4,0.3
```

**Long format** (explicit time column):
```csv
id_sector,time_year,value
0,2020,0.5
0,2025,0.4
```

---

### 7. Distribution Tables — `Data_*.csv`

Probability distributions for random agent initialization.
Support conditional sampling based on existing agent attributes.

```csv
id_group,mean_income,std_income
0,50000,10000
1,80000,15000
```

---

## Data Quality Checklist

Before running the model, verify:
- [ ] `SimulatorScenarios.csv` exists with at least one row (id=0)
- [ ] All Scenario attributes declared in `setup()` have matching CSV columns
- [ ] `id` columns are integers starting at 0
- [ ] No duplicate `id` values in ID tables
- [ ] Time ranges in time-varying tables cover all simulation periods
- [ ] Agent attribute names in AgentParams.csv match `agent.setup()` declarations

## tab2dict Integration (advanced, optional)

For datasets with 3+ lookup dimensions accessed per-agent per-timestep,
consider the `tab2dict` library (if installed). See `tab2dict-guide.md`.
Without tab2dict, use pandas DataFrames loaded in `Scenario.load_data()`.
