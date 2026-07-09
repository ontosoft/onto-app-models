"""The engine worker main loop.

A worker registers itself in Redis, consumes its inbox, and runs each op against
an in-process LocalEngineTransport in a thread pool — so one session's 10-25s
reasoner load does not block other sessions this worker holds. Replies go on the
caller's reply channel. Crash isolation: if this process dies, its heartbeat key
expires, the API sees its sessions as gone, and a supervisor restarts it.
"""

from __future__ import annotations

import logging
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import redis
from pydantic import BaseModel

from app.core import engine_rpc as rpc
from app.core.config import settings
from app.core.engine_transport import LocalEngineTransport

logger = logging.getLogger("ontoui_app")


def _jsonable(x):
    """Engine ops return DTOs (pydantic), dicts, bools or None — normalise for JSON."""
    if isinstance(x, BaseModel):
        return x.model_dump()
    return x


class EngineWorker:
    def __init__(self) -> None:
        self.wid = uuid4().hex[:12]
        # Explicit socket_timeout: with redis-py's default (None), blocking BLPOP
        # hits an internal ~5s read ceiling, which under GIL contention from the
        # reasoner can spuriously time out the inbox loop. Give it ample headroom.
        self.r = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_timeout=settings.ENGINE_RPC_TIMEOUT + 15,
            socket_keepalive=True,
        )
        self.transport = LocalEngineTransport()
        self.executor = ThreadPoolExecutor(
            max_workers=settings.ENGINE_WORKER_CONCURRENCY,
            thread_name_prefix="engine-op",
        )
        self._stop = threading.Event()

    # -- registration / liveness --
    def _register(self) -> None:
        self.r.set(rpc.worker_alive_key(self.wid), "1", ex=rpc.WORKER_ALIVE_TTL)
        self.r.zadd(rpc.WORKERS_LOAD, {self.wid: 0})

    def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.r.set(rpc.worker_alive_key(self.wid), "1", ex=rpc.WORKER_ALIVE_TTL)
                self.r.zadd(rpc.WORKERS_LOAD, {self.wid: self.transport.session_count()})
            except Exception:
                logger.exception("engine worker heartbeat failed")
            self._stop.wait(rpc.WORKER_ALIVE_TTL / 3)

    # -- op handling --
    def _handle(self, msg: dict) -> None:
        op = msg.get("op")
        sid = msg.get("sid")
        kwargs = msg.get("kwargs") or {}
        reply = msg.get("reply")
        try:
            fn = getattr(self.transport, op)
            resp = {"ok": True, "result": _jsonable(fn(sid, **kwargs))}
        except Exception as e:
            logger.exception(f"engine worker op={op} failed for session {sid}")
            resp = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        if reply:
            try:
                pipe = self.r.pipeline()
                pipe.rpush(reply, rpc.encode(resp))
                pipe.expire(reply, rpc.REPLY_TTL)
                pipe.execute()
            except Exception:
                logger.exception("engine worker failed to send reply")

    def run(self) -> None:
        logging.basicConfig(level=logging.INFO)
        logger.info(
            f"engine worker {self.wid} up (concurrency={settings.ENGINE_WORKER_CONCURRENCY}, "
            f"redis={settings.REDIS_URL})"
        )
        self._register()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        # Signal handlers only register on the main thread (so the worker can also
        # be embedded in a thread, e.g. for tests). In production it IS the main
        # thread, so SIGTERM/SIGINT still drive a clean shutdown.
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, lambda *_: self._stop.set())
            signal.signal(signal.SIGINT, lambda *_: self._stop.set())

        inbox = rpc.worker_inbox_key(self.wid)
        try:
            while not self._stop.is_set():
                try:
                    item = self.r.blpop(inbox, timeout=1)
                except redis.exceptions.RedisError:
                    # A transient Redis/socket hiccup must not kill the worker loop.
                    logger.debug("inbox blpop error; retrying", exc_info=True)
                    continue
                if item is None:
                    continue
                _key, raw = item
                try:
                    msg = rpc.decode(raw)
                except Exception:
                    logger.exception("engine worker got an undecodable message")
                    continue
                self.executor.submit(self._handle, msg)
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        logger.info(f"engine worker {self.wid} shutting down")
        self._stop.set()
        try:
            self.r.zrem(rpc.WORKERS_LOAD, self.wid)
            self.r.delete(rpc.worker_alive_key(self.wid))
        except Exception:
            logger.exception("engine worker deregistration failed")
        self.executor.shutdown(wait=False)


def main() -> None:
    EngineWorker().run()


if __name__ == "__main__":
    main()
