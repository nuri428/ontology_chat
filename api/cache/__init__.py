"""Multi-level caching system for Ontology Chat."""

from .multi_level_cache import (
    MultiLevelCache,
    L1MemoryCache,
    L2RedisCache,
    L3DiskCache,
    CacheLevel,
    CacheEntry,
    CacheStats,
    multi_level_cache,
    cache_key_generator
)

from .cache_decorators import (
    multi_cache,
    l1_cache,
    l2_cache,
    l3_cache,
    tiered_cache,
    conditional_cache,
    cache_aside,
    cache_invalidation_group,
    monitored_cache,
    CachingContext,
    CacheMetrics,
    cache_metrics
)

from .cache_strategies import (
    CacheStrategy,
    WriteThrough,
    WriteBack,
    ReadThrough,
    RefreshAhead,
    CacheStrategyConfig,
    cache_strategy_manager
)

__all__ = [
    # Core classes
    "MultiLevelCache",
    "L1MemoryCache",
    "L2RedisCache",
    "L3DiskCache",
    "CacheLevel",
    "CacheEntry",
    "CacheStats",

    # Global instances
    "multi_level_cache",
    "cache_metrics",
    "cache_strategy_manager",

    # Decorators
    "multi_cache",
    "l1_cache",
    "l2_cache",
    "l3_cache",
    "tiered_cache",
    "conditional_cache",
    "cache_aside",
    "cache_invalidation_group",
    "monitored_cache",

    # Utilities
    "cache_key_generator",
    "CachingContext",
    "CacheMetrics",

    # Strategies
    "CacheStrategy",
    "WriteThrough",
    "WriteBack",
    "ReadThrough",
    "RefreshAhead",
    "CacheStrategyConfig"
]