"""Check a business website: robots.txt first, then fetch and compare with the listing.
Emails are read only from the business's own website (home + up to 2 contact/about pages)."""
import json
import re
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from app.config import USER_AGENT, HTTP_TIMEOUT
from app.data_processing.normalize import normalize_name

NAME_MATCH = 85
PHONE_RE = re.compile(r"\+?\d[\d\s\-]{8,}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
EMAIL_FULL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PINCODE_RE = re.compile(r"\b\d{6}\b")

# Directory / listing sites are NOT the business's official website.
DIRECTORY_DOMAINS = (
    "justdial.com", "dialmia.com", "practo.com", "sulekha.com", "indiamart.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "tripadvisor.com", "yellowpages.com", "lybrate.com",
    "zomato.com", "swiggy.com", "mapquest.com", "wikipedia.org",
)
EXTRA_PATHS = ("/contact", "/contact-us", "/about")
MAX_EXTRA_PAGES = 2

JUNK_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
JUNK_PARTS = ("example.", "sentry", "wixpress", "yourdomain", "domain.com", "email.com")


def is_directory(url):
    """True if the url belongs to a directory / social site."""
    host = (urlparse(url if "//" in url else "https://" + url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in DIRECTORY_DOMAINS)


def decode_cfemail(hexstr):
    """Cloudflare protected email (data-cfemail) -> plain email, or None."""
    try:
        data = bytes.fromhex(hexstr)
        key = data[0]
        return bytes(b ^ key for b in data[1:]).decode()
    except (ValueError, UnicodeDecodeError, IndexError):
        return None


def _clean_email(raw):
    e = (raw or "").strip().lower()
    if e.startswith("mailto:"):
        e = e[len("mailto:"):]
    e = e.split("?")[0].strip().rstrip(".")
    if not EMAIL_FULL_RE.match(e):
        return None
    if e.endswith(JUNK_SUFFIX) or any(j in e for j in JUNK_PARTS):
        return None
    return e


def _deobfuscate(text):
    text = re.sub(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", "@", text, flags=re.I)
    text = re.sub(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", ".", text, flags=re.I)
    return text


def _walk_json(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == "email" and isinstance(v, str):
                out.append(v)
            else:
                _walk_json(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_json(v, out)


def extract_emails(html):
    """Pure function. mailto links, Cloudflare data-cfemail, JSON-LD, [at]/(at) forms, visible text."""
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("mailto:"):
            found.extend(a["href"][7:].split(","))

    for tag in soup.find_all(attrs={"data-cfemail": True}):
        decoded = decode_cfemail(tag["data-cfemail"])
        if decoded:
            found.append(decoded)

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            _walk_json(json.loads(script.string or ""), found)
        except ValueError:
            pass

    text = _deobfuscate(soup.get_text(" ")[:200_000])
    found.extend(EMAIL_RE.findall(text))

    cleaned = {_clean_email(e) for e in found}
    return sorted(e for e in cleaned if e)


def compare_page(business, html):
    """Pure function (no internet). Compare listing facts with page text.
    Returns {"name_match": bool, "conflicts": [...], "emails": [...]}"""
    text = BeautifulSoup(html, "html.parser").get_text(" ")[:200_000]
    conflicts = []

    # 1. name
    name_norm = business.get("name_norm") or ""
    name_match = fuzz.partial_ratio(name_norm, normalize_name(text)) >= NAME_MATCH if name_norm else False
    if name_norm and not name_match:
        conflicts.append("website name mismatch")

    # 2. phone: conflict only if the page shows phone numbers and none match
    phone = business.get("phone_norm")
    page_numbers = {re.sub(r"\D", "", m)[-10:] for m in PHONE_RE.findall(text)}
    if phone and page_numbers and phone not in page_numbers:
        conflicts.append("phone mismatch")

    # 3. address: compare pincode if both sides have one
    listing_pins = set(PINCODE_RE.findall(business.get("address") or ""))
    page_pins = set(PINCODE_RE.findall(text))
    if listing_pins and page_pins and not (listing_pins & page_pins):
        conflicts.append("address mismatch")

    return {"name_match": name_match, "conflicts": conflicts, "emails": extract_emails(html)}


async def robots_allows(client, url):
    """True only if robots.txt allows us. If we cannot read it, we do not fetch."""
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        r = await client.get(robots_url, follow_redirects=True)
    except httpx.HTTPError:
        return False
    if r.status_code >= 500:
        return False
    if r.status_code >= 400:      # no robots.txt = allowed
        return True
    parser = RobotFileParser()
    parser.parse(r.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


async def _fetch_page(client, url):
    """Returns html text or None. Respects robots.txt."""
    if not await robots_allows(client, url):
        return None
    try:
        r = await client.get(url, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if r.status_code != 200 or is_directory(str(r.url)):
        return None
    return r.text


async def check_website(business, client):
    """Returns {"state": no_website | directory | blocked | error | checked, "url",
    "conflicts", "emails", "name_match", "email_source"}
    email_source = the page url where the first email was found (or None)."""
    url = (business.get("website") or "").strip()
    result = {"state": "no_website", "url": None, "conflicts": [], "emails": [],
              "name_match": False, "email_source": None}
    if not url:
        return result
    if "//" not in url:
        url = "https://" + url
    result["url"] = url

    if is_directory(url):
        result["state"] = "directory"
        return result

    if not await robots_allows(client, url):
        result["state"] = "blocked"
        return result
    try:
        r = await client.get(url, follow_redirects=True)
    except httpx.HTTPError:
        result["state"] = "error"
        return result
    if r.status_code != 200:
        result["state"] = "error"
        return result
    if is_directory(str(r.url)):          # redirected to a directory page
        result["state"] = "directory"
        return result

    home = compare_page(business, r.text)
    result.update(home)
    result["state"] = "checked"
    if home["emails"]:
        result["email_source"] = str(r.url)

    # Contact / about pages: only emails are read from them.
    if not result["emails"] and result["name_match"] and not result["conflicts"]:
        base = str(r.url)
        extra = 0
        for path in EXTRA_PATHS:
            if extra >= MAX_EXTRA_PAGES or result["emails"]:
                break
            page_url = urljoin(base, path)
            html = await _fetch_page(client, page_url)
            if html is None:
                continue
            extra += 1
            emails = extract_emails(html)
            if emails:
                result["emails"] = emails
                result["email_source"] = page_url
    return result


def make_client():
    """One shared client for the pipeline."""
    return httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)