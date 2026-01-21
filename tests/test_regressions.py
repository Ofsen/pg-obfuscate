"""Regression tests for identified bugs."""

import pytest
import time
from pg_obfuscate.strategies.base import BaseStrategy
from pg_obfuscate.strategies.fake import FakeStrategy

def test_referential_integrity_with_groups():
    """
    Verify that consistency groups produce identical seeds for the same value
    across different tables/columns.
    """
    global_seed = 12345
    original_id = "user_123"
    group_name = "user_identity"
    
    # Obfuscating the same ID in two different tables with the SAME consistency group
    seed_table_users = BaseStrategy.compute_seed(
        global_seed, "public.users", "id", original_id, group=group_name
    )
    seed_table_orders = BaseStrategy.compute_seed(
        global_seed, "public.orders", "user_id", original_id, group=group_name
    )
    
    assert seed_table_users == seed_table_orders, (
        f"Referential integrity still broken even with groups: {seed_table_users} != {seed_table_orders}"
    )
    
    # Verify that WITHOUT group, they are still different (to avoid accidental collisions)
    seed_no_group_users = BaseStrategy.compute_seed(global_seed, "public.users", "id", original_id)
    seed_no_group_orders = BaseStrategy.compute_seed(global_seed, "public.orders", "user_id", original_id)
    assert seed_no_group_users != seed_no_group_orders

def test_fake_strategy_performance_overhead():
    """
    BUG: Frequent Faker.seed() calls cause significant performance overhead.
    """
    iterations = 1000
    strategy = FakeStrategy("email")
    
    start_time = time.time()
    for i in range(iterations):
        strategy.obfuscate(f"user_{i}@example.com", i)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time_ms = (total_time / iterations) * 1000
    
    # On most modern systems, 1000 calls to Faker.seed() plus generation 
    # should be much faster than 1ms per row if optimized. 
    # Current baseline is around 0.9ms per row.
    # We'll set a soft threshold of 0.5ms for now to highlight the issue, 
    # though this is environment dependent.
    assert avg_time_ms < 0.5, f"Performance too slow: {avg_time_ms:.4f}ms per row"
