from __future__ import annotations

import os
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar

import numpy as np


K = TypeVar("K")
V = TypeVar("V")

_DEFAULT_CACHE_MB = 256
_MAX_CACHE_MB = 2048


def effect_cache_budget_bytes() -> int:
    """Return the per-renderer cache budget, configurable without code edits."""
    try:
        megabytes = int(os.environ.get("AI_EDITOR_EFFECT_CACHE_MB", _DEFAULT_CACHE_MB))
    except ValueError:
        megabytes = _DEFAULT_CACHE_MB
    return max(0, min(_MAX_CACHE_MB, megabytes)) * 1024 * 1024


def estimate_nbytes(value: object, seen: set[int] | None = None) -> int:
    """Estimate retained array/byte storage without recursively double-counting."""
    visited = seen if seen is not None else set()
    identity = id(value)
    if identity in visited:
        return 0
    visited.add(identity)
    if isinstance(value, np.ndarray):
        return int(value.nbytes)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return len(value)
    if isinstance(value, Mapping):
        return sum(
            estimate_nbytes(key, visited) + estimate_nbytes(item, visited)
            for key, item in value.items()
        )
    if isinstance(value, (tuple, list, set, frozenset)):
        return sum(estimate_nbytes(item, visited) for item in value)
    return 0


@dataclass(frozen=True, slots=True)
class CacheInfo:
    entries: int
    current_bytes: int
    max_bytes: int
    hits: int
    misses: int
    evictions: int


class ByteBudgetLRU(Generic[K, V]):
    """Small thread-safe LRU that evicts by retained byte size, not item count."""

    def __init__(
        self,
        max_bytes: int,
        *,
        size_of: Callable[[V], int] = estimate_nbytes,
    ) -> None:
        self.max_bytes = max(0, int(max_bytes))
        self._size_of = size_of
        self._items: OrderedDict[K, tuple[V, int]] = OrderedDict()
        self._current_bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = RLock()

    def get_or_create(self, key: K, factory: Callable[[], V]) -> V:
        with self._lock:
            cached = self._items.pop(key, None)
            if cached is not None:
                self._items[key] = cached
                self._hits += 1
                return cached[0]
            self._misses += 1
            value = factory()
            self._put_locked(key, value)
            return value

    def put(self, key: K, value: V) -> None:
        with self._lock:
            self._put_locked(key, value)

    def _put_locked(self, key: K, value: V) -> None:
        previous = self._items.pop(key, None)
        if previous is not None:
            self._current_bytes -= previous[1]
        size = max(0, int(self._size_of(value)))
        if self.max_bytes <= 0 or size > self.max_bytes:
            return
        while self._items and self._current_bytes + size > self.max_bytes:
            _, (_, removed_size) = self._items.popitem(last=False)
            self._current_bytes -= removed_size
            self._evictions += 1
        self._items[key] = value, size
        self._current_bytes += size

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._current_bytes = 0

    def info(self) -> CacheInfo:
        with self._lock:
            return CacheInfo(
                entries=len(self._items),
                current_bytes=self._current_bytes,
                max_bytes=self.max_bytes,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
            )

