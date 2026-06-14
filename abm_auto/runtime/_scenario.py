"""ABM Auto Runtime — ``Scenario``: the parameters for one run.

What this class does
--------------------
A Scenario carries the parameters for a single simulation run. Users
subclass it and override ``setup()`` to declare attributes; the framework
then overrides those attributes from a CSV row, and the resulting object is
handed to the Model.

Lifecycle (called by the framework, not by users):

    s = ScenarioCls()                # __init__
    s.manager = data_loader_or_sim   # framework injects
    s._setup(row_dict)               # setup() → setattr-from-row → load_data() → setup_data()

Per-run, the simulator deep-copies via ``s.copy()`` before assigning
``s.id_run``. The surface the orchestrator depends on is small and duck-typed:
``__init__()``, ``_setup(row)``, ``copy()``, ``to_dict()``, and the mutable
``manager`` / ``id_run`` attributes.
"""
from __future__ import annotations

import copy as _copy
from typing import Any, Optional, Union


class Scenario:
    """Scenario carrier: the parameters for one run.

    Subclass and override :meth:`setup` to declare scenario attributes.
    Framework-called hooks (``load_data``, ``setup_data``) default to
    no-ops; override only when you need them.

    Attributes set by ``__init__``:
      - id, id_run, run_num, period_num: scenario/run identifiers
      - manager: framework back-reference (Calibrator | Simulator | DataLoader),
        assigned by the framework after construction. ``None`` until then.
      - _parameters: unused list, kept for source-compat with any
        third-party code that mutates ``scenario._parameters``.
    """

    def __init__(self, id_scenario: Optional[Union[int, str]] = 0):
        if id_scenario is not None and not isinstance(id_scenario, (int, str)):
            raise TypeError(
                f"id_scenario must be int|str|None, got {type(id_scenario).__name__}"
            )
        self.id = id_scenario
        self.id_run: int = -1
        self.run_num: int = 1
        self.period_num: int = 0
        self.manager: Any = None
        self._parameters: list = []

    # ── user-overridable hooks ────────────────────────────────────────

    def setup(self) -> None:
        """Override to assign scenario attributes (parameters, sizes, seeds)."""

    def setup_data(self) -> None:
        """Override to pre-compute derived data after CSV load. Optional."""

    def load_data(self) -> None:
        """Override to load static data tables. Optional."""

    # ── framework-called lifecycle ────────────────────────────────────

    def _setup(self, data: Optional[dict] = None) -> None:
        """Lifecycle: ``setup()`` then setattr-from-row then ``load_data()``
        then ``setup_data()`` — declared defaults first, CSV overrides next, so
        a subclass sees row values by the time ``load_data``/``setup_data`` run.
        """
        self.setup()
        if data is not None:
            for col_name, value in data.items():
                setattr(self, col_name, value)
        self.load_data()
        self.setup_data()

    def initialize(self) -> None:
        """Manual lifecycle trigger (for standalone Scenario instantiation
        outside the standard Simulator loop)."""
        self._setup()

    def copy(self) -> "Scenario":
        """Deep copy. ``manager`` is INTENTIONALLY shallow — the framework
        re-assigns it after copy, and deepcopying would walk the entire
        DataLoader/Simulator graph."""
        new = self.__class__()
        for k, v in self.__dict__.items():
            if k == "manager":
                setattr(new, k, v)
            else:
                setattr(new, k, _copy.deepcopy(v))
        return new

    # ── observability ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Plain dict of public scenario attributes, for logging/reporting.
        Excludes the ``manager`` back-reference and any leading-underscore
        privates."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_") and k != "manager"
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} id_run={self.id_run}>"

    # ── data-loading proxies (delegate to manager.data_loader) ────────

    def load_dataframe(self, df_info: Any):
        """Delegate to the framework's data loader. Not used by any
        current handcrafted example; lands when Phase 2/3 ship our own
        DataLoader/AgentList replacements.
        """
        if self.manager is None or getattr(self.manager, "data_loader", None) is None:
            raise RuntimeError(
                "Scenario.load_dataframe() called without manager.data_loader. "
                "This path requires Phase 2/3 of ADR-009 to be in place."
            )
        return self.manager.data_loader.load_dataframe(df_info)

    def load_matrix(self, mat_info: Any):
        """Same as ``load_dataframe`` for matrices."""
        if self.manager is None or getattr(self.manager, "data_loader", None) is None:
            raise RuntimeError(
                "Scenario.load_matrix() called without manager.data_loader. "
                "This path requires Phase 2/3 of ADR-009 to be in place."
            )
        return self.manager.data_loader.load_matrix(mat_info)
