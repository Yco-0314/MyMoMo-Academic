from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# --- Path roots -----------------------------------------------------------
# Package-data root: the installed ``abm_auto/`` directory. Bundled data
# (prompts, knowledge, runtime templates, quickstart assets) resolves from here
# so it works identically in a dev tree and an installed wheel.
_PKG_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = _PKG_DIR / "prompts"
KNOWLEDGE_DIR = _PKG_DIR / "mymomo_knowledge"
TEMPLATES_DIR = _PKG_DIR / "runtime_templates"
QUICKSTART_DIR = _PKG_DIR / "quickstart_assets"

# Kept ONLY so executor.py can put the import root on a subprocess PYTHONPATH
# (so generated model code can ``import abm_auto``). Same value as before:
# repo root in a dev tree, site-packages in an installed wheel — both correct.
PROJECT_ROOT = _PKG_DIR.parent

# User/runtime paths resolve from the working directory, never site-packages.
load_dotenv(find_dotenv(usecwd=True), override=True)  # find user's .env from CWD up
WORKSPACE_DIR = Path(os.getenv("ABM_WORKSPACE_DIR", str(Path.cwd() / "workspace")))

# LLM provider selection — controls which SDK + API key is used.
# Set in .env:  LLM_PROVIDER=anthropic  (default)  OR  LLM_PROVIDER=deepseek
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", None)

# DeepSeek (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Default models — provider-dependent. Override per-call via ABM_MODEL / ABM_STRONG_MODEL.
if LLM_PROVIDER == "deepseek":
    DEFAULT_MODEL = os.getenv("ABM_MODEL", "deepseek-chat")
    STRONG_MODEL = os.getenv("ABM_STRONG_MODEL", "deepseek-reasoner")
else:
    DEFAULT_MODEL = os.getenv("ABM_MODEL", "claude-sonnet-4-6")
    STRONG_MODEL = os.getenv("ABM_STRONG_MODEL", "claude-opus-4-6")


def get_api_key() -> str:
    """Return the API key for the active provider."""
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_API_KEY
    return ANTHROPIC_API_KEY


def get_base_url() -> str | None:
    """Return the base URL for the active provider (None = SDK default)."""
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_BASE_URL
    return ANTHROPIC_BASE_URL

# Simulation defaults
DEFAULT_ITERATIONS = 3
DEFAULT_MAX_RETRIES = 5
DEFAULT_TIMEOUT = 300  # seconds per simulation run

# Phase-specific timeouts (seconds)
PHASE_TIMEOUTS = {
    "design": int(os.getenv("ABM_TIMEOUT_DESIGN", "300")),
    "odd": int(os.getenv("ABM_TIMEOUT_ODD", "180")),
    "code": int(os.getenv("ABM_TIMEOUT_CODE", "600")),
    "verification": int(os.getenv("ABM_TIMEOUT_VERIFICATION", "120")),
    "simulation": int(os.getenv("ABM_TIMEOUT_SIMULATION", "300")),
    "analysis": int(os.getenv("ABM_TIMEOUT_ANALYSIS", "180")),
    "sensitivity_analysis": int(os.getenv("ABM_TIMEOUT_SA", "1800")),
    "optimization": int(os.getenv("ABM_TIMEOUT_OPTIMIZATION", "180")),
    "report": int(os.getenv("ABM_TIMEOUT_REPORT", "600")),
    "llm": int(os.getenv("ABM_TIMEOUT_LLM", "300")),  # Anthropic client timeout
}

# Memory system configuration
WORKING_MEMORY_MAX_ENTRIES = int(os.getenv("ABM_WORKING_MEMORY_SIZE", "20"))
EPISODIC_MEMORY_MAX_ENTRIES = int(os.getenv("ABM_EPISODIC_MEMORY_SIZE", "1000"))  # Append-only, rarely pruned
SEMANTIC_MEMORY_MAX_ENTRIES = int(os.getenv("ABM_SEMANTIC_MEMORY_SIZE", "200"))
MEMORY_TOKEN_BUDGET = int(os.getenv("ABM_MEMORY_TOKEN_BUDGET", "3500"))

# Memory token allocation ratios (must sum to 1.0)
MEMORY_ALLOCATION_RATIOS = {
    "working": float(os.getenv("ABM_MEMORY_RATIO_WORKING", "0.14")),
    "episodic": float(os.getenv("ABM_MEMORY_RATIO_EPISODIC", "0.43")),
    "semantic": float(os.getenv("ABM_MEMORY_RATIO_SEMANTIC", "0.43")),
}

# Publication-quality defaults (users can override via CLI)
# Example: abm-auto run story.md --iterations 10 --sa-samples 100 --fetch-citations
PUBLICATION_ITERATIONS = 10  # More optimization cycles
PUBLICATION_SA_SAMPLES = 100  # Larger sensitivity analysis sample size


def get_phase_timeout(phase: str, default: int = DEFAULT_TIMEOUT) -> int:
    """Get timeout for a specific pipeline phase."""
    return PHASE_TIMEOUTS.get(phase, default)


def allocate_memory_budget(total_budget: int | None = None) -> dict[str, int]:
    """
    Allocate token budget across memory tiers.

    Args:
        total_budget: Total tokens to allocate (default: MEMORY_TOKEN_BUDGET)

    Returns:
        Dict with keys: working, episodic, semantic
    """
    total = total_budget or MEMORY_TOKEN_BUDGET
    ratios = MEMORY_ALLOCATION_RATIOS

    # Apply constraints
    working = max(200, min(1000, int(total * ratios["working"])))
    remaining = total - working

    episodic_ratio = ratios["episodic"] / (ratios["episodic"] + ratios["semantic"])
    episodic = max(500, int(remaining * episodic_ratio))
    semantic = max(500, remaining - episodic)

    return {
        "working": working,
        "episodic": episodic,
        "semantic": semantic,
    }

