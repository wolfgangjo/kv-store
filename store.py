# store.py
# Append-only persistence layer.
# Every write command is appended to data.db as a line.
# On startup, the log is replayed to rebuild the in-memory index.

import time
from index import Index

DB_FILE = "data.db"

class Store:
    def __init__(self):
        self.index = Index()
        self.ttl_index = Index()  # key -> expire_at (unix timestamp as string)
        self._load()

    def _load(self):
        try:
            with open(DB_FILE, "r") as f:
                for line in f:
                    self._apply(line.rstrip("\n"))
        except FileNotFoundError:
            pass

    def _append(self, line):
        with open(DB_FILE, "a") as f:
            f.write(line + "\n")

    def _apply(self, line):
        parts = line.split("\t")
        op = parts[0]
        if op == "SET":
            self.index.set(parts[1], parts[2])
            self.ttl_index.delete(parts[1])  # new SET clears old ttl
        elif op == "DEL":
            self.index.delete(parts[1])
            self.ttl_index.delete(parts[1])
        elif op == "FLUSHDB":
            self.index.flush()
            self.ttl_index.flush()
        elif op == "EXPIRE":
            self.ttl_index.set(parts[1], parts[2])

    def _check_expired(self, key):
        expire_at = self.ttl_index.get(key)
        if expire_at is not None and time.time() > float(expire_at):
            self.index.delete(key)
            self.ttl_index.delete(key)
            return True
        return False

    def set(self, key, value):
        self._append(f"SET\t{key}\t{value}")
        self.index.set(key, value)
        self.ttl_index.delete(key)

    def get(self, key):
        self._check_expired(key)
        return self.index.get(key)

    def delete(self, key):
        self._append(f"DEL\t{key}")
        self.ttl_index.delete(key)
        return self.index.delete(key)

    def exists(self, key):
        self._check_expired(key)
        return self.index.exists(key)

    def range(self, start, end):
        return self.index.range(start, end)

    def flushdb(self):
        self._append("FLUSHDB")
        self.index.flush()
        self.ttl_index.flush()

    def expire(self, key, seconds):
        if not self.index.exists(key):
            return False
        expire_at = time.time() + seconds
        self._append(f"EXPIRE\t{key}\t{expire_at}")
        self.ttl_index.set(key, str(expire_at))
        return True

    def ttl(self, key):
        self._check_expired(key)
        if not self.index.exists(key):
            return -2  # key doesn't exist
        expire_at = self.ttl_index.get(key)
        if expire_at is None:
            return -1  # no ttl set
        return max(0, int(float(expire_at) - time.time()))