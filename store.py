# store.py
# Append-only persistence layer.
# Every write command is appended to data.db as a line.
# On startup, the log is replayed to rebuild the in-memory index.
# Supports transactions: BEGIN buffers writes, COMMIT flushes them to disk,
# ABORT reverts the in-memory index using an undo list.
# Hashes are stored as composite keys: "<hashname>\x1f<field>" -> value
# Lists are stored as composite keys: "<listname>\x1f<zero_padded_index>" -> value
# Counters (INCR/DECR) reuse the normal SET path on integer-parsed values.

import time
from index import Index

DB_FILE = "data.db"
HASH_SEP = "\x1f"
LIST_PAD = 10


class Store:
    def __init__(self):
        self.index = Index()
        self.ttl_index = Index()

        self.in_transaction = False
        self.tx_log = []
        self.tx_undo = []

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
        if self.in_transaction:
            self.tx_log.append(line)
        else:
            self._write_line(line)

    def _record_undo(self, key):
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
        elif op == "HSET":
            composite = parts[1] + HASH_SEP + parts[2]
            self.index.set(composite, parts[3])
        elif op == "LPUSH":
            self._do_lpush(parts[1], parts[2])
        elif op == "RPUSH":
            self._do_rpush(parts[1], parts[2])

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
        for key, old_value in reversed(self.tx_undo):
            if old_value is None:
                self.index.delete(key)
            else:
                self.index.set(key, old_value)
        self.in_transaction = False
        self.tx_log = []
        self.tx_undo = []
        return True

    def hset(self, hashname, field, value):
        composite = hashname + HASH_SEP + field
        self._record_undo(composite)
        self._append(f"HSET\t{hashname}\t{field}\t{value}")
        self.index.set(composite, value)

    def hget(self, hashname, field):
        composite = hashname + HASH_SEP + field
        return self.index.get(composite)

    def hgetall(self, hashname):
        prefix = hashname + HASH_SEP
        result = []
        for k, v in self.index.entries:
            if k.startswith(prefix):
                field = k[len(prefix):]
                result.append((field, v))
        return result

    def _list_items(self, listname):
        prefix = listname + HASH_SEP
        items = []
        for k, v in self.index.entries:
            if k.startswith(prefix):
                idx_str = k[len(prefix):]
                items.append((int(idx_str), v))
        items.sort(key=lambda pair: pair[0])
        return items

    def _do_lpush(self, listname, value):
        items = self._list_items(listname)
        for idx, v in reversed(items):
            old_key = listname + HASH_SEP + str(idx).zfill(LIST_PAD)
            new_key = listname + HASH_SEP + str(idx + 1).zfill(LIST_PAD)
            self.index.delete(old_key)
            self.index.set(new_key, v)
        new_key = listname + HASH_SEP + "0".zfill(LIST_PAD)
        self.index.set(new_key, value)

    def _do_rpush(self, listname, value):
        items = self._list_items(listname)
        next_idx = (items[-1][0] + 1) if items else 0
        new_key = listname + HASH_SEP + str(next_idx).zfill(LIST_PAD)
        self.index.set(new_key, value)

    def lpush(self, listname, value):
        self._append(f"LPUSH\t{listname}\t{value}")
        self._do_lpush(listname, value)

    def rpush(self, listname, value):
        self._append(f"RPUSH\t{listname}\t{value}")
        self._do_rpush(listname, value)

    def lrange(self, listname, start, stop):
        items = self._list_items(listname)
        values = [v for _, v in items]
        n = len(values)

        if start < 0:
            start = max(n + start, 0)
        if stop < 0:
            stop = n + stop
        stop = min(stop, n - 1)

        if start > stop or n == 0:
            return []
        return values[start:stop + 1]

    def incr(self, key):
        current = self.index.get(key)
        try:
            num = int(current) if current is not None else 0
        except ValueError:
            return None
        num += 1
        self.set(key, str(num))
        return num

    def decr(self, key):
        current = self.index.get(key)
        try:
            num = int(current) if current is not None else 0
        except ValueError:
            return None
        num -= 1
        self.set(key, str(num))
        return num
