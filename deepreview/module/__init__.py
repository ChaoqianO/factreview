from .deepreview import DeepReview, OpenScholarClient
from .mamorx import Mamorx
from .agentreview import AgentReview

# Convenience alias to mirror the requested `deepreview(...)` style.
deepreview = DeepReview

__all__ = ["DeepReview", "OpenScholarClient", "deepreview", "Mamorx", "AgentReview"]