"""Null obfuscation strategy."""

from typing import Any

from pg_obfuscate.strategies.base import BaseStrategy


class NullStrategy(BaseStrategy):
    """Strategy that sets values to NULL."""

    def obfuscate(self, value: Any, seed: int) -> None:
        """Return NULL regardless of input.
        
        Args:
            value: Original value (ignored)
            seed: Seed (ignored)
            
        Returns:
            None (SQL NULL)
        """
        return None
