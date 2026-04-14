"""Abstract base class for all reference checkers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

VerifyResult = Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]


class BaseChecker(ABC):
    """Abstract base for all reference checkers.

    Every checker receives a reference dict and returns:
        (verified_data, errors, url)
    where verified_data is the authoritative metadata or None.
    """

    @abstractmethod
    def verify_reference(self, reference: Dict[str, Any]) -> VerifyResult:
        ...
