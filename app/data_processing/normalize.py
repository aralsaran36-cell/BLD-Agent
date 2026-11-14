"""Clean name, address, phone, website so businesses from different sources can be compared."""
import re
from urllib.parse import urlparse

import phonenumbers


def _clean_text(text):
    """lowercase, remove punctuation, collapse spaces."""
    if not text:
        return ""
    text = text.lower().replace("'", "")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
    


def normalize_name(name):
    return _clean_text(name)


def normalize_address(address):
    return _clean_text(address)


def normalize_phone(raw, region="IN"):
    """'+91 98765-43210' -> '9876543210'. Returns None if not a possible number.
    We never guess or fill a missing phone."""
    if not raw or not raw.strip():
        return None
    try:
        parsed = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(parsed):
        return None
    return str(parsed.national_number)


def normalize_domain(url):
    """'https://www.VijayHospital.in/contact' -> 'vijayhospital.in'."""
    if not url or not url.strip():
        return None
    url = url.strip().lower()
    if "//" not in url:
        url = "//" + url
    host = urlparse(url).netloc.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or None


def normalize_business(b):
    """Keep original fields (for display), add normalized ones (for matching)."""
    return {
        **b,
        "name_norm": normalize_name(b.get("name")),
        "address_norm": normalize_address(b.get("address")),
        "phone_norm": normalize_phone(b.get("phone")),
        "domain": normalize_domain(b.get("website")),
    }


if __name__ == "__main__":
    print(normalize_phone("+91 98765-43210"))
    print(normalize_phone("0422 2456789"))
    print(normalize_phone(""))
    print(normalize_name("  VIJAY   Hospital!! "))
    print(normalize_domain("https://www.VijayHospital.in/contact"))
    print(normalize_business({"name": "Vijay Hospital", "phone": "+91 98765-43210"}))