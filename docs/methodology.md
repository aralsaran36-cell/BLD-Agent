# Verification and Scoring Methodology

Verification status and relevance score are separate. Both are rule-based. No LLM is used.

## Verification status (app/lead_evaluation/verifier.py)
Independent sources: google, osm, website. Each counts once. Rules are checked top to bottom.
1. Closed permanently: rejected.
2. No source evidence: rejected.
3. Any conflict (website name, phone or pincode mismatch): unverified. The conflict text is shown.
4. Two or more independent sources: verified.
5. One source: partially_verified.

A website counts as a source only if it is not a directory, robots allows it, it was fetched, the name matches and there is no conflict.

Each decision is stored in verification_events with the rule text.

Known limit: this is source-count based. Field-wise verification (name, location, phone, website each confirmed by 2 sources) is planned, not built yet. Email and phone are never labelled verified on their own.

## Relevance score (app/lead_evaluation/scoring.py)
Factors required by the brief: geographic match, product/service fit, category fit, evidence completeness and freshness.
TO VERIFY: copy the exact factors, weights and formula from scoring.py (run: cat app/lead_evaluation/scoring.py).
The score is shown with its breakdown. It is not objective truth.

## Relevance reason (app/lead_evaluation/reason.py)
Built from the score factors. Always shown with the label "(inference)". It is never treated as a verified fact.

## Missing data
Missing values stay missing and are shown as "Not found". Nothing is invented.

## Deduplication
Same lead from Google and OSM is merged by domain, normalized name and location. Provenance (all sources) is kept. A possible_duplicate flag marks uncertain cases. TO VERIFY: exact thresholds in dedupe.py.

## Conflicts
If sources disagree, the conflict is recorded and the lead becomes unverified. The system does not choose one value silently.

## Evidence
Every fact is saved in the evidence table: fact, value, source names, source URL, retrieved_at. An email's source URL is the page where it was found.

## Test coverage
Unit tests cover normalization, dedupe, exclusions, distance, scoring, reason, verifier, parsers, website mismatch, email extraction, export, missing data and API failure. TO VERIFY: a named test dataset with valid, duplicate, stale, conflicting and non-existent businesses is still pending.