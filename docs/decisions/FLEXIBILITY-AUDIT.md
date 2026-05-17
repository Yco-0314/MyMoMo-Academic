# Architecture Flexibility Audit

**Date**: 2026-04-30  
**Auditor**: System review  
**Scope**: Identify hardcoded limits and inflexible design patterns

---

## Executive Summary

**Total Issues Found**: 12  
**Critical (blocks user workflows)**: 3  
**Major (limits advanced use)**: 5  
**Minor (quality-of-life)**: 4

**Recommended Action**: Implement hierarchical configuration system (see [ADR-004](ADR-004-configuration-flexibility.md))

---

## Critical Issues

### 1. Memory Tier Size Limits (Critical)

**Location**: `abm_auto/memory/store.py`

```python
class WorkingMemory:
    MAX_ENTRIES = 20  # Hardcoded

class SemanticMemory:
    MAX_ENTRIES = 200  # Hardcoded
```

**Problem**: Users running large-scale experiments (100+ iterations) hit semantic memory limit, causing knowledge loss.

**Impact**: 
- Long-running experiments lose early insights
- No way to preserve all cross-run patterns
- Forces manual memory management

**Proposed Fix**:
```python
class WorkingMemory:
    def __init__(self, path: Path, max_entries: int = 20):
        self.max_entries = max_entries
        # ...

# Usage
config = load_config()
working_mem = WorkingMemory(path, max_entries=config.memory.limits.working_max_entries)
```

**Priority**: High (implement in Phase 1)

---

### 2. Binary Enhanced Mode (Critical)

**Location**: `abm_auto/config.py`

```python
ENHANCED_ITERATIONS = 10
ENHANCED_SA_SAMPLES = 100
ENHANCED_AGENT_MULTIPLIER = 2.0
ENHANCED_TIMESTEPS_MULTIPLIER = 2.0
```

**Problem**: Only two modes (default vs enhanced), no fine-grained control.

**User Scenario**:
- Researcher wants 15 iterations (not 3 or 10)
- Needs 3x agent scaling (not 1x or 2x)
- Wants to test different SA sample sizes

**Current Workaround**: Edit source code

**Proposed Fix**: Profile-based configuration
```yaml
profiles:
  quick_test:
    iterations: 1
    sa_samples: 10
  
  my_custom:
    iterations: 15
    sa_samples: 150
    agent_multiplier: 3.0
```

**Priority**: High (implement in Phase 3)

---

### 3. No Per-Phase Timeout Control (Critical)

**Location**: `abm_auto/config.py`

```python
DEFAULT_TIMEOUT = 300  # seconds per simulation run
```

**Problem**: Single timeout for all phases, but phases have vastly different durations:
- Verification: ~30s
- Simulation: ~120s
- Sensitivity Analysis: ~1800s (30 min for large parameter spaces)

**Impact**: 
- SA phase times out prematurely
- Or verification phase waits unnecessarily long

**Proposed Fix**:
```yaml
pipeline:
  timeout: 300  # Default fallback
  per_phase_timeout:
    verification: 120
    simulation: 600
    sensitivity_analysis: 1800
    report_generation: 300
```

**Priority**: High (implement in Phase 1)

---

## Major Issues

### 4. Token Estimation Inaccuracy (Major)

**Location**: `abm_auto/memory/store.py`

```python
def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // 3)
```

**Problem**: 
- Assumes 3 chars/token (optimized for mixed CJK/English)
- Pure English: ~4 chars/token (underestimates by 25%)
- Pure Chinese: ~2 chars/token (overestimates by 33%)

**Impact**: Memory budget allocation is inaccurate, leading to:
- Context overflow (underestimation)
- Wasted context space (overestimation)

**Proposed Fix**:
```yaml
memory:
  token_estimation:
    method: tiktoken  # tiktoken | simple | custom
    chars_per_token: 3  # For simple method
```

```python
def estimate_tokens(text: str, method: str = "simple", chars_per_token: int = 3) -> int:
    if method == "tiktoken":
        import tiktoken
        enc = tiktoken.encoding_for_model("claude-sonnet-4-6")
        return len(enc.encode(text))
    elif method == "simple":
        return max(1, len(text) // chars_per_token)
    else:
        raise ValueError(f"Unknown method: {method}")
```

**Priority**: Medium (implement in Phase 1)

---

### 5. No Per-Agent Model Selection (Major)

**Location**: `abm_auto/pipeline.py`

```python
def __init__(self, ..., model: str = config.DEFAULT_MODEL):
    # All agents use same model
    self.designer = DesignAgent(self.client, self.workspace, model)
    self.coder = CoderAgent(self.client, self.workspace, model)
    # ...
```

**Problem**: Cannot optimize cost by using:
- Opus for design/reporting (creative tasks)
- Sonnet for coding/analysis (structured tasks)
- Haiku for verification (simple checks)

**Cost Impact**: Using Opus for all agents costs ~5x more than mixed approach

**Proposed Fix**:
```yaml
models:
  default: claude-sonnet-4-6
  strong: claude-opus-4-6
  agents:
    designer: claude-opus-4-6
    coder: claude-sonnet-4-6
    verifier: claude-haiku-4-5
    analyzer: claude-sonnet-4-6
    optimizer: claude-sonnet-4-6
    reporter: claude-opus-4-6
```

**Priority**: Medium (implement in Phase 2)

---

### 6. Fixed Retry Strategy (Major)

**Location**: `abm_auto/config.py`

```python
DEFAULT_MAX_RETRIES = 5
```

**Problem**: 
- Same retry count for all error types
- No exponential backoff configuration
- No per-agent retry limits

**Scenarios**:
- Syntax errors: 5 retries reasonable
- API rate limits: Need exponential backoff
- Logic errors: May need 10+ retries

**Proposed Fix**:
```yaml
pipeline:
  max_retries: 5
  retry_strategy:
    syntax_errors: 5
    logic_errors: 10
    api_errors: 3
    backoff:
      initial_delay: 1
      max_delay: 60
      multiplier: 2
```

**Priority**: Medium (implement in Phase 2)

---

### 7. No Output Customization (Major)

**Location**: Hardcoded in `abm_auto/agents/reporter.py`

**Problem**: Report format is fixed:
- Always includes full code listing
- Always generates 5000+ word reports
- No language selection (always uses prompt language)

**User Needs**:
- Short reports for internal review (2000 words)
- Long reports for journal submission (8000 words)
- Exclude code for non-technical audiences
- Bilingual output (Chinese + English)

**Proposed Fix**:
```yaml
output:
  language: zh  # zh | en | bilingual
  report_length: medium  # short (3000) | medium (5000) | long (8000)
  include_code: false
  include_raw_data: false
  format: markdown  # markdown | latex | docx
```

**Priority**: Medium (implement in Phase 2)

---

### 8. Citation Fetcher Limits (Major)

**Location**: `abm_auto/agents/citation_fetcher.py`

```python
def search_semantic_scholar(self, query: str, limit: int = 10):
    # Hardcoded limit
```

**Problem**: 
- Fixed 10 results per query
- No API preference (always tries Semantic Scholar first)
- No caching configuration

**Proposed Fix**:
```yaml
citation:
  max_results: 20
  apis:
    - semantic_scholar
    - crossref
  cache_ttl: 86400  # 24 hours
  fallback_on_failure: true
```

**Priority**: Low (implement in Phase 3)

---

## Minor Issues

### 9. No Workspace Cleanup Policy (Minor)

**Location**: `abm_auto/pipeline.py`

**Problem**: Workspace accumulates files across runs, no automatic cleanup

**Proposed Fix**:
```yaml
workspace:
  cleanup_policy: on_success  # never | on_success | always
  keep_last_n_runs: 5
```

**Priority**: Low

---

### 10. Fixed Knowledge Base Path (Minor)

**Location**: `abm_auto/config.py`

```python
KNOWLEDGE_DIR = PROJECT_ROOT / "abm_auto" / "knowledge"
```

**Problem**: Cannot add custom knowledge files without modifying package

**Proposed Fix**:
```yaml
knowledge:
  base_dirs:
    - ~/.abm-auto/knowledge  # User-level
    - ./.abm-auto/knowledge  # Project-level
    - <package>/knowledge    # System-level
```

**Priority**: Low

---

### 11. No Logging Configuration (Minor)

**Location**: Hardcoded `print()` statements throughout

**Problem**: 
- Cannot control verbosity
- No structured logging
- No log file output

**Proposed Fix**:
```yaml
logging:
  level: INFO  # DEBUG | INFO | WARNING | ERROR
  format: structured  # simple | structured | json
  output:
    - console
    - file: ~/.abm-auto/logs/abm-auto.log
```

**Priority**: Low

---

### 12. No Parallel Execution Control (Minor)

**Location**: Sequential execution in `pipeline.py`

**Problem**: Cannot parallelize independent runs (e.g., 10 iterations with different seeds)

**Proposed Fix**:
```yaml
execution:
  parallel: true
  max_workers: 4
  batch_size: 10
```

**Priority**: Low (future enhancement)

---

## Summary Table

| Issue | Location | Severity | Phase | Effort |
|-------|----------|----------|-------|--------|
| Memory tier limits | `memory/store.py` | Critical | 1 | 2h |
| Binary enhanced mode | `config.py` | Critical | 3 | 4h |
| No per-phase timeout | `config.py` | Critical | 1 | 1h |
| Token estimation | `memory/store.py` | Major | 1 | 3h |
| No per-agent models | `pipeline.py` | Major | 2 | 4h |
| Fixed retry strategy | `config.py` | Major | 2 | 3h |
| No output customization | `agents/reporter.py` | Major | 2 | 4h |
| Citation limits | `agents/citation_fetcher.py` | Major | 3 | 2h |
| No workspace cleanup | `pipeline.py` | Minor | 3 | 2h |
| Fixed knowledge path | `config.py` | Minor | 3 | 1h |
| No logging config | Throughout | Minor | 3 | 4h |
| No parallel execution | `pipeline.py` | Minor | Future | 8h |

**Total Estimated Effort**: 38 hours (1 week)

---

## Recommended Implementation Order

### Phase 1: Core Flexibility (Week 1)
- Memory tier limits
- Per-phase timeout
- Token estimation
- Config file infrastructure

**Deliverable**: Users can tune memory and timeout via `.abm-auto.yml`

### Phase 2: Cost Optimization (Week 2)
- Per-agent model selection
- Retry strategy
- Output customization

**Deliverable**: Users can reduce API costs by 50%+ via smart model selection

### Phase 3: Advanced Features (Week 3)
- Profile-based scaling
- Citation configuration
- Workspace cleanup
- Knowledge path customization
- Logging configuration

**Deliverable**: Power users have full control over system behavior

---

## Migration Strategy

1. **v0.2.0**: Add config file support, keep CLI args working
2. **v0.3.0**: Deprecation warnings for hardcoded values
3. **v1.0.0**: Remove hardcoded limits, require config for non-defaults

**Backward Compatibility**: All existing CLI workflows continue working through v0.3.x

---

## References

- [ADR-004: Configuration Flexibility Strategy](ADR-004-configuration-flexibility.md)
- [12-Factor App: Config](https://12factor.net/config)
- [Pydantic Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
