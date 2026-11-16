# Source Compliance Notes

Last reviewed: 16 Nov 2026. Items marked TO VERIFY must be checked against the official terms before submission.

## Sources used
| Source | Used for | Access | Attribution |
|---|---|---|---|
| Nominatim (OpenStreetMap) | Area text to lat/lng | Public API, no key | Yes: OpenStreetMap contributors |
| OSM Overpass API | Business candidates (amenity/shop tags) | Public API, no key | Yes: OpenStreetMap contributors (ODbL) |
| Google Places API (New), Text Search | Business candidates, area fallback | API key in .env | TO VERIFY: Google Maps Platform terms |
| Business websites | Official website check, public email | Plain HTTP fetch | Source URL stored with each email |

## Rate limits and polite use
- Nominatim: maximum 1 request per second (enforced in geocode.py with a lock and minimum interval). Results are cached per area text. A descriptive User-Agent is sent.
- Overpass: one query per search. TO VERIFY: current public server limits.
- Google Places: field mask limited to needed fields. Paging capped by GOOGLE_MAX_PAGES. TO VERIFY: quota and pricing. Daily quota cap and budget alert: not set yet.
- Websites: robots.txt is checked before every fetch. If robots.txt cannot be read, we do not fetch. At most 3 pages per business (home + up to 2 of /contact, /contact-us, /about).

## Restrictions we respect
- No login, CAPTCHA or paywall bypass. No scraping of personal profiles.
- Directory and social sites (justdial, dialmia, practo, sulekha, indiamart, facebook, instagram, linkedin and others) are never treated as the official website and are not scraped for contacts.
- Emails come only from the business's own website or the OSM email tag. Google gives no email. Nothing is guessed.
- Missing data is shown as "Not found".

## Attribution
- The UI footer shows "Map data (c) OpenStreetMap contributors" with a link to openstreetmap.org/copyright. It must stay visible.
- TO VERIFY: Google attribution requirements for displayed Places data.

## Data storage
- Raw connector records, evidence rows (fact, value, source, source URL, retrieved_at) and verification events are stored in SQLite (data/bld_agent.db).
- Google raw_json is not stored (raw_json = None). TO VERIFY: Google terms on caching and storage.
- API keys live only in .env, which is excluded from git.

## Privacy
- Only public business contact details are collected. No owner identity, revenue or history is inferred.