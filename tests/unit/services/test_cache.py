"""Tests for src/services/cache.py.

These tests don't need a real Redis — they monkeypatch `get_client`
to substitute a fake. End-to-end Redis tests would belong under
tests/integration/ behind a marker.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import redis

from src.services import cache


class FakeRedis:
    """In-memory dict-backed Redis fake (subset of API we use)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.pub_log: list[tuple[str, str]] = []
        self.fail_next: str | None = None  # set to a method name to raise

    def _maybe_fail(self, name: str) -> None:
        if self.fail_next == name:
            self.fail_next = None
            raise redis.RedisError(f"fake fail in {name}")

    def get(self, key: str) -> str | None:
        self._maybe_fail("get")
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._maybe_fail("set")
        self.store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        self._maybe_fail("delete")
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n

    def scan_iter(self, match: str | None = None) -> Any:
        prefix = (match or "").rstrip("*")
        for k in list(self.store):
            if k.startswith(prefix):
                yield k

    def publish(self, channel: str, message: str) -> int:
        self._maybe_fail("publish")
        self.pub_log.append((channel, message))
        return 1


@pytest.fixture
def fake(monkeypatch) -> FakeRedis:
    f = FakeRedis()
    monkeypatch.setattr(cache, "get_client", lambda: f)
    return f


class TestCacheGetSet:
    def test_set_then_get_round_trip(self, fake: FakeRedis) -> None:
        cache.cache_set("k", {"a": 1})
        assert cache.cache_get("k") == {"a": 1}

    def test_get_missing_returns_none(self, fake: FakeRedis) -> None:
        assert cache.cache_get("nope") is None

    def test_set_failure_returns_false(self, fake: FakeRedis) -> None:
        fake.fail_next = "set"
        assert cache.cache_set("k", "v") is False

    def test_get_failure_returns_none(self, fake: FakeRedis) -> None:
        fake.store["k"] = json.dumps("v")
        fake.fail_next = "get"
        assert cache.cache_get("k") is None


class TestDeleteAndInvalidate:
    def test_cache_delete(self, fake: FakeRedis) -> None:
        cache.cache_set("k1", 1)
        cache.cache_set("k2", 2)
        assert cache.cache_delete("k1", "k2") == 2
        assert cache.cache_get("k1") is None

    def test_invalidate_villain(self, fake: FakeRedis) -> None:
        cache.cache_set("villain:Alice:profile", {"vpip": 30})
        cache.cache_set("villain:Alice:sizing", {"flop": 1})
        cache.cache_set("villain:Bob:profile", {"vpip": 40})
        n = cache.invalidate_villain("Alice")
        assert n == 2
        assert cache.cache_get("villain:Bob:profile") == {"vpip": 40}


class TestPublishProgress:
    def test_publish_progress_serializes_event(self, fake: FakeRedis) -> None:
        cache.publish_progress("job1", {"stage": "extract", "current": 5})
        assert len(fake.pub_log) == 1
        channel, payload = fake.pub_log[0]
        assert channel == "jobs:job1"
        assert json.loads(payload) == {"stage": "extract", "current": 5}

    def test_publish_failure_returns_zero(self, fake: FakeRedis) -> None:
        fake.fail_next = "publish"
        assert cache.publish_progress("job1", {"stage": "x"}) == 0
