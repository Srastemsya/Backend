import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "runtime"))

from room_rules import passes_threshold


class ThresholdTests(unittest.TestCase):
    def test_below_threshold(self):
        for likes, member_count in [(1, 2), (2, 3), (2, 4), (3, 5), (4, 6), (4, 7), (6, 10)]:
            with self.subTest(likes=likes, member_count=member_count):
                self.assertFalse(passes_threshold(likes, member_count))

    def test_at_or_above_threshold(self):
        for likes, member_count in [(2, 2), (3, 3), (3, 4), (4, 5), (5, 6), (5, 7), (7, 10)]:
            with self.subTest(likes=likes, member_count=member_count):
                self.assertTrue(passes_threshold(likes, member_count))
