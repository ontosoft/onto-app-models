"""Engine transport abstraction — the swap point between running the engine
in-process and (Stage 2b) delegating to a Redis-backed worker container.

``EngineSessionService`` talks only to an ``EngineTransport``. ``LocalEngineTransport``
runs ``AppEngine`` instances in this process (the Stage-1 behavior, unchanged). A
future ``RedisEngineTransport`` will forward the same operations to a worker over
Redis; because both satisfy the ``EngineTransport`` protocol, no route code changes.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Protocol

from app.contracts.engine import AppExchangeGetOutput
from app.owlprocessor.app_engine import AppEngine

DEFAULT_SESSION = "__default__"  # fallback when no X-Onto-Session header is sent


class EngineTransport(Protocol):
    """The operations the API needs on a per-session engine, regardless of where
    that engine actually runs (this process, or a worker container)."""

    def load(self, sid: str, *, file_name=None, rdf_string=None) -> None: ...
    def run(self, sid: str) -> bool: ...
    def run_model(self, sid: str, *, rdf_string=None, file_name=None) -> None: ...
    def post(self, sid: str, frontend_state) -> AppExchangeGetOutput: ...
    def get(self, sid: str) -> AppExchangeGetOutput: ...
    def stop(self, sid: str) -> None: ...
    def status(self, sid: str) -> dict: ...


class _Session:
    __slots__ = ("engine", "lock")

    def __init__(self) -> None:
        self.engine = AppEngine()
        self.lock = threading.Lock()  # serialize ops on this one engine


class LocalEngineTransport:
    """Runs one :class:`AppEngine` per session id, in this process, LRU-bounded.

    The bound stops abandoned tabs (closed without Stop) from leaking
    reasoner-loaded engines. A short registry lock guards only the dict; a
    per-session lock serializes operations on a single engine so one session's
    10-25s reasoner load never blocks another session's requests.
    """

    def __init__(self, max_sessions: int = 32) -> None:
        self._sessions: "OrderedDict[str, _Session]" = OrderedDict()
        self._registry_lock = threading.Lock()
        self._max = max_sessions

    # -- registry (short critical sections only) --
    def _get_or_create(self, sid: str) -> _Session:
        with self._registry_lock:
            s = self._sessions.get(sid)
            if s is None:
                s = _Session()
                self._sessions[sid] = s
                while len(self._sessions) > self._max:
                    self._sessions.popitem(last=False)  # evict least-recently-used
            self._sessions.move_to_end(sid)
            return s

    def _get(self, sid: str) -> _Session | None:
        with self._registry_lock:
            s = self._sessions.get(sid)
            if s is not None:
                self._sessions.move_to_end(sid)
            return s

    # -- operations (engine work happens OUTSIDE the registry lock) --
    def load(self, sid: str, *, file_name=None, rdf_string=None) -> None:
        s = self._get_or_create(sid)
        with s.lock:
            s.engine.reset()  # fresh run if this session id is reused
            s.engine.load_inner_app_model(file_name=file_name, rdf_string=rdf_string)

    def run(self, sid: str) -> bool:
        s = self._get(sid)
        if s is None:
            return False
        with s.lock:
            s.engine.run_application()
            return True

    def run_model(self, sid: str, *, rdf_string=None, file_name=None) -> None:
        """load + run atomically for one session (the appmodels run path)."""
        s = self._get_or_create(sid)
        with s.lock:
            s.engine.reset()
            s.engine.load_inner_app_model(file_name=file_name, rdf_string=rdf_string)
            s.engine.run_application()

    def post(self, sid: str, frontend_state) -> AppExchangeGetOutput:
        s = self._get(sid)
        if s is None:
            return AppExchangeGetOutput(
                message_type="error",
                layout_type="message-box",
                message_content={"message": "No running application for this session."},
                output_knowledge_graph="",
            )
        with s.lock:
            return s.engine.process_received_client_data(frontend_state)

    def get(self, sid: str) -> AppExchangeGetOutput:
        s = self._get(sid)
        if s is None:
            return AppExchangeGetOutput(
                message_type="notification",
                layout_type="message-box",
                message_content={"message": "No running application for this session."},
                output_knowledge_graph="",
            )
        with s.lock:
            return s.engine.read_new_model_layout()

    def stop(self, sid: str) -> None:
        with self._registry_lock:
            self._sessions.pop(sid, None)

    def status(self, sid: str) -> dict:
        s = self._get(sid)
        if s is None:
            return {"exists": False, "loaded": False, "running": False}
        with s.lock:
            eng = s.engine
            loaded = (
                eng.internal_app_static_model is not None
                and eng.internal_app_static_model.is_loaded
            )
            return {
                "exists": True,
                "loaded": loaded,
                "running": eng.process_engine_instance is not None,
                "model_name": eng.model_name,
            }
