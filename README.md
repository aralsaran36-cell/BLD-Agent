# BLD Agent (Business Lead Discovery)

Evidence-based, location-aware business lead finder. Rule-based, no LLM.
You enter an area, radius, product, category and exclusions. It returns businesses with phone, email, website, address, distance, verification status, relevance score, and the source and date of each fact.

Rule: missing data stays missing and is shown as "Not found". Nothing is guessed.

## Features
- Area lookup: Nominatim, then spelling variants, then Google area search, then district fallback. Every fallback shows a note.
- Sources: Google Places (New) and OpenStreetMap Overpass, run in parallel.
- Normalize, radius filter, duplicate merge (provenance kept), exclusions.
- Website check: robots.txt respected, directory sites (justdial, dialmia, practo etc.) rejected, name/phone/pincode compared.
- Email only from the OSM tag or the business's own website, with the source page URL.
- Status: verified, partially_verified, unverified, rejected. Score is separate.
- Live result cards, full CSV download.

## Setup
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Create a .env file in the project root with your Google Places API key (variable name must match app/config.py). Never commit .env.

## Run
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000

## Test
    python -m pytest tests -q

## Structure
- app/ : config, db, schemas, pipeline, main
- app/data_collection/ : geocode, overpass, google_places
- app/data_processing/ : normalize, distance, dedupe, exclusions
- app/lead_evaluation/ : website, verifier, scoring, reason
- app/output/export.py : CSV
- frontend/ : index.html, app.js, style.css
- docs/ : compliance, connectors, methodology, architecture
- tests/

## Known limits
- Google gives no email, so email depends on the OSM tag or website pages.
- JavaScript-rendered websites and non-standard contact URLs are missed.
- Small villages have little OSM data.
- Verification is source-count based. Field-wise verification is planned.
- Category type filter on Google is only for "hospital".
- Search history UI is not built yet (backend routes exist).

## Attribution
Map data (c) OpenStreetMap contributors (ODbL). Google Places data is used under Google Maps Platform terms.