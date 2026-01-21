"""Preserve obfuscation strategy."""

from typing import Any

from pg_obfuscate.strategies.base import BaseStrategy


class PreserveStrategy(BaseStrategy):
    """Strategy that preserves original values."""

    def obfuscate(self, value: Any, seed: int) -> Any:
        """Return original value unchanged.
        
        Args:
            value: Original value
            seed: Seed (ignored)
            
        Returns:
            Original value unchanged
        """
        return value
