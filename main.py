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

        elif cmd == "FLUSHDB":
            store.flushdb()
            print("OK")

        else:
            print(f"ERROR: unknown command {cmd}")

if __name__ == "__main__":
    main()