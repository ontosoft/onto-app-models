"""Per-session engine registry — the seam between the API and the runtime engine.

Every browser tab / run gets its own :class:`AppEngine`, keyed by a session id
(the ``X-Onto-Session`` header). This replaces the former module-level global
engine in ``onto_app_router`` that made the backend single-tenant.

The whole API talks to the engine *only* through this service. That is the point
of the seam: Stage 2 can swap the in-process ``AppEngine`` for an RPC client to a
separate worker container without any route code changing.
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from app.owlprocessor.app_engine import AppEngine
from app.owlprocessor.communication import AppExchangeGetOutput

DEFAULT_SESSION = "__default__"  # fallback when no X-Onto-Session header is sent


class _Session:
    __slots__ = ("engine", "lock")

    def __init__(self) -> None:
        self.engine = AppEngine()
        self.lock = threading.Lock()  # serialize ops on this one engine


class EngineSessionService:
    """One :class:`AppEngine` per session id, LRU-bounded.

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


engine_sessions = EngineSessionService()  # process-wide singleton, imported by both routers
