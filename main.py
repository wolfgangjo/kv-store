# main.py
# CLI entry point. Reads commands from stdin, dispatches to Store, prints to stdout.

import sys
from store import Store

def main():
    store = Store()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        cmd = parts[0].upper()

        if cmd == "EXIT":
            break

        elif cmd == "SET":
            if len(parts) < 3:
                print("ERROR: SET requires a key and value")
                continue
            key = parts[1]
            value = " ".join(parts[2:])
            store.set(key, value)
            print("OK")

        elif cmd == "GET":
            if len(parts) < 2:
                print("ERROR: GET requires a key")
                continue
            result = store.get(parts[1])
            print(result if result is not None else "NULL")

        elif cmd == "DEL":
            if len(parts) < 2:
                print("ERROR: DEL requires a key")
                continue
            deleted = store.delete(parts[1])
            print("1" if deleted else "0")

        elif cmd == "EXISTS":
            if len(parts) < 2:
                print("ERROR: EXISTS requires a key")
                continue
            print("1" if store.exists(parts[1]) else "0")

        elif cmd == "MSET":
            if len(parts) < 3 or (len(parts) - 1) % 2 != 0:
                print("ERROR: MSET requires key value pairs")
                continue
            pairs = parts[1:]
            for i in range(0, len(pairs), 2):
                store.set(pairs[i], pairs[i + 1])
            print("OK")

        elif cmd == "MGET":
            if len(parts) < 2:
                print("ERROR: MGET requires at least one key")
                continue
            results = []
            for key in parts[1:]:
                val = store.get(key)
                results.append(val if val is not None else "NULL")
            print(" ".join(results))

        elif cmd == "EXPIRE":
            if len(parts) < 3:
                print("ERROR: EXPIRE requires a key and seconds")
                continue
            try:
                seconds = int(parts[2])
            except ValueError:
                print("ERROR: seconds must be an integer")
                continue
            print("1" if store.expire(parts[1], seconds) else "0")

        elif cmd == "TTL":
            if len(parts) < 2:
                print("ERROR: TTL requires a key")
                continue
            print(store.ttl(parts[1]))

        elif cmd == "RANGE":
            if len(parts) < 3:
                print("ERROR: RANGE requires a start and end key")
                continue
            results = store.range(parts[1], parts[2])
            if not results:
                print("EMPTY")
            else:
                for k, v in results:
                    print(f"{k} {v}")

        elif cmd == "BEGIN":
            print("OK" if store.begin() else "ERROR: already in a transaction")

        elif cmd == "COMMIT":
            print("OK" if store.commit() else "ERROR: no transaction in progress")

        elif cmd == "ABORT":
            print("OK" if store.abort() else "ERROR: no transaction in progress")

        elif cmd == "HSET":
            if len(parts) < 4:
                print("ERROR: HSET requires hash, field, and value")
                continue
            store.hset(parts[1], parts[2], " ".join(parts[3:]))
            print("OK")

        elif cmd == "HGET":
            if len(parts) < 3:
                print("ERROR: HGET requires hash and field")
                continue
            result = store.hget(parts[1], parts[2])
            print(result if result is not None else "NULL")

        elif cmd == "HGETALL":
            if len(parts) < 2:
                print("ERROR: HGETALL requires a hash name")
                continue
            results = store.hgetall(parts[1])
            if not results:
                print("EMPTY")
            else:
                for field, val in results:
                    print(f"{field} {val}")

        elif cmd == "LPUSH":
            if len(parts) < 3:
                print("ERROR: LPUSH requires a key and value")
                continue
            store.lpush(parts[1], " ".join(parts[2:]))
            print("OK")

        elif cmd == "RPUSH":
            if len(parts) < 3:
                print("ERROR: RPUSH requires a key and value")
                continue
            store.rpush(parts[1], " ".join(parts[2:]))
            print("OK")

        elif cmd == "LRANGE":
            if len(parts) < 4:
                print("ERROR: LRANGE requires a key, start, and stop")
                continue
            try:
                start = int(parts[2])
                stop = int(parts[3])
            except ValueError:
                print("ERROR: start and stop must be integers")
                continue
            values = store.lrange(parts[1], start, stop)
            if not values:
                print("EMPTY")
            else:
                for v in values:
                    print(v)

        elif cmd == "FLUSHDB":
            store.flushdb()
            print("OK")

        else:
            print(f"ERROR: unknown command {cmd}")

if __name__ == "__main__":
    main()