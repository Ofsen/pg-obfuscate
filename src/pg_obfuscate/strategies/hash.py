"""Hash obfuscation strategy."""

import hashlib
from typing import Any

from pg_obfuscate.strategies.base import BaseStrategy


class HashStrategy(BaseStrategy):
    """SHA256 hash obfuscation strategy."""

    def obfuscate(self, value: Any, seed: int, column_type: str | None = None) -> str:
        """Hash value with seed salt.
        
        Args:
            value: Original value to hash
            seed: Seed used as salt
            
        Returns:
            Hexadecimal hash string
        """
        if value is None:
            return None
        
        # Combine seed as salt with value
        salted = f"{seed}:{value}"
        return hashlib.sha256(salted.encode()).hexdigest()
