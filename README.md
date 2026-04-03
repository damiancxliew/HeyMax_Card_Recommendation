# HeyMax Card Spend AI Prototype

This prototype recommends the best card for a spend event, explains the choice, assigns a confidence level, and flags cases that should be queued for data updates.

## How to run

```bash
python app.py
```

To run tests:

```bash
python -m unittest discover -s tests -v
```

To use a custom input file:

```bash
python app.py --input data/sample_queries.json 
python app.py --input data/extra_queries.json
```

Find generated recommendations in `output/output.json`

## What it does

- Resolves merchants using normalization plus lightweight fuzzy matching
- Maps noisy category hints into canonical categories
- Chooses the highest reward card from the user's available cards
- Falls back to general earn rates when a card does not have an explicit rule
- Returns `high`, `medium`, or `low` confidence
- Sets `needs_update` as `true` for missing merchants, category conflicts, close calls, and rule gaps

## Project structure

- `app.py`: CLI entrypoint
- `engine.py`: recommendation and detection logic
- `data/cards.json`: sample card rules
- `data/merchants.json`: sample merchant knowledge base
- `data/sample_queries.json`: example input queries
- `data/extra_queries.json`: extra input queries
- `tests/test_engine.py`: a few focused unit tests
- `output/output.json`: an output file generated from `app.py`
- `PRODUCT_NOTE.md`: short product and workflow note

## Assumptions

- `reward_rate` is interpreted as points or cashback units per dollar spent
- Merchant data is more reliable than a noisy free-text category hint, so the engine prefers merchant category when both exist
- If a merchant is unknown, the engine can still make a best-effort recommendation from the category hint.
- If no card has a specific category rule, falling back to the card’s general rate is acceptable, but confidence should be lower.
- For this prototype, a single best card is returned even if two cards are close
- Update signals are intended to represent items that should be reviewed and added to the merchant/card knowledge base later.

## Tradeoffs due to the 2-hour limit

- I used deterministic rules instead of an LLM or learned ranking model
- Merchant matching uses Python’s standard-library difflib.SequenceMatcher
- The project is a CLI script rather than a frontend or service.
- Card rules are intentionally simple and do not model exclusions, caps, T&Cs, promotions or currencies

## AI usage

I used AI as a coding assistant to help develop the prototype quickly and writing unit tests, but kept the implementation itself simple, deterministic, and easy to inspect.
