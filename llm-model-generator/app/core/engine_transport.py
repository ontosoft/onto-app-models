"""Engine transport abstraction — the swap point between running the engine
in-process and (Stage 2b) delegating to a Redis-backed worker container.

``EngineSessionService`` talks only to an ``EngineTransport``. ``LocalEngineTransport``
runs ``AppEngine`` instances in this process (the Stage-1 behavior, unchanged). A
future ``RedisEngineTransport`` will forward the same operations to a worker over
Redis; because both satisfy the ``EngineTransport`` protocol, no route code changes.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from typing import Protocol
from uuid import uuid4

from app.contracts.engine import AppExchangeGetOutput

logger = logging.getLogger("ontoui_app")

DEFAULT_SESSION = "__default__"  # fallback when no X-Onto-Session header is sent


def _not_running_post() -> AppExchangeGetOutput:
    return AppExchangeGetOutput(
        message_type="error",
        layout_type="message-box",
        message_content={"message": "No running application for this session."},
        output_knowledge_graph="",
    )


def _not_running_get() -> AppExchangeGetOutput:
    return AppExchangeGetOutput(
        message_type="notification",
        layout_type="message-box",
        message_content={"message": "No running application for this session."},
        output_knowledge_graph="",
    )


class EngineTransport(Protocol):
    """The operations the API needs on a per-session engine, regardless of where
    that engine actually runs (this process, or a worker container)."""

    def load(self, sid: str, *, file_name=None, rdf_string=None, model_name=None) -> None: ...
    def run(self, sid: str) -> bool: ...
    def run_model(self, sid: str, *, rdf_string=None, file_name=None, model_name=None) -> None: ...
    def post(self, sid: str, frontend_state) -> AppExchangeGetOutput: ...
    def get(self, sid: str) -> AppExchangeGetOutput: ...
    def stop(self, sid: str) -> None: ...
    def status(self, sid: str) -> dict: ...


class _Session:
    __slots__ = ("engine", "lock")

    def __init__(self) -> None:
        # Imported lazily so an API process configured with the Redis transport
        # never loads the heavy engine (owlready2/reasoners) at all.
        from app.owlprocessor.app_engine import AppEngine

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
    def load(self, sid: str, *, file_name=None, rdf_string=None, model_name=None) -> None:
        s = self._get_or_create(sid)
        with s.lock:
            s.engine.reset()  # fresh run if this session id is reused
            s.engine.load_inner_app_model(
                file_name=file_name, rdf_string=rdf_string, model_name=model_name
            )

    def run(self, sid: str) -> bool:
        s = self._get(sid)
        if s is None:
            return False
        with s.lock:
            s.engine.run_application()
            return True

    def run_model(self, sid: str, *, rdf_string=None, file_name=None, model_name=None) -> None:
        """load + run atomically for one session (the appmodels run path)."""
        s = self._get_or_create(sid)
        with s.lock:
            s.engine.reset()
            s.engine.load_inner_app_model(
                file_name=file_name, rdf_string=rdf_string, model_name=model_name
            )
            s.engine.run_application()

    def post(self, sid: str, frontend_state) -> AppExchangeGetOutput:
        s = self._get(sid)
        if s is None:
            return _not_running_post()
        with s.lock:
            return s.engine.process_received_client_data(frontend_state)

    def get(self, sid: str) -> AppExchangeGetOutput:
        s = self._get(sid)
        if s is None:
            return _not_running_get()
        with s.lock:
            return s.engine.read_new_model_layout()

    def stop(self, sid: str) -> None:
        with self._registry_lock:
            self._sessions.pop(sid, None)

    def session_count(self) -> int:
        with self._registry_lock:
            return len(self._sessions)

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


class RedisEngineTransport:
    """Forwards each per-session op to the engine_worker that owns the session.

    Sticky routing: a session id is pinned to one worker (affinity map in Redis);
    create-ops (load/run_model) assign the least-loaded live worker. Each op is an
    RPC — push a request to the worker's inbox, block on a reply channel. If the
    owning worker is gone (crashed) the session is treated as expired, which the
    routes surface as "no running application for this session".

    All methods are synchronous and may block on Redis for up to
    ENGINE_RPC_TIMEOUT seconds; async routes call them via run_in_threadpool.
    """

    def __init__(self) -> None:
        import redis  # local import so `local` transport never needs the client

        from app.core.config import settings
        from app.core import engine_rpc as rpc

        self._rpc = rpc
        self._timeout = settings.ENGINE_RPC_TIMEOUT
        # socket_timeout MUST exceed the blocking BLPOP timeout: with redis-py's
        # default (None), blocking reads hit an internal ~5s ceiling, so any RPC
        # whose reply takes >~5s (e.g. a cold reasoner load) would fail with
        # "Timeout reading from socket". +15s of headroom over the RPC budget.
        self._r = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_timeout=self._timeout + 15,
            socket_keepalive=True,
        )

    # -- worker resolution --
    def _live(self, wid: str | None) -> bool:
        return bool(wid) and bool(self._r.exists(self._rpc.worker_alive_key(wid)))

    def _resolve(self, sid: str) -> str | None:
        """Worker currently owning sid, or None if unassigned / worker dead."""
        wid = self._rpc.as_str(self._r.get(self._rpc.session_worker_key(sid)))
        if wid and self._live(wid):
            self._r.expire(self._rpc.session_worker_key(sid), self._rpc.SESSION_TTL)
            return wid
        return None

    def _select_worker(self) -> str | None:
        """Least-loaded live worker; opportunistically drops dead ZSET entries."""
        for member in self._r.zrange(self._rpc.WORKERS_LOAD, 0, -1):
            wid = self._rpc.as_str(member)
            if self._live(wid):
                return wid
            self._r.zrem(self._rpc.WORKERS_LOAD, member)  # prune stale worker
        return None

    def _assign(self, sid: str) -> str | None:
        wid = self._resolve(sid)
        if wid:
            return wid
        wid = self._select_worker()
        if wid is None:
            return None
        self._r.set(self._rpc.session_worker_key(sid), wid, ex=self._rpc.SESSION_TTL)
        return wid

    def _call(self, wid: str, op: str, sid: str, kwargs: dict):
        cid = uuid4().hex
        reply = self._rpc.reply_key(cid)
        msg = {"op": op, "sid": sid, "kwargs": kwargs, "reply": reply}
        self._r.rpush(self._rpc.worker_inbox_key(wid), self._rpc.encode(msg))
        got = self._r.blpop(reply, timeout=self._timeout)
        if got is None:
            raise TimeoutError(f"engine worker {wid} did not reply to op={op}")
        _key, raw = got
        resp = self._rpc.decode(raw)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "engine worker error"))
        return resp.get("result")

    @staticmethod
    def _s(v):
        return str(v) if v is not None else None

    # -- EngineTransport ops --
    def load(self, sid: str, *, file_name=None, rdf_string=None, model_name=None) -> None:
        wid = self._assign(sid)
        if wid is None:
            raise RuntimeError("no engine worker available")
        self._call(wid, "load", sid, {
            "file_name": self._s(file_name),
            "rdf_string": rdf_string,
            "model_name": model_name,
        })

    def run(self, sid: str) -> bool:
        wid = self._resolve(sid)
        if wid is None:
            return False
        return bool(self._call(wid, "run", sid, {}))

    def run_model(self, sid: str, *, rdf_string=None, file_name=None, model_name=None) -> None:
        wid = self._assign(sid)
        if wid is None:
            raise RuntimeError("no engine worker available")
        self._call(wid, "run_model", sid, {
            "rdf_string": rdf_string,
            "file_name": self._s(file_name),
            "model_name": model_name,
        })

    def post(self, sid: str, frontend_state) -> AppExchangeGetOutput | None:
        wid = self._resolve(sid)
        if wid is None:
            return _not_running_post()
        result = self._call(wid, "post", sid, {"frontend_state": frontend_state})
        return AppExchangeGetOutput(**result) if result is not None else None

    def get(self, sid: str) -> AppExchangeGetOutput:
        wid = self._resolve(sid)
        if wid is None:
            return _not_running_get()
        result = self._call(wid, "get", sid, {})
        return AppExchangeGetOutput(**result)

    def stop(self, sid: str) -> None:
        wid = self._resolve(sid)
        if wid is not None:
            try:
                self._call(wid, "stop", sid, {})
            except Exception:
                logger.exception("engine worker stop failed; dropping affinity anyway")
        self._r.delete(self._rpc.session_worker_key(sid))

    def status(self, sid: str) -> dict:
        wid = self._resolve(sid)
        if wid is None:
            return {"exists": False, "loaded": False, "running": False}
        return self._call(wid, "status", sid, {})
