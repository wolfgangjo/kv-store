# tests/test_store.py
# Unit tests for the Store class covering core functionality.
# Uses a temporary db file so it never touches the real data.db.

import unittest
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import store as store_module

TEST_DB = "test_data.db"


class TestStore(unittest.TestCase):

    def setUp(self):
        # point Store at a throwaway file, and make sure it starts empty
        store_module.DB_FILE = TEST_DB
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        self.store = store_module.Store()

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_set_get(self):
        self.store.set("foo", "bar")
        self.assertEqual(self.store.get("foo"), "bar")

    def test_get_missing_key(self):
        self.assertIsNone(self.store.get("nope"))

    def test_last_write_wins(self):
        self.store.set("foo", "first")
        self.store.set("foo", "second")
        self.assertEqual(self.store.get("foo"), "second")

    def test_delete(self):
        self.store.set("foo", "bar")
        self.assertTrue(self.store.delete("foo"))
        self.assertIsNone(self.store.get("foo"))

    def test_delete_missing_key(self):
        self.assertFalse(self.store.delete("nope"))

    def test_exists(self):
        self.store.set("foo", "bar")
        self.assertTrue(self.store.exists("foo"))
        self.assertFalse(self.store.exists("nope"))

    def test_range(self):
        self.store.set("apple", "1")
        self.store.set("banana", "2")
        self.store.set("cherry", "3")
        result = self.store.range("banana", "cherry")
        keys = [k for k, v in result]
        self.assertEqual(keys, ["banana", "cherry"])

    def test_flushdb(self):
        self.store.set("foo", "bar")
        self.store.flushdb()
        self.assertIsNone(self.store.get("foo"))

    def test_persistence_across_restart(self):
        self.store.set("foo", "bar")
        self.store.delete_placeholder = None  # no-op, just for clarity
        reloaded = store_module.Store()
        self.assertEqual(reloaded.get("foo"), "bar")

    def test_expire_and_ttl(self):
        self.store.set("foo", "bar")
        self.store.expire("foo", 10)
        ttl_val = self.store.ttl("foo")
        self.assertTrue(0 < ttl_val <= 10)

    def test_expired_key_is_gone(self):
        self.store.set("foo", "bar")
        self.store.expire("foo", -1)  # already expired
        self.assertIsNone(self.store.get("foo"))
        self.assertEqual(self.store.ttl("foo"), -2)

    def test_transaction_commit(self):
        self.store.set("foo", "bar")
        self.store.begin()
        self.store.set("foo", "baz")
        self.store.commit()
        self.assertEqual(self.store.get("foo"), "baz")

    def test_transaction_abort(self):
        self.store.set("foo", "bar")
        self.store.begin()
        self.store.set("foo", "baz")
        self.store.abort()
        self.assertEqual(self.store.get("foo"), "bar")

    def test_hash_operations(self):
        self.store.hset("user1", "name", "Jordan")
        self.store.hset("user1", "age", "21")
        self.assertEqual(self.store.hget("user1", "name"), "Jordan")
        fields = dict(self.store.hgetall("user1"))
        self.assertEqual(fields["name"], "Jordan")
        self.assertEqual(fields["age"], "21")

    def test_list_operations(self):
        self.store.rpush("mylist", "a")
        self.store.rpush("mylist", "b")
        self.store.lpush("mylist", "z")
        result = self.store.lrange("mylist", 0, -1)
        self.assertEqual(result, ["z", "a", "b"])

    def test_incr_decr(self):
        self.store.set("counter", "10")
        self.assertEqual(self.store.incr("counter"), 11)
        self.assertEqual(self.store.decr("counter"), 10)

    def test_incr_on_missing_key(self):
        self.assertEqual(self.store.incr("newcounter"), 1)


if __name__ == "__main__":
    unittest.main()