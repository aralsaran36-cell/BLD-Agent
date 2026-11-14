"""Template reason. Uses only facts we really have. Never invents anything."""


def build_reason(lead, breakdown, user_category):
    parts = []

    category = lead.get("category")
    if category and breakdown.get("category", 0) > 0:
        parts.append(f"Listed as '{category}', which matches your category '{user_category}'.")
    elif category:
        parts.append(f"Listed as '{category}', which does not clearly match '{user_category}'.")
    else:
        parts.append("Category not listed.")

    if lead.get("distance_km") is not None:
        parts.append(f"Located {lead['distance_km']:.1f} km from the search centre.")

    sources = lead.get("sources") or []
    if sources:
        names = ", ".join(s["name"] for s in sources)
        parts.append(f"Found in {len(sources)} source(s): {names}.")

    missing = [f for f in ("phone", "email", "website") if not lead.get(f)]
    if missing:
        parts.append("Not found: " + ", ".join(missing) + ".")

    return " ".join(parts)