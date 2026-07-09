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

from app.contracts.engine import AppExchangeGetOutput
from app.core.engine_transport import (
    DEFAULT_SESSION,
    EngineTransport,
    LocalEngineTransport,
)

__all__ = ["EngineSessionService", "engine_sessions", "DEFAULT_SESSION"]


class EngineSessionService:
    """Delegates every per-session operation to the configured transport."""

    def __init__(self, transport: EngineTransport | None = None) -> None:
        # Stage 2b will select the transport from settings (ENGINE_TRANSPORT):
        # LocalEngineTransport in-process, or a RedisEngineTransport to a worker.
        self._transport: EngineTransport = transport or LocalEngineTransport()

    def load(self, sid: str, *, file_name=None, rdf_string=None) -> None:
        return self._transport.load(sid, file_name=file_name, rdf_string=rdf_string)

    def run(self, sid: str) -> bool:
        return self._transport.run(sid)

    def run_model(self, sid: str, *, rdf_string=None, file_name=None) -> None:
        return self._transport.run_model(
            sid, rdf_string=rdf_string, file_name=file_name
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
