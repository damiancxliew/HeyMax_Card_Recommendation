import unittest

from engine import SpendRecommendationEngine, canonicalize_category


class SpendRecommendationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SpendRecommendationEngine(None, None)

    def test_known_merchant_prefers_best_category_card(self) -> None:
        result = self.engine.recommend(
            merchant="Starbucks",
            category_hint="coffee",
            amount=12.5,
            user_cards=["Max Cashback+", "Max Travel Visa"],
        )
        self.assertEqual(result["recommended_card"], "Max Cashback+")
        self.assertEqual(result["estimated_reward_rate"], 5.0)
        self.assertEqual(result["confidence"], "high")
        self.assertFalse(result["needs_update"])
        self.assertIsNone(result["type"])
        self.assertIsNone(result["reason"])

    def test_fuzzy_merchant_match_works(self) -> None:
        result = self.engine.recommend(
            merchant="Amazon SG",
            category_hint="shopping",
            amount=84.2,
            user_cards=["Max Online Rewards", "Max Everyday Mastercard"],
        )
        self.assertEqual(result["matched_merchant"], "Amazon")
        self.assertEqual(result["resolved_category"], "online_shopping")
        self.assertEqual(result["recommended_card"], "Max Online Rewards")
        self.assertEqual(result["confidence"], "high")
        self.assertFalse(result["needs_update"])

    def test_unknown_merchant_queues_update(self) -> None:
        result = self.engine.recommend(
            merchant="Don Don Donki",
            category_hint="groceries",
            amount=45.0,
            user_cards=["Max Cashback+", "Max Everyday Mastercard"],
        )
        self.assertEqual(result["recommended_card"], "Max Cashback+")
        self.assertEqual(result["confidence"], "medium")
        self.assertTrue(result["needs_update"])
        self.assertEqual(result["type"], "merchant_missing")
        self.assertEqual(
            result["reason"],
            "Merchant not found in known merchant database.",
        )

    def test_category_conflict_is_flagged(self) -> None:
        result = self.engine.recommend(
            merchant="Agoda",
            category_hint="travel",
            amount=220.0,
            user_cards=["Max Travel Visa", "Max Cashback+"],
        )
        self.assertEqual(result["recommended_card"], "Max Travel Visa")
        self.assertEqual(result["confidence"], "medium")
        self.assertTrue(result["needs_update"])
        self.assertEqual(result["type"], "category_conflict")
        self.assertIn("incoming hint looks like 'travel_portal'", result["reason"])

    def test_unknown_user_cards_returns_nested_update_object(self) -> None:
        result = self.engine.recommend(
            merchant="Starbucks",
            category_hint="coffee",
            amount=12.5,
            user_cards=["Imaginary Card"],
        )
        self.assertIsNone(result["recommended_card"])
        self.assertEqual(result["confidence"], "low")
        self.assertIn("update_needed", result)
        self.assertTrue(result["update_needed"]["needs_update"])
        self.assertEqual(result["update_needed"]["type"], "user_cards_unknown")

    def test_general_fallback_creates_card_rule_gap(self) -> None:
        result = self.engine.recommend(
            merchant="Starbucks",
            category_hint="coffee",
            amount=20.0,
            user_cards=["Max Everyday Mastercard"],
        )
        self.assertEqual(result["recommended_card"], "Max Everyday Mastercard")
        self.assertEqual(result["estimated_reward_rate"], 1.5)
        self.assertEqual(result["candidate_cards"][0]["matched_category"], "general")
        self.assertEqual(result["confidence"], "medium")
        self.assertTrue(result["needs_update"])
        self.assertEqual(result["type"], "card_rule_gap")

    def test_branch_style_merchant_name_still_matches(self) -> None:
        result = self.engine.recommend(
            merchant="Starbucks Orchard",
            category_hint="cafe",
            amount=9.0,
            user_cards=["Max Cashback+", "Max Travel Visa"],
        )
        self.assertEqual(result["matched_merchant"], "Starbucks")
        self.assertEqual(result["recommended_card"], "Max Cashback+")
        self.assertEqual(result["confidence"], "high")

    def test_no_category_hint_and_unknown_merchant_falls_back_to_general(self) -> None:
        result = self.engine.recommend(
            merchant="Mystery Boutique",
            category_hint="",
            amount=60.0,
            user_cards=["Max Travel Visa", "Max Everyday Mastercard"],
        )
        self.assertEqual(result["resolved_category"], "general")
        self.assertEqual(result["recommended_card"], "Max Everyday Mastercard")
        self.assertEqual(result["estimated_reward_rate"], 1.5)
        self.assertEqual(result["confidence"], "low")
        self.assertTrue(result["needs_update"])
        self.assertEqual(result["type"], "merchant_missing")

    def test_empty_user_cards_considers_all_cards(self) -> None:
        result = self.engine.recommend(
            merchant="Singapore Airlines",
            category_hint="flight",
            amount=100.0,
            user_cards=[],
        )
        self.assertEqual(result["recommended_card"], "Max Travel Visa")
        self.assertEqual(result["estimated_reward_rate"], 4.0)
        self.assertEqual(result["confidence"], "high")

    def test_category_normalization_for_unseen_inputs(self) -> None:
        self.assertEqual(canonicalize_category("Taxi"), "transport")
        self.assertEqual(canonicalize_category("restaurant"), "dining")
        self.assertEqual(canonicalize_category("supermarket"), "groceries")


if __name__ == "__main__":
    unittest.main()
