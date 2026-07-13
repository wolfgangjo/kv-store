# store.py
# Append-only persistence layer.
# Every write command is appended to data.db as a line.
# On startup, the log is replayed to rebuild the in-memory index.
# Supports transactions: BEGIN buffers writes, COMMIT flushes them to disk,
# ABORT reverts the in-memory index using an undo list.

import time
from index import Index

DB_FILE = "data.db"

class Store:
    def __init__(self):
        self.index = Index()
        self.ttl_index = Index()

        self.in_transaction = False
        self.tx_log = []    # buffered log lines to write on COMMIT
        self.tx_undo = []   # list of (key, old_value_or_None) to revert on ABORT

        self._load()

    def _load(self):
        try:
            with open(DB_FILE, "r") as f:
                for line in f:
                    self._apply(line.rstrip("\n"))
        except FileNotFoundError:
            pass

    def _write_line(self, line):
        with open(DB_FILE, "a") as f:
            f.write(line + "\n")

    def _append(self, line):
        # if inside a transaction, buffer instead of writing immediately
        if self.in_transaction:
            self.tx_log.append(line)
        else:
            self._write_line(line)

    def _record_undo(self, key):
        # save the current value of key so we can revert it on ABORT
        if self.in_transaction:
            self.tx_undo.append((key, self.index.get(key)))

    def _apply(self, line):
        parts = line.split("\t")
        op = parts[0]
        if op == "SET":
            self.index.set(parts[1], parts[2])
            self.ttl_index.delete(parts[1])
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
        self._record_undo(key)
        self._append(f"SET\t{key}\t{value}")
        self.index.set(key, value)
        self.ttl_index.delete(key)

    def get(self, key):
        self._check_expired(key)
        return self.index.get(key)

    def delete(self, key):
        self._record_undo(key)
        self._append(f"DEL\t{key}")
        self.ttl_index.delete(key)
        return self.index.delete(key)

    def exists(self, key):
        self._check_expired(key)
        return self.index.exists(key)

    def range(self, start, end):
        return self.index.range(start, end)

    def flushdb(self):
        # record undo for every existing key before wiping
        if self.in_transaction:
            for k, v in self.index.entries:
                self.tx_undo.append((k, v))
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
            return -2
        expire_at = self.ttl_index.get(key)
        if expire_at is None:
            return -1
        return max(0, int(float(expire_at) - time.time()))

    def begin(self):
        if self.in_transaction:
            return False
        self.in_transaction = True
        self.tx_log = []
        self.tx_undo = []
        return True

    def commit(self):
        if not self.in_transaction:
            return False
        for line in self.tx_log:
            self._write_line(line)
        self.in_transaction = False
        self.tx_log = []
        self.tx_undo = []
        return True

    def abort(self):
        if not self.in_transaction:
            return False
        # revert in reverse order in case the same key changed multiple times
        for key, old_value in reversed(self.tx_undo):
            if old_value is None:
                self.index.delete(key)
            else:
                self.index.set(key, old_value)
        self.in_transaction = False
        self.tx_log = []
        self.tx_undo = []
        return True