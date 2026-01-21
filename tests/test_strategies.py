"""Unit tests for fake strategy."""

import pytest
from pg_obfuscate.strategies.fake import FakeStrategy
from decimal import Decimal

def test_fake_text_types():
    strategy = FakeStrategy("email")
    val1 = strategy.obfuscate("original", 123)
    val2 = strategy.obfuscate("original", 123)
    val3 = strategy.obfuscate("original", 456)
    
    assert "@" in val1
    assert val1 == val2  # Deterministic with same seed
    assert val1 != val3  # Different seed = different value

def test_fake_numeric_matching_int():
    strategy = FakeStrategy("int")
    
    # Single digit -> single digit
    val = strategy.obfuscate(5, 123)
    assert isinstance(val, int)
    assert 0 <= val <= 9
    
    # 3 digits -> 3 digits
    val = strategy.obfuscate(123, 123)
    assert 100 <= val <= 999

def test_fake_numeric_matching_decimal():
    strategy = FakeStrategy("decimal")
    
    # 2 decimal places -> 2 decimal places
    val = strategy.obfuscate(12.34, 123)
    assert isinstance(val, Decimal)
    assert abs(val).as_tuple().exponent == -2
    
    # Magnitude matching (10-99)
    assert 10 <= val <= 99

def test_fake_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported fake type"):
        FakeStrategy("invalid_type")

def test_fake_null_handling():
    strategy = FakeStrategy("email")
    assert strategy.obfuscate(None, 123) is None
