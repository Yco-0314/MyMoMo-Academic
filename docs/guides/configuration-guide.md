# Configuration Guide

## Overview

ABM-Auto supports flexible configuration through environment variables, CLI parameters, and configuration files. This guide covers all available configuration options.

## Memory System Configuration

### Memory Tier Sizes

Control the maximum number of entries in each memory tier:

```bash
# Environment variables
export ABM_WORKING_MEMORY_SIZE=20      # Default: 20
export ABM_EPISODIC_MEMORY_SIZE=1000   # Default: 1000
export ABM_SEMANTIC_MEMORY_SIZE=200    # Default: 200
```

### Token Budget Allocation

Configure token budget for memory retrieval:

```bash
export ABM_MEMORY_TOKEN_BUDGET=8000    # Default: 8000
```

Or use CLI parameters:

```bash
abm-auto run story.md --memory-budget 10000
```

## Timeout Configuration

### Phase-Specific Timeouts

Each pipeline phase has independent timeout control:

```bash
# Environment variables (in seconds)
export ABM_TIMEOUT_DESIGN=300          # Design phase (default: 300s)
export ABM_TIMEOUT_ODD=180             # ODD documentation (default: 180s)
export ABM_TIMEOUT_CODE=600            # Code generation (default: 600s)
export ABM_TIMEOUT_VERIFICATION=120    # Code verification (default: 120s)
export ABM_TIMEOUT_SIMULATION=300      # Simulation execution (default: 300s)
export ABM_TIMEOUT_ANALYSIS=180        # Analysis phase (default: 180s)
export ABM_TIMEOUT_SA=1800             # Sensitivity analysis (default: 1800s)
export ABM_TIMEOUT_OPTIMIZATION=180    # Optimization phase (default: 180s)
export ABM_TIMEOUT_REPORT=600          # Report generation (default: 600s)
export ABM_TIMEOUT_LLM=300             # LLM API calls (default: 300s)
```

### CLI Timeout Overrides

Override specific phase timeouts via CLI:

```bash
# Override simulation timeout
abm-auto run story.md --timeout-simulation 600

# Override sensitivity analysis timeout
abm-auto run story.md --timeout-sa 3600

# Override LLM API timeout
abm-auto run story.md --timeout-llm 450

# Global timeout (fallback for phases without specific config)
abm-auto run story.md --timeout 300
```

## Iteration and Sample Size Control

### Basic Usage

```bash
# Set number of iterations (default: 3)
abm-auto run story.md --iterations 10

# Set sensitivity analysis samples (default: 10 for Morris, 1024 for Sobol)
abm-auto run story.md --sensitivity sobol --sa-samples 2048
```

### Publication-Quality Configuration

For publication-ready results, combine multiple parameters:

```bash
abm-auto run story.md \
  --iterations 10 \
  --sensitivity sobol \
  --sa-samples 128 \
  --fetch-citations \
  --baseline baseline_results.csv \
  --timeout-sa 3600
```

## Citation and Baseline Comparison

### Enable Citation Fetching

```bash
# Fetch citations from Semantic Scholar and CrossRef
abm-auto run story.md --fetch-citations
```

### Baseline Comparison

```bash
# Compare results with original study
abm-auto run story.md --baseline path/to/baseline.csv
```

Expected CSV format:
```csv
metric,mean,std
cooperation_rate,0.65,0.08
average_wealth,1250.5,150.2
```

## Configuration Precedence

Configuration sources are applied in this order (later overrides earlier):

1. **Default values** in `config.py`
2. **Environment variables** (`ABM_*`)
3. **CLI parameters** (`--timeout-*`, `--iterations`, etc.)

## Example Configurations

### Quick Prototype (Fast)

```bash
abm-auto run story.md \
  --iterations 1 \
  --sensitivity morris \
  --timeout 120
```

### Standard Research (Balanced)

```bash
export ABM_TIMEOUT_SA=1800
export ABM_MEMORY_TOKEN_BUDGET=8000

abm-auto run story.md \
  --iterations 5 \
  --sensitivity sobol \
  --sa-samples 64
```

### Publication Quality (Thorough)

```bash
export ABM_TIMEOUT_SA=3600
export ABM_TIMEOUT_SIMULATION=600
export ABM_MEMORY_TOKEN_BUDGET=12000

abm-auto run story.md \
  --iterations 10 \
  --sensitivity sobol \
  --sa-samples 128 \
  --fetch-citations \
  --baseline original_study.csv
```

### Large-Scale Experiment (Maximum)

```bash
export ABM_TIMEOUT_SA=7200
export ABM_TIMEOUT_SIMULATION=1200
export ABM_EPISODIC_MEMORY_SIZE=2000
export ABM_MEMORY_TOKEN_BUDGET=16000

abm-auto run story.md \
  --iterations 20 \
  --sensitivity sobol \
  --sa-samples 256 \
  --fetch-citations \
  --timeout-llm 600
```

## Troubleshooting

### Timeout Issues

If you encounter timeout errors:

1. **Identify the failing phase** from error messages
2. **Increase phase-specific timeout**:
   ```bash
   export ABM_TIMEOUT_CODE=1200  # Double the default
   ```
3. **Or use CLI override**:
   ```bash
   abm-auto run story.md --timeout-simulation 900
   ```

### Memory Issues

If memory retrieval is slow or incomplete:

1. **Increase token budget**:
   ```bash
   export ABM_MEMORY_TOKEN_BUDGET=12000
   ```
2. **Adjust memory tier sizes**:
   ```bash
   export ABM_WORKING_MEMORY_SIZE=30
   export ABM_SEMANTIC_MEMORY_SIZE=300
   ```

### LLM API Timeouts

For complex models or slow API responses:

```bash
# Increase LLM timeout to 10 minutes
export ABM_TIMEOUT_LLM=600
abm-auto run story.md --timeout-llm 600
```

## See Also

- [ADR-001: Memory Architecture](../decisions/ADR-001-memory-architecture.md)
- [ADR-004: Configuration Flexibility](../decisions/ADR-004-configuration-flexibility.md)
- [FLEXIBILITY-AUDIT.md](../decisions/FLEXIBILITY-AUDIT.md)
