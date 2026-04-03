# Product Note

## Failure modes noticed

Beyond the two core issues stated in the problem statement, I noticed three practical failure modes. First, there is terms mismatch: users may say `coffee` or `travel`, while the rules use categories like `dining`, `hotels`, or `travel_portal`. Second, fuzzy matching improves merchant coverage but can introduce false positives, which is risky because a wrong confident match is worse than a lower-confidence fallback. Third, the current card rules are simplified, so a card may look optimal from headline earn rates while still being invalid under real constraints like caps, minimum spend, exclusions, or MCC rules.

## What I would log or store

- Raw query: merchant, category hint, amount, available cards
- Merchant resolution: normalized merchant, matched merchant, fuzzy match score
- Category resolution: raw hint, canonicalized hint, resolved category
- Recommendation output: ranked cards, selected card, confidence, reward gap vs runner-up
- Fallback/update signals: merchant missing, category conflict, card rule gap, close call
- Feedback signals if available later: accepted recommendation, override, merchant/category correction

These logs would help separate data coverage issues from ranking issues and create a feedback loop for improving the knowledge base over time.

## How I would improve merchant/card coverage

I would first improve the terms and merchant mapping layer by adding merchant aliases (unique identifier for merchants), reviewer-approved mappings, and a queue for repeated unknown merchants. This is the fastest way to reduce obvious recommendation failures.

I would then expand the card rule schema to capture more realistic reward logic such as minimum spend, caps, exclusions, and channel-specific bonuses. I would keep the live recommendation path deterministic, and use AI only to suggest candidate KB updates for human review.

## Next 2-week roadmap

Week 1: Improve merchant normalization, alias coverage, and the update queue for unknown merchants and category conflicts.

Week 2: Expand the card rule schema to support richer constraints such as minimum spend requirements and add more regression test cases. I will also start tracking logs and metrics such as unknown merchant rate, confidence mix, and recommendation override rate.
