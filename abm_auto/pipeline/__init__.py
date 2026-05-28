"""ABM Auto Pipeline package.

Public surface: `from abm_auto.pipeline import Pipeline` (unchanged from
the legacy single-file module).
"""
from abm_auto.pipeline.pipeline import Pipeline
from abm_auto.pipeline.phase import LoopedPhase, Phase, PipelineContext

__all__ = ["Pipeline", "Phase", "PipelineContext", "LoopedPhase"]
