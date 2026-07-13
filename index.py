# index.py
# Custom in-memory index: sorted list of [key, value] pairs
# No built-in dict/map used - lookups done via manual binary search

class Index:
    def __init__(self):
        self.entries = []  # list of [key, value]

    def _find(self, key):
        # binary search, returns (found: bool, position: int)
        lo, hi = 0, len(self.entries)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.entries[mid][0] < key:
                lo = mid + 1
            elif self.entries[mid][0] > key:
                hi = mid
            else:
                return True, mid
        return False, lo

    def set(self, key, value):
        found, pos = self._find(key)
        if found:
            self.entries[pos][1] = value
        else:
            self.entries.insert(pos, [key, value])

    def get(self, key):
        found, pos = self._find(key)
        return self.entries[pos][1] if found else None

    def delete(self, key):
        found, pos = self._find(key)
        if found:
            del self.entries[pos]
            return True
        return False

    def exists(self, key):
        found, _ = self._find(key)
        return found

    def range(self, start, end):
        # returns list of [key, value] where start <= key <= end
        result = []
        for k, v in self.entries:
            if start <= k <= end:
                result.append([k, v])
        return result

    def flush(self):
        self.entries = []
