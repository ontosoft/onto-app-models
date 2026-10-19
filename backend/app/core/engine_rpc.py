"""Redis wire protocol shared by RedisEngineTransport (API side) and the
engine_worker (worker side).

Keys
----
  engine:workers:load          ZSET  score = live session count (least-loaded pick)
  engine:worker:{wid}:alive    STR   heartbeat, TTL WORKER_ALIVE_TTL
  engine:worker:{wid}:inbox    LIST  worker mailbox; worker BLPOPs JSON requests
  engine:session:{sid}:worker  STR   affinity map session -> worker, TTL SESSION_TTL
  engine:reply:{cid}           LIST  RPC reply channel; API BLPOPs JSON response

Message shapes (JSON)
---------------------
  request : {"op": str, "sid": str, "kwargs": {...}, "reply": "engine:reply:{cid}"}
  response: {"ok": true, "result": <json>} | {"ok": false, "error": str}
"""

from __future__ import annotations

import json

WORKERS_LOAD = "engine:workers:load"

WORKER_ALIVE_TTL = 15  # seconds; heartbeat refreshes at ~1/3 of this
SESSION_TTL = 1800  # 30 min affinity, refreshed on activity
REPLY_TTL = 120  # reply channel self-expiry (guards against lost readers)


def worker_alive_key(wid: str) -> str:
    return f"engine:worker:{wid}:alive"


def worker_inbox_key(wid: str) -> str:
    return f"engine:worker:{wid}:inbox"


def session_worker_key(sid: str) -> str:
    return f"engine:session:{sid}:worker"


def reply_key(cid: str) -> str:
    return f"engine:reply:{cid}"


def encode(obj) -> str:
    return json.dumps(obj)


def decode(raw) -> dict:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def as_str(v) -> str | None:
    """Redis returns bytes by default; normalise member/value reads to str."""
    if v is None:
        return None
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)
