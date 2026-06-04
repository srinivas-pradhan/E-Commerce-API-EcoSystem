from __future__ import annotations

from copy import deepcopy
from time import monotonic
from typing import Any

from config import settings


class PermissionCache:
    def __init__(self):
        self._items: dict[tuple[str, int, int], tuple[float, Any]] = {}

    def get(self, user_id: str, page: int, per_page: int) -> Any | None:
        ttl = settings.permission_cache_ttl_seconds
        if ttl <= 0:
            return None

        key = (user_id, page, per_page)
        cached = self._items.get(key)
        if cached is None:
            return None

        expires_at, value = cached
        if expires_at <= monotonic():
            self._items.pop(key, None)
            return None

        return deepcopy(value)

    def set(self, user_id: str, page: int, per_page: int, value: Any) -> None:
        ttl = settings.permission_cache_ttl_seconds
        if ttl <= 0:
            return

        self._items[(user_id, page, per_page)] = (monotonic() + ttl, deepcopy(value))

    def invalidate_user(self, user_id: str) -> None:
        for key in list(self._items):
            if key[0] == user_id:
                self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()


permission_cache = PermissionCache()
