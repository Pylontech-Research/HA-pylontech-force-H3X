"""Small, Home Assistant-independent polling resilience helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PollFailureState:
    """Track whether a failed poll may temporarily reuse the last snapshot."""

    failure_threshold: int
    consecutive_failures: int = 0
    stale: bool = False

    def record_failure(self, *, has_snapshot: bool) -> bool:
        """Return whether the previous snapshot should be preserved."""
        self.consecutive_failures += 1
        self.stale = has_snapshot
        return has_snapshot and self.consecutive_failures < self.failure_threshold

    def record_success(self) -> int:
        """Reset the failure state and return the previous failure count."""
        previous_failures = self.consecutive_failures
        self.consecutive_failures = 0
        self.stale = False
        return previous_failures
