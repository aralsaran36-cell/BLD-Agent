"""Decide the verification status. Fixed rules, no AI. Rule order matters."""

# Independent sources: each counts once.
INDEPENDENT = {"google", "osm", "website"}


def decide_status(facts):
    """facts = {"closed": bool, "sources": [names], "conflicts": [texts]}
    Returns (status, rule_text). Rules are checked top to bottom."""
    closed = facts.get("closed", False)
    sources = set(facts.get("sources", [])) & INDEPENDENT
    conflicts = facts.get("conflicts", [])

    # Rule 1: closed permanently or no evidence
    if closed:
        return "rejected", "closed permanently"
    if not sources:
        return "rejected", "no source evidence"

    # Rule 2: key facts disagree
    if conflicts:
        return "unverified", "conflict: " + ", ".join(conflicts)

    # Rule 3: two or more independent sources
    if len(sources) >= 2:
        return "verified", f"{len(sources)} independent sources: " + ", ".join(sorted(sources))

    # Rule 4: exactly one source
    return "partially_verified", "only one source: " + next(iter(sources))