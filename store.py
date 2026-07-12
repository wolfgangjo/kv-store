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
        self.ttls = {}       # key -> expire_unix_time
        self.hashes = {}     # simple dict allowed here? NO - see note below
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
        # parses a stored log line and applies it to the index
        parts = line.split("\t")
        op = parts[0]
        if op == "SET":
            self.index.set(parts[1], parts[2])
        elif op == "DEL":
            self.index.delete(parts[1])
        elif op == "FLUSHDB":
            self.index.flush()

    def set(self, key, value):
        self._append(f"SET\t{key}\t{value}")
        self.index.set(key, value)

    def get(self, key):
        return self.index.get(key)

    def delete(self, key):
        self._append(f"DEL\t{key}")
        return self.index.delete(key)

    def exists(self, key):
        return self.index.exists(key)

    def range(self, start, end):
        return self.index.range(start, end)

    def flushdb(self):
        self._append("FLUSHDB")
        self.index.flush()