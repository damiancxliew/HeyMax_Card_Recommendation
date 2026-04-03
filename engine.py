from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent / "data"


CATEGORY_SYNONYMS = {
    "coffee": "dining",
    "cafe": "dining",
    "cafes": "dining",
    "restaurant": "dining",
    "food": "dining",
    "shopping": "online_shopping",
    "ecommerce": "online_shopping",
    "e-commerce": "online_shopping",
    "e commerce": "online_shopping",
    "supermarket": "groceries",
    "grocery": "groceries",
    "travel": "travel_portal",
    "hotel": "hotels",
    "flight": "airlines",
    "airline": "airlines",
    "ride": "transport",
    "taxi": "transport",
}


@dataclass
class CardOption:
    card_name: str
    matched_category: str
    reward_rate: float
    estimated_rewards: float


def load_json(path) :
    with path.open() as f:
        return json.load(f)


def normalize_text(value):
    lowered = value.lower().strip()
    lowered = re.sub(r"\b(sg|pte ltd|ltd|inc|co)\b", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def canonicalize_category(category_hint):
    if not category_hint:
        return None
    normalized = normalize_text(category_hint)
    return CATEGORY_SYNONYMS.get(normalized, normalized or None)


class SpendRecommendationEngine:
    def __init__(self, cards = None, merchants = None):
        self.cards = cards or load_json(DATA_DIR / "cards.json")
        self.merchants = merchants or load_json(DATA_DIR / "merchants.json")

    def find_merchant(self, merchant_name):
        query = normalize_text(merchant_name)
        best_match = None
        best_score = 0.0

        for merchant in self.merchants:
            candidate = merchant["normalized_name"]
            score = SequenceMatcher(None, query, candidate).ratio()
            if query == candidate:
                return merchant, 1.0
            if query.startswith(candidate) or candidate in query:
                score = max(score, 0.90) # boost score for substring matches
            if score > best_score:
                best_score = score
                best_match = merchant

        if best_score >= 0.80:
            return best_match, best_score
        return None, best_score

    def get_reward_rate(self, card, category):
        general_rate = 0.0
        for rule in card["earn_rules"]:
            if rule["category"] == category:
                return float(rule["reward_rate"]), category
            if rule["category"] == "general":
                general_rate = float(rule["reward_rate"])
        return general_rate, "general"

    def recommend(self, merchant, category_hint, amount, user_cards):
        merchant_match, merchant_score = self.find_merchant(merchant)
        hint_category = canonicalize_category(category_hint)
        merchant_category = merchant_match["category"] if merchant_match else None

        chosen_category = merchant_category or hint_category or "general"
        update_flags = []

        if merchant_match is None:
            update_flags.append(
                {
                    "type": "merchant_missing",
                    "detail": "Merchant not found in known merchant database.",
                }
            )

        if merchant_match and hint_category and merchant_category != hint_category:
            update_flags.append(
                {
                    "type": "category_conflict",
                    "detail": (
                        f"Merchant data maps to '{merchant_category}' but the incoming hint "
                        f"looks like '{hint_category}'."
                    ),
                }
            )

        eligible_cards = self.cards
        if user_cards:
            user_card_set = set(user_cards)
            eligible_cards = [card for card in self.cards if card["card_name"] in user_card_set]

        if not eligible_cards:
            return {
                "recommended_card": None,
                "estimated_reward_rate": 0.0,
                "estimated_rewards": 0.0,
                "explanation": "None of the provided user cards matched the card catalog.",
                "confidence": "low",
                "matched_merchant": merchant_match["merchant_name"] if merchant_match else None,
                "resolved_category": chosen_category,
                "update_needed": {
                    "needs_update": True,
                    "type": "user_cards_unknown",
                    "reason": "User card list did not overlap with known card definitions.",
                },
            }

        options = []
        for card in eligible_cards:
            reward_rate, matched_category = self.get_reward_rate(card, chosen_category)
            options.append(
                CardOption(
                    card_name=card["card_name"],
                    matched_category=matched_category,
                    reward_rate=reward_rate,
                    estimated_rewards=round(reward_rate * amount, 2),
                )
            )

        options.sort(key=lambda option: (-option.reward_rate, option.card_name))
        best_option = options[0]
        runner_up = options[1] if len(options) > 1 else None

        confidence = "high"
        explanation_parts = []

        if merchant_match:
            if merchant_score < 0.95:
                explanation_parts.append(
                    f"Matched '{merchant}' to known merchant '{merchant_match['merchant_name']}'."
                )
            else:
                explanation_parts.append(
                    f"Recognized '{merchant_match['merchant_name']}' as '{chosen_category}'."
                )
        elif hint_category:
            explanation_parts.append(
                f"Merchant was unknown, so the recommendation relied on the category hint '{hint_category}'."
            )
        else:
            explanation_parts.append(
                "Merchant and category were unclear, so the recommendation fell back to general earn rates."
            )

        if best_option.matched_category == "general" and chosen_category != "general":
            update_flags.append(
                {
                    "type": "card_rule_gap",
                    "detail": (
                        f"No explicit earn rule was available for '{chosen_category}' on the recommended card."
                    ),
                }
            )
            confidence = "medium" if merchant_match else "low"

        if runner_up and abs(best_option.reward_rate - runner_up.reward_rate) <= 0.5:
            update_flags.append(
                {
                    "type": "close_call",
                    "detail": (
                        f"Top cards were close: {best_option.card_name} at {best_option.reward_rate}x "
                        f"vs {runner_up.card_name} at {runner_up.reward_rate}x."
                    ),
                }
            )
            confidence = "medium" if confidence == "high" else confidence
            explanation_parts.append(
                f"It was a close call versus {runner_up.card_name}."
            )

        if merchant_match is None:
            confidence = "medium" if hint_category else "low"
        elif update_flags and confidence == "high":
            confidence = "medium"

        explanation_parts.append(
            f"{best_option.card_name} earns {best_option.reward_rate}x in the resolved category."
        )

        update_summary = None
        if update_flags:
            update_types = update_flags[0]["type"]
            update_summary = update_flags[0]["detail"]

        update_needed = {
            "needs_update": bool(update_flags),
            "type": update_types if update_flags else None,
            "reason": update_summary if update_flags else None,
        }

        res_json = {
            "recommended_card": best_option.card_name,
            "estimated_reward_rate": best_option.reward_rate,
            "estimated_rewards": best_option.estimated_rewards,
            "explanation": " ".join(explanation_parts),
            "confidence": confidence,
            "matched_merchant": merchant_match["merchant_name"] if merchant_match else None,
            "resolved_category": chosen_category,
            **update_needed,
            "candidate_cards": [
                {
                    "card_name": option.card_name,
                    "reward_rate": option.reward_rate,
                    "matched_category": option.matched_category,
                    "estimated_rewards": option.estimated_rewards,
                }
                for option in options
            ],
        }

        return res_json
