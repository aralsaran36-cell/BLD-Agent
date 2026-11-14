"""Remove businesses that match the user's exclusion words."""


def apply_exclusions(businesses, words):
    """Returns (kept, removed). Each removed item gets 'excluded_because'."""
    words = [w.strip().lower() for w in words if w and w.strip()]
    if not words:
        return list(businesses), []

    kept = []
    removed = []
    for b in businesses:
        name = (b.get("name") or "").lower()
        category = (b.get("category") or "").lower()
        text = name + " " + category

        hit = None
        for w in words:
            if w in text:
                hit = w
                break

        if hit:
            removed.append({**b, "excluded_because": hit})
        else:
            kept.append(b)
    return kept, removed


def summarize_removed(removed):
    """Short text for the status line, e.g. '2 removed (dental: 1, pharmacy: 1)'."""
    if not removed:
        return "0 removed"
    counts = {}
    for r in removed:
        word = r["excluded_because"]
        counts[word] = counts.get(word, 0) + 1
    detail = ", ".join(f"{w}: {n}" for w, n in counts.items())
    return f"{len(removed)} removed ({detail})"


if __name__ == "__main__":
    sample = [
        {"name": "Vijay Hospital"},
        {"name": "Smile Dental Clinic"},
        {"name": "City Pharmacy"},
    ]
    kept, removed = apply_exclusions(sample, ["dental", "pharmacy"])
    print(kept)
    print(summarize_removed(removed))