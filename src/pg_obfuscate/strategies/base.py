"""Base strategy interface."""

import hashlib
from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    """Abstract base class for obfuscation strategies."""

    @abstractmethod
    def obfuscate(self, value: Any, seed: int, column_type: str | None = None) -> Any:
        """Obfuscate a value deterministically.
        
        Args:
            value: Original value to obfuscate
            seed: Seed for deterministic output
            column_type: Optional database column type for enforcing limits
            
        Returns:
            Obfuscated value
        """
        pass

    @staticmethod
    def compute_seed(global_seed: int, table: str, column: str, value: Any, group: str | None = None) -> int:
        """Compute deterministic seed for a specific value.
        
        Args:
            global_seed: Global seed from config
            table: Table name
            column: Column name
            value: Original value
            group: Optional consistency group name
            
        Returns:
            Deterministic seed integer
        """
        if group:
            # When a group is provided, we ignore table and column names
            # to ensure consistent seeding across different tables/columns.
            combined = f"{global_seed}:group:{group}:{value}"
        else:
            combined = f"{global_seed}:{table}:{column}:{value}"
            
        # Use SHA-256 for stable determinism across runs/platforms
        digest = hashlib.sha256(combined.encode("utf-8")).digest()
        # Take first 8 bytes and convert to int
        return int.from_bytes(digest[:8], byteorder="big")
