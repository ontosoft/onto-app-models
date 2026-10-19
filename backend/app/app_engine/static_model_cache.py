"""Per-process cache of reasoned owlready2 worlds, keyed by a hash of the input.

The Java reasoner (Pellet/HermiT) is the dominant cost of loading a model
(10-25s). Its output — the fully materialised, inferred world — serialises to
RDF/XML and reloads into a fresh ``World`` *without* re-running the reasoner
(verified: inferences survive save->reload). So we cache the serialised reasoned
world and, on a repeat load of the same input, reload a NEW ``World`` from it per
caller (its own SQLite connection => thread-safe; no shared-state locking).

This benefits every load path — local transport and the Redis engine worker
alike — since it sits in the reasoning step itself.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Callable

from owlready2 import World

logger = logging.getLogger("ontoui_app")


def serialize_world(world: World) -> bytes:
    """RDF/XML bytes of every triple in the world (including reasoner inferences)."""
    fd, name = tempfile.mkstemp(suffix=".owl")
    os.close(fd)
    try:
        world.save(file=name, format="rdfxml")
        return Path(name).read_bytes()
    finally:
        os.unlink(name)


def load_world(data: bytes) -> World:
    """Load RDF/XML bytes into a brand-new World (its own SQLite connection)."""
    fd, name = tempfile.mkstemp(suffix=".owl")
    os.close(fd)
    try:
        Path(name).write_bytes(data)
        world = World()
        world.get_ontology(name).load()
        return world
    finally:
        os.unlink(name)


class ReasonedWorldCache:
    """LRU cache of serialised reasoned worlds with per-key build de-duplication."""

    def __init__(self, max_entries: int = 16) -> None:
        self._store: "OrderedDict[str, bytes]" = OrderedDict()
        self._lock = threading.Lock()
        self._build_locks: dict[str, threading.Lock] = {}
        self._max = max_entries

    @staticmethod
    def key(reasoner: str, content_key: str) -> str:
        """Cache key = reasoner name + a STABLE content key (a hash of the original
        model RDF, supplied by the caller).

        Deliberately NOT derived from the owlready world's serialization: that is
        not byte-stable across loads (blank-node / storid numbering, element order),
        so it would produce a different key every time and defeat the cache.
        """
        return f"{reasoner}:{content_key}"

    def get_or_build(self, key: str, build: Callable[[], bytes]) -> tuple[bytes, bool]:
        """Return ``(serialized_reasoned_world, was_cached)``.

        Builds at most once per key even under concurrent callers (the slow
        reasoner runs outside the registry lock, guarded by a per-key lock).
        """
        with self._lock:
            data = self._store.get(key)
            if data is not None:
                self._store.move_to_end(key)
                return data, True
            build_lock = self._build_locks.setdefault(key, threading.Lock())
        with build_lock:
            with self._lock:
                data = self._store.get(key)
                if data is not None:
                    self._store.move_to_end(key)
                    return data, True
            data = build()  # slow: runs the Java reasoner
            with self._lock:
                self._store[key] = data
                self._store.move_to_end(key)
                while len(self._store) > self._max:
                    old, _ = self._store.popitem(last=False)
                    self._build_locks.pop(old, None)
            return data, False


reasoned_world_cache = ReasonedWorldCache()
