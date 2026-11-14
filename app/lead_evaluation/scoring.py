"""Relevance score (0-100) with a factor breakdown. Separate from verification status."""

WEIGHTS = {"geographic": 40, "category": 30, "evidence": 30}
EVIDENCE_FIELDS = ["phone", "email", "website", "address"]


def geographic_points(distance_km, radius_km):
    """Closer to the centre = more points. At the edge of the radius = half."""
    if distance_km is None or not radius_km:
        return 0
    ratio = min(distance_km / radius_km, 1)
    return round(WEIGHTS["geographic"] * (1 - 0.5 * ratio))


def category_terms(user_category):
    """'Hospitals, Clinics' -> ['hospital', 'clinic']"""
    terms = [t.strip().lower() for t in user_category.split(",")]
    return [t[:-1] if t.endswith("s") else t for t in terms if t]


def category_points(lead, user_category):
    text = ((lead.get("category") or "") + " " + (lead.get("name") or "")).lower()
    for term in category_terms(user_category):
        if term in text:
            return WEIGHTS["category"]
    return 0


def evidence_points(lead):
    present = sum(1 for f in EVIDENCE_FIELDS if lead.get(f))
    return round(WEIGHTS["evidence"] * present / len(EVIDENCE_FIELDS))


def score_lead(lead, radius_km, user_category):
    breakdown = {
        "geographic": geographic_points(lead.get("distance_km"), radius_km),
        "category": category_points(lead, user_category),
        "evidence": evidence_points(lead),
    }
    return {"score": sum(breakdown.values()), "breakdown": breakdown}