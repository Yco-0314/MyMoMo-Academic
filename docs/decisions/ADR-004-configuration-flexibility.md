# ADR-004: Configuration Flexibility Strategy

**Status**: Proposed  
**Date**: 2026-04-30  
**Deciders**: Core team  
**Related**: [ADR-001](ADR-001-memory-architecture.md), [ADR-002](ADR-002-flat-file-storage.md)

---

## Context and Problem Statement

Current implementation contains several hardcoded limits that reduce system flexibility:

### Identified Inflexibilities

1. **Memory Tier Sizes** (hardcoded in `memory/store.py`)
   - `WorkingMemory.MAX_ENTRIES = 20`
   - `SemanticMemory.MAX_ENTRIES = 200`
   - No user control over these limits

2. **Enhanced Mode Multipliers** (hardcoded in `config.py`)
   - `ENHANCED_ITERATIONS = 10`
   - `ENHANCED_SA_SAMPLES = 100`
   - `ENHANCED_AGENT_MULTIPLIER = 2.0`
   - `ENHANCED_TIMESTEPS_MULTIPLIER = 2.0`
   - Binary choice (default vs enhanced), no fine-tuning

3. **Token Estimation** (hardcoded in `memory/store.py`)
   - `estimate_tokens(text) = len(text) // 3`
   - Assumes mixed CJK/English, inaccurate for pure English/Chinese

4. **Retry/Timeout Defaults** (hardcoded in `config.py`)
   - `DEFAULT_MAX_RETRIES = 5`
   - `DEFAULT_TIMEOUT = 300`
   - No per-phase customization (verification vs simulation may need different limits)

5. **Model Selection** (limited flexibility)
   - Only `DEFAULT_MODEL` and `STRONG_MODEL`
   - No per-agent model override (e.g., use Haiku for verification, Opus for design)

---

## Decision Drivers

1. **User Control** — Advanced users should tune system behavior without code changes
2. **Sensible Defaults** — Beginners should get good results without configuration
3. **Cost Optimization** — Users should balance quality vs API cost
4. **Experiment Reproducibility** — Configuration should be version-controlled
5. **Progressive Disclosure** — Simple cases stay simple, complex cases become possible

---

## Proposed Solution

### Hierarchical Configuration System

**Priority Order**: CLI args > Project config (`.abm-auto.yml`) > User config (`~/.abm-auto/config.yml`) > System defaults

### Configuration Schema

```yaml
# .abm-auto.yml (project-level)
models:
  default: claude-sonnet-4-6
  strong: claude-opus-4-6
  agents:
    designer: claude-opus-4-6      # Override for specific agent
    coder: claude-opus-4-6
    verifier: claude-sonnet-4-6
    analyzer: claude-sonnet-4-6
    optimizer: claude-sonnet-4-6
    reporter: claude-opus-4-6

memory:
  budget: 8000                      # Total token budget
  allocation:
    working: 0.14
    episodic: 0.43
    semantic: 0.43
  limits:
    working_max_entries: 30         # Override hardcoded 20
    semantic_max_entries: 500       # Override hardcoded 200
  token_estimation:
    method: tiktoken                # tiktoken | simple | custom
    chars_per_token: 3              # For simple method

pipeline:
  iterations: 5
  max_retries: 5
  timeout: 300
  per_phase_timeout:
    verification: 120
    simulation: 600
    sensitivity_analysis: 1800

enhanced_mode:
  iterations: 10
  sa_samples: 100
  agent_multiplier: 2.0
  timesteps_multiplier: 2.0
  # Or allow custom scaling
  custom_scaling:
    agent_count: 1000               # Absolute value instead of multiplier
    timesteps: 500

sensitivity_analysis:
  morris:
    trajectories: 10                # Default
    enhanced_trajectories: 20       # Enhanced mode
  sobol:
    base_samples: 32                # Default
    enhanced_samples: 64            # Enhanced mode
  
citation:
  max_results: 20
  apis:
    - semantic_scholar
    - crossref
  cache_ttl: 86400                  # 24 hours

output:
  language: zh                      # zh | en
  report_length: medium             # short (3000) | medium (5000) | long (8000) words
  include_code: false
  include_raw_data: false
```

---

## Implementation Strategy

### Phase 1: Config File Support (High Priority)

**Changes**:
1. Add `pydantic` for schema validation
2. Create `ConfigManager` class to load/merge configs
3. Update `Pipeline.__init__()` to accept config object
4. Add `abm-auto config validate` command

**Example**:
```python
from pydantic import BaseModel, Field

class MemoryConfig(BaseModel):
    budget: int = 3500
    allocation: dict[str, float] = {"working": 0.14, "episodic": 0.43, "semantic": 0.43}
    limits: dict[str, int] = {"working_max_entries": 20, "semantic_max_entries": 200}

class PipelineConfig(BaseModel):
    iterations: int = 3
    max_retries: int = 5
    timeout: int = 300
    per_phase_timeout: dict[str, int] = Field(default_factory=dict)

class ABMAutoConfig(BaseModel):
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    # ... other sections
```

### Phase 2: Per-Agent Model Selection (Medium Priority)

**Changes**:
1. Add `agent_models` dict to config
2. Update agent initialization to check config first
3. Add cost estimation command: `abm-auto estimate-cost story.md --config .abm-auto.yml`

**Example**:
```python
class Pipeline:
    def __init__(self, config: ABMAutoConfig):
        agent_models = config.models.agents
        self.designer = DesignAgent(
            self.client, 
            self.workspace, 
            model=agent_models.get("designer", config.models.strong)
        )
```

### Phase 3: Dynamic Scaling (Low Priority)

**Changes**:
1. Replace binary `--enhanced` flag with `--profile` (minimal/default/enhanced/custom)
2. Allow custom profiles in config file
3. Add validation to prevent unrealistic values

**Example**:
```yaml
profiles:
  quick_test:
    iterations: 1
    sa_samples: 10
    agent_count: 100
  
  publication:
    iterations: 20
    sa_samples: 200
    agent_count: 5000
    timesteps: 1000
```

---

## Consequences

### Positive

✅ **User Empowerment**: Advanced users can fine-tune every aspect  
✅ **Cost Control**: Per-agent model selection reduces API costs  
✅ **Reproducibility**: Config files can be version-controlled  
✅ **Experimentation**: Easy to A/B test different configurations  
✅ **Documentation**: Config schema serves as self-documenting reference

### Negative

⚠️ **Complexity**: More configuration options = steeper learning curve  
⚠️ **Validation Burden**: Need to validate all config combinations  
⚠️ **Breaking Changes**: Existing CLI workflows may need updates  
⚠️ **Maintenance**: Config schema must stay in sync with code

### Risks

🔴 **Configuration Explosion**: Too many options overwhelm users  
**Mitigation**: Use progressive disclosure (simple defaults, advanced options hidden in docs)

🔴 **Invalid Configurations**: Users set contradictory values  
**Mitigation**: Pydantic validation + `abm-auto config validate` command

🔴 **Version Skew**: Old config files break on new versions  
**Mitigation**: Config schema versioning + migration tool

---

## Migration Path

### Backward Compatibility

**Phase 1 (v0.2.0)**: Config file support added, CLI args still work  
**Phase 2 (v0.3.0)**: Deprecation warnings for hardcoded values  
**Phase 3 (v1.0.0)**: Remove hardcoded limits, require config for non-default values

### Example Migration

**Before (v0.1.x)**:
```bash
abm-auto run story.md --iterations 10 --enhanced
```

**After (v0.2.0+)**:
```bash
# Option 1: CLI args (still works)
abm-auto run story.md --iterations 10 --enhanced

# Option 2: Config file (recommended)
abm-auto run story.md --config .abm-auto.yml
```

**Config file**:
```yaml
pipeline:
  iterations: 10
enhanced_mode:
  enabled: true
```

---

## Alternatives Considered

### Option 1: Environment Variables Only
**Reason Rejected**: Not version-controllable, hard to share across team

### Option 2: Python Config Files (`.py`)
**Reason Rejected**: Security risk (arbitrary code execution), harder to parse

### Option 3: TOML Format
**Reason Rejected**: Less familiar to researchers than YAML, no nested structure advantage

### Option 4: Keep Hardcoded Values
**Reason Rejected**: Limits advanced users, forces code changes for tuning

---

## Implementation Checklist

- [ ] Add `pydantic` dependency
- [ ] Create `abm_auto/config_schema.py` with Pydantic models
- [ ] Create `abm_auto/config_manager.py` for loading/merging
- [ ] Update `Pipeline.__init__()` to accept config object
- [ ] Update `WorkingMemory` and `SemanticMemory` to accept max_entries param
- [ ] Add `abm-auto config validate` command
- [ ] Add `abm-auto config init` command (generate template)
- [ ] Update CLI to load config file via `--config` flag
- [ ] Write migration guide in docs
- [ ] Add config examples to `examples/` directory
- [ ] Update all documentation to reference config file approach

---

## Related Decisions

- **ADR-001**: Memory architecture (now configurable via `memory.limits`)
- **ADR-002**: Flat file storage (config files also use flat files)
- **ADR-003**: LLM orchestration (now supports per-agent model selection)

---

## References

- [12-Factor App: Config](https://12factor.net/config)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [YAML Specification](https://yaml.org/spec/1.2.2/)

---

## Changelog

- **2026-04-30**: Initial proposal (ADR-004)
