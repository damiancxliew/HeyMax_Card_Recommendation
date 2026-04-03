from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine import SpendRecommendationEngine, load_json


def parse_args() :
    parser = argparse.ArgumentParser(
        description="Recommend the best card for a spend event."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample_queries.json"),
        help="Path to a JSON file containing one query or a list of queries.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    payload = load_json(args.input)
    queries = payload if isinstance(payload, list) else [payload]

    engine = SpendRecommendationEngine()
    results = [
        engine.recommend(
            merchant=query["merchant"],
            category_hint=query.get("category_hint", ""),
            amount=float(query["amount"]),
            user_cards=query.get("user_cards"),
        )
        for query in queries
    ]
    print(json.dumps(results, indent=2))
    output_path = "./output/output.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
