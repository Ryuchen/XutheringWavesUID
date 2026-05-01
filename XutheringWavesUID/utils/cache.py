import json
import sqlite3
import time
from collections import OrderedDict
from contextlib import closing
from pathlib import Path
from typing import Optional, Union


class TimedCache:
    """轻量定时缓存。

    - 默认纯内存（OrderedDict + TTL），与原版一致。
    - 传 `persist_path` 时启用 sqlite 落盘：
      多 worker / 进程重启场景下，磁盘作为权威源，
      解决登录态写入 A 进程内存、读到 B 进程内存而 404 的问题。
    """

    def __init__(
        self,
        timeout: int = 5,
        maxsize: int = 10,
        persist_path: Optional[Union[str, Path]] = None,
    ):
        self.cache = OrderedDict()
        self.timeout = timeout
        self.maxsize = maxsize
        self.persist_path: Optional[Path] = (
            Path(persist_path) if persist_path else None
        )
        if self.persist_path:
            self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.persist_path), timeout=2.0)

    def _init_db(self):
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(self._connect()) as conn:
                with conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS timed_cache ("
                        "key TEXT PRIMARY KEY, value TEXT NOT NULL, expiry REAL NOT NULL)"
                    )
                    conn.execute(
                        "DELETE FROM timed_cache WHERE expiry <= ?", (time.time(),)
                    )
        except Exception:
            self.persist_path = None  # 落盘不可用时退化为纯内存

    def _persist_set(self, key, value, expiry):
        if not self.persist_path:
            return
        try:
            with closing(self._connect()) as conn:
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO timed_cache (key, value, expiry) VALUES (?, ?, ?)",
                        (key, json.dumps(value, default=str), expiry),
                    )
        except Exception:
            pass

    def _persist_delete(self, key):
        if not self.persist_path:
            return
        try:
            with closing(self._connect()) as conn:
                with conn:
                    conn.execute("DELETE FROM timed_cache WHERE key = ?", (key,))
        except Exception:
            pass

    def _persist_get(self, key):
        if not self.persist_path:
            return None
        try:
            with closing(self._connect()) as conn:
                row = conn.execute(
                    "SELECT value, expiry FROM timed_cache WHERE key = ?", (key,)
                ).fetchone()
                if not row:
                    return None
                value_json, expiry = row
                if time.time() >= expiry:
                    with conn:
                        conn.execute(
                            "DELETE FROM timed_cache WHERE key = ?", (key,)
                        )
                    return None
                return json.loads(value_json), expiry
        except Exception:
            return None

    def set(self, key, value):
        if len(self.cache) >= self.maxsize:
            self._clean_up()
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            self._clean_up()
        expiry = time.time() + self.timeout
        self.cache[key] = (value, expiry)
        self._persist_set(key, value, expiry)

    def get(self, key):
        # 启用持久化时，磁盘是权威源——避免本进程内存 stale，
        # 而真正的更新发生在另一个 worker / 重启之前。
        if self.persist_path:
            disk = self._persist_get(key)
            if disk is None:
                self.cache.pop(key, None)
                return None
            value, expiry = disk
            self.cache[key] = (value, expiry)
            return value
        # 纯内存模式
        if key in self.cache:
            value, expiry = self.cache.pop(key)
            if time.time() < expiry:
                self.cache[key] = (value, expiry)
                return value
        return None

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
        self._persist_delete(key)

    def _clean_up(self):
        current_time = time.time()
        keys_to_delete = []
        for key, (value, expiry_time) in self.cache.items():
            if expiry_time <= current_time:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.cache[key]
