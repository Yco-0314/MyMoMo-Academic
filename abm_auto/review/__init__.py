"""Peer-review sub-agent package.

Decomposes the historic `ReviewerAgent` god class (544 LoC) into one
adapter per reviewer concern, mirroring the Phase / CodegenFixup
decomposition patterns established earlier in v3.

Public surface:
    SubReviewer, REVIEWERS, run_panel
"""
from abm_auto.review.sub_reviewer import REVIEWERS, SubReviewer, run_panel

__all__ = ["SubReviewer", "REVIEWERS", "run_panel"]
