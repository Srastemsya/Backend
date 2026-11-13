import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "runtime"))

from room_rules import category_weights, order_candidates, passes_threshold, top_score


class ThresholdTests(unittest.TestCase):
    def test_below_threshold(self):
        for likes, member_count in [(1, 2), (2, 3), (2, 4), (3, 5), (4, 6), (4, 7), (6, 10)]:
            with self.subTest(likes=likes, member_count=member_count):
                self.assertFalse(passes_threshold(likes, member_count))

    def test_at_or_above_threshold(self):
        for likes, member_count in [(2, 2), (3, 3), (3, 4), (4, 5), (5, 6), (5, 7), (7, 10)]:
            with self.subTest(likes=likes, member_count=member_count):
                self.assertTrue(passes_threshold(likes, member_count))


class PoolOrderingTests(unittest.TestCase):
    def test_empty_history(self):
        self.assertEqual(category_weights([]), {})

    def test_equal_weights_preserve_catalog_order(self):
        items = [
            {"id": "z", "categoryId": "unshown"},
            {"id": "a", "categoryId": "neutral"},
            {"id": "m", "categoryId": "unshown"},
        ]
        self.assertEqual(order_candidates(items, {"neutral": 0}), items)

    def test_weights_accumulate_over_mixed_rounds(self):
        catalog = [
            {"id": number, "categoryId": (
                "a" if number % 2 else "b"
            ) if number <= 10 else "abc"[(number - 11) % 3]}
            for number in range(1, 36)
        ]
        first, unseen = catalog[:10], catalog[10:]
        history = [{"cards": [
            {**card, "likes": 3, "passes": 2} if card["categoryId"] == "a"
            else {**card, "likes": 0, "passes": 5}
            for card in first
        ]}]
        weights = category_weights(history)
        self.assertEqual(weights, {"a": 5, "b": -25})
        second = order_candidates(unseen, weights)[:10]
        second_ids = [card["id"] for card in second]
        self.assertEqual(second_ids, [11, 14, 17, 20, 23, 26, 29, 32, 35, 13])

        history.append({"cards": [
            {**card, "likes": 2, "passes": 3} if card["categoryId"] == "a"
            else {**card, "likes": 0, "passes": 5}
            for card in second
        ]})
        weights = category_weights(history)
        self.assertEqual(weights, {"a": -4, "b": -25, "c": -5})
        third = order_candidates([card for card in unseen if card["id"] not in second_ids], weights)[:10]
        self.assertEqual([card["id"] for card in third], [16, 19, 22, 25, 28, 31, 34, 12, 15, 18])


class TopScoreTests(unittest.TestCase):
    @staticmethod
    def completed_round(*scores):
        return {"cards": [
            {"ref": {"kind": "EVENT", "id": candidate_id}, "likes": likes}
            for candidate_id, likes in scores
        ]}

    def test_empty_history(self):
        self.assertIsNone(top_score([]))

    def test_zero_likes(self):
        self.assertIsNone(top_score([self.completed_round(("first", 0), ("second", 0))]))

    def test_later_round_has_highest_score(self):
        history = [self.completed_round(("first", 1)), self.completed_round(("second", 2))]
        self.assertEqual(top_score(history), ({"kind": "EVENT", "id": "second"}, 2))

    def test_tie_prefers_earlier_round(self):
        history = [self.completed_round(("first", 2)), self.completed_round(("second", 2))]
        self.assertEqual(top_score(history), ({"kind": "EVENT", "id": "first"}, 2))

    def test_tie_prefers_earlier_pool_card(self):
        history = [self.completed_round(("z", 2), ("a", 2))]
        self.assertEqual(top_score(history), ({"kind": "EVENT", "id": "z"}, 2))
