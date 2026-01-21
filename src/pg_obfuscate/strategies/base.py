"""Base strategy interface."""

import hashlib
from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    """Abstract base class for obfuscation strategies."""

    @abstractmethod
    def obfuscate(self, value: Any, seed: int) -> Any:
        """Obfuscate a value deterministically.
        
        Args:
            value: Original value to obfuscate
            seed: Seed for deterministic output
            
        Returns:
            Obfuscated value
        """
        pass

    @staticmethod
    def compute_seed(global_seed: int, table: str, column: str, value: Any) -> int:
        """Compute deterministic seed for a specific value.
        
        Args:
            global_seed: Global seed from config
            table: Table name
            column: Column name
            value: Original value
            
        Returns:
            Deterministic seed integer
        """
        combined = f"{global_seed}:{table}:{column}:{value}"
        # Use SHA-256 for stable determinism across runs/platforms
        digest = hashlib.sha256(combined.encode("utf-8")).digest()
        # Take first 8 bytes and convert to int
        return int.from_bytes(digest[:8], byteorder="big")
