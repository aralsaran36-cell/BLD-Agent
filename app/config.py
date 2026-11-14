"""Central settings. Every other file imports from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "BLD Agent"

# --- Keys and identity (from .env) ---
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")

# Nominatim and Overpass require a real User-Agent that identifies the app.
USER_AGENT = f"BLDAgent/0.1 ({CONTACT_EMAIL or 'no-contact-set'})"

# --- Database ---
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "bld_agent.db"))

# --- External endpoints ---
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

# --- Limits ---
HTTP_TIMEOUT = 20             # seconds
NOMINATIM_MIN_INTERVAL = 1.0  # Nominatim policy: max 1 request per second
GOOGLE_MAX_PAGES = 3

def google_enabled() -> bool:
    """True only if a Google key is present."""
    return bool(GOOGLE_PLACES_API_KEY.strip())