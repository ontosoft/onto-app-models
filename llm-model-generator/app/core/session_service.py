"""Per-session engine access for the API — a thin facade over an EngineTransport.

Routes import ``engine_sessions`` and call ``load/run/run_model/post/get/stop/status``
keyed by the caller's session id (the ``X-Onto-Session`` header). This facade owns
*which* transport backs those calls:

- Stage 1/2a: ``LocalEngineTransport`` — engines run in this process.
- Stage 2b: a Redis-backed transport that forwards to a worker container.

Because routes talk only to this facade, moving the engine out of the process
does not touch any route code. See app/core/engine_transport.py.
"""

from __future__ import annotations

import logging

from app.contracts.engine import AppExchangeGetOutput
from app.core.config import settings
from app.core.engine_transport import (
    DEFAULT_SESSION,
    EngineTransport,
    LocalEngineTransport,
)

logger = logging.getLogger("ontoui_app")

__all__ = ["EngineSessionService", "engine_sessions", "DEFAULT_SESSION"]


def _build_transport() -> EngineTransport:
    """Select the engine transport from settings.ENGINE_TRANSPORT.

    "redis" forwards ops to an engine_worker container; anything else runs the
    engine in this process. Falls back to local if the Redis client can't be
    constructed, so a misconfigured API still serves (single-tenant) rather than
    failing to boot.
    """
    if settings.ENGINE_TRANSPORT == "redis":
        try:
            from app.core.engine_transport import RedisEngineTransport

            logger.info("Engine transport: redis (delegating to engine_worker)")
            return RedisEngineTransport()
        except Exception:
            logger.exception("Failed to init Redis engine transport; using local")
    return LocalEngineTransport()


class EngineSessionService:
    """Delegates every per-session operation to the configured transport."""

    def __init__(self, transport: EngineTransport | None = None) -> None:
        self._transport: EngineTransport = transport or _build_transport()

    def load(self, sid: str, *, file_name=None, rdf_string=None, model_name=None) -> None:
        return self._transport.load(
            sid, file_name=file_name, rdf_string=rdf_string, model_name=model_name
        )

    def run(self, sid: str) -> bool:
        return self._transport.run(sid)

    def run_model(self, sid: str, *, rdf_string=None, file_name=None, model_name=None) -> None:
        return self._transport.run_model(
            sid, rdf_string=rdf_string, file_name=file_name, model_name=model_name
        )

    def post(self, sid: str, frontend_state) -> AppExchangeGetOutput:
        return self._transport.post(sid, frontend_state)

    def get(self, sid: str) -> AppExchangeGetOutput:
        return self._transport.get(sid)

    def stop(self, sid: str) -> None:
        return self._transport.stop(sid)

    def status(self, sid: str) -> dict:
        return self._transport.status(sid)


engine_sessions = EngineSessionService()  # process-wide singleton, imported by both routers
