"""
ABM Auto Runtime — ``Environment``: shared, global run state.

The environment holds the global state agents read and update. It is created
once per run by ``Model.create_environment()`` and carries ``model`` /
``scenario`` refs plus a ``setup()`` hook. A thin base (serialization +
lifecycle, via ``_Element``) so generated environment classes stay small.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass  # avoid circular imports; model/scenario are set at runtime


class Environment:
    """Base class for ABM Auto simulation environments.

    The environment holds global (shared) state that agents read and update.
    It is created once per run by ``Model.create_environment()``.

    Lifecycle::

        model.create_environment(MyEnvironment)
            → env.model   = model          # set by Model
            → env.scenario = model.scenario # set by Model
            → env.setup()                  # called by framework

    Subclass pattern::

        class MyEnvironment(Environment):
            def setup(self):
                self.price: float = 0.0
                self.total_infected: int = 0

            def step(self, agents=None):
                self.total_infected = sum(a.state == 1 for a in agents)
    """

    def __init__(self) -> None:
        self.model: Optional[Any] = None
        self.scenario: Optional[Any] = None

    def setup(self) -> None:
        """Declare and initialise environment-level state variables.

        Called once at the start of each simulation run, after ``self.scenario``
        is set.  Use scenario parameters freely here.
        """

    def step(self, agents: Any = None) -> None:
        """Advance global state by one time step.

        Called from ``Model.run()`` once per period.  Override this to update
        any global metrics, apply policies, or compute aggregate outputs.

        :param agents: The model's AgentList, passed in from ``Model.run()``.
        """

    def to_dict(self, properties: List[str] = None) -> Dict[str, Any]:
        """Serialise environment properties to a plain dict.

        Used by DataCollector when collecting environment-level metrics.

        :param properties: List of attribute names to include.  If None,
            all public instance attributes are included.
        """
        if properties is None:
            properties = [k for k in self.__dict__ if not k.startswith("_")]
        return {p: self.__dict__[p] for p in properties if p in self.__dict__}

    # Internal hook called by the framework — do not override
    def _setup(self) -> None:
        self.setup()
