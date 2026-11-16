# Source Connectors

All connectors return one common record shape: source, source_id, name, category, address, phone, email (OSM only), website, lat, lng, closed, source_url, retrieved_at. A connector failure raises ConnectorError. The pipeline continues with the other source and shows a note.

## 1. Geocode (app/data_collection/geocode.py)
- Input: area text. Output: matches (id, label, lat, lng) plus an optional note.
- Order: Nominatim exact, spelling variants (rr/r, tt/t, tty/tti), Google Text Search area lookup, then parent/district fallback.
- Every fallback returns a note shown to the user. Nothing is silent.
- countrycodes=in, 1 retry, 1 request per second, successful results cached.
- Known limit: a Google area result can be a road point, not the village centre.

## 2. OSM Overpass (app/data_collection/overpass.py)
- Input: lat, lng, radius, category text.
- Category text is mapped to OSM tags by the CATEGORY_TAGS table (about 50 categories: health, education, food, shops, services).
- Unmapped category: raises ConnectorError ("not mapped to OSM tags yet").
- Reads name, address parts, phone, website, email (email or contact:email). Unnamed places are skipped.
- Known limit: small villages have little OSM data.

## 3. Google Places (app/data_collection/google_places.py)
- Text Search with query "{category} in {area}", locationBias circle (radius capped at 50 km), pageSize 20, paging up to GOOGLE_MAX_PAGES.
- Field mask: id, displayName, formattedAddress, location, nationalPhoneNumber, websiteUri, googleMapsUri, businessStatus, primaryTypeDisplayName, primaryType, types.
- Type filter (includedType + strictTypeFiltering) only for "hospital". Other categories use text query only. TO VERIFY: Google accepts these fields without HTTP 400.
- CLOSED_PERMANENTLY maps to closed = true.
- Known limit: no email field.

## 4. Website check (app/lead_evaluation/website.py)
- Steps: block directory domains, check robots.txt, fetch home page, compare facts, then read /contact, /contact-us, /about (max 2 extra pages) only if the name matches and there is no conflict.
- Compared facts: name (fuzzy, threshold 85), phone, pincode.
- Email extraction: mailto links, Cloudflare data-cfemail, JSON-LD email, [at]/(dot) forms, visible text. Junk addresses are filtered.
- Result states: no_website, directory, blocked, error, checked. The source page URL is saved as email_source.
- Known limits: JavaScript-rendered pages, other contact URLs.

## Pipeline order
geocode, Google + OSM (parallel), normalize, radius filter, dedupe, exclusions, website check, verifier, score and reason, save, stream to UI.