"""Engine worker process: a LocalEngineTransport behind a Redis mailbox.

Run with ``python -m app.engine_worker``. Holds the runtime engines in memory,
consuming per-session ops from Redis and replying to the API. DB-less; scale by
running more replicas of this process/container.
"""
