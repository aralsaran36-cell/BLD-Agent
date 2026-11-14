"""Orchestrator. Runs the whole flow and yields (event_name, data) for SSE."""
import asyncio
import logging

from app.config import google_enabled
from app.data_collection import ConnectorError
from app.data_collection.geocode import geocode_with_note
from app.data_collection.google_places import fetch_google
from app.data_collection.overpass import fetch_overpass
from app.data_processing.dedupe import dedupe
from app.data_processing.distance import filter_by_radius
from app.data_processing.exclusions import apply_exclusions, summarize_removed
from app.data_processing.normalize import normalize_business
from app.db import (get_search, maps_url_of, save_business, save_evidence, save_raw_records,
                    save_verification_event, set_search_location, set_search_status, utc_now)
from app.lead_evaluation.reason import build_reason
from app.lead_evaluation.scoring import score_lead
from app.lead_evaluation.verifier import decide_status
from app.lead_evaluation.website import check_website, make_client

log = logging.getLogger("bld")

CHOICES: dict[str, dict] = {}   # waiting state for the "pick an area" step


def register(search_id):
    CHOICES[search_id] = {"event": asyncio.Event(), "choice_id": None}


def provide_choice(search_id, choice_id):
    state = CHOICES.get(search_id)
    if state is None:
        return False
    state["choice_id"] = choice_id
    state["event"].set()
    return True


async def collect_sources(client, lat, lng, search):
    """Run Google + OSM in parallel. One down = continue with a note.
    Returns (records, notes, how_many_sources_worked)."""
    jobs = {"osm": fetch_overpass(client, lat, lng, search["radius_km"], search["category"])}
    notes = []
    if google_enabled():
        jobs["google"] = fetch_google(client, lat, lng, search["radius_km"],
                                      search["category"], search["area"])
    else:
        notes.append("Google Places is not configured. Using OpenStreetMap only.")

    results = await asyncio.gather(*jobs.values(), return_exceptions=True)
    records, worked = [], 0
    for name, result in zip(jobs, results):
        if isinstance(result, Exception):
            notes.append(f"{name} unavailable: {result}")
        else:
            worked += 1
            records.extend(result)
    return records, notes, worked


def _evidence_rows(lead):
    names = ", ".join(s["name"] for s in lead["sources"] if s.get("name"))
    url = next((s["url"] for s in lead["sources"] if s.get("url")), None)
    when = lead.get("retrieved_at") or utc_now()
    rows = []
    for fact in ("name", "address", "phone", "email", "website"):
        if not lead.get(fact):
            continue
        fact_url = lead.get("email_source") if fact == "email" and lead.get("email_source") else url
        rows.append((fact, str(lead[fact]), names, fact_url, when))
    return rows


async def run_search(search_id):
    search = get_search(search_id)
    if search is None:
        yield "error_event", {"message": "Search not found."}
        return
    try:
        async with make_client() as client:
            # --- E: geocode ---
            yield "status", {"message": f"Finding {search['area']} on the map..."}
            try:
                matches, note = await geocode_with_note(client, search["area"])
            except ConnectorError:
                yield "error_event", {"message": "Map lookup is unavailable right now. Try again."}
                return
            if not matches:
                yield "error_event", {"message": f"Area not found: {search['area']}"}
                return

            if note:
                yield "status", {"message": note}

            chosen = matches[0]
            if len(matches) > 1:
                yield "needs_choice", {"options": [{"id": m["id"], "label": m["label"]} for m in matches]}
                state = CHOICES.get(search_id)
                try:
                    await asyncio.wait_for(state["event"].wait(), timeout=300)
                except (asyncio.TimeoutError, AttributeError, TypeError):
                    yield "error_event", {"message": "No area was chosen. Search stopped."}
                    return
                chosen = next((m for m in matches if m["id"] == state["choice_id"]), None)
                if chosen is None:
                    yield "error_event", {"message": "Chosen area is invalid."}
                    return

            lat, lng, radius = chosen["lat"], chosen["lng"], search["radius_km"]
            set_search_location(search_id, lat, lng)
            yield "status", {"message": f"Found: {chosen['label']}"}

            # --- F, G: collect + save raw ---
            yield "status", {"message": "Collecting businesses..."}
            records, notes, worked = await collect_sources(client, lat, lng, search)
            for note_text in notes:
                yield "status", {"message": note_text}
            if worked == 0:
                set_search_status(search_id, "failed")
                yield "error_event", {"message": "All data sources failed. Try again later."}
                return
            save_raw_records(search_id, records)

            # --- H, I, J, K: process ---
            normalized = [normalize_business(r) for r in records]
            inside = filter_by_radius(normalized, lat, lng, radius)
            unique = dedupe(inside)
            kept, removed = apply_exclusions(unique, search["exclusions"])
            yield "status", {"message": (
                f"{len(records)} collected, {len(inside)} inside {radius} km, "
                f"{len(unique)} after duplicates. Exclusions: {summarize_removed(removed)}.")}

            # --- L..X: evaluate each lead ---
            total = 0
            for lead in kept:
                yield "status", {"message": f"Checking {lead['name']}..."}
                web = await check_website(lead, client)

                # A directory page (dialmia, justdial...) is not the official website.
                if web["state"] == "directory":
                    lead = {**lead, "website": None}

                web_ok = web["state"] == "checked" and not web["conflicts"] and web["name_match"]

                lead_sources = list(lead["sources"])
                if web_ok:
                    lead_sources.append({"name": "website", "url": web["url"]})
                lead = {**lead, "sources": lead_sources}

                # Email: keep the listing email (OSM) if present, else official website email.
                lead["email_source"] = None
                if lead.get("email"):
                    lead["email_source"] = next((s["url"] for s in lead_sources if s.get("url")), None)
                elif web_ok and web["emails"]:
                    lead["email"] = web["emails"][0]
                    lead["email_source"] = web["email_source"]

                status, rule = decide_status({
                    "closed": lead.get("closed", False),
                    "sources": [s["name"] for s in lead_sources],
                    "conflicts": list(web["conflicts"]) + lead.get("conflicts", []),
                })
                scored = score_lead(lead, radius, search["category"])
                lead["status"] = status
                lead["score"] = scored["score"]
                lead["reason"] = build_reason(lead, scored["breakdown"], search["category"])
                lead["last_verified"] = utc_now()[:10]
                lead["maps_url"] = maps_url_of(lead_sources)

                business_id = save_business(search_id, lead)
                save_evidence(business_id, _evidence_rows(lead))
                save_verification_event(business_id, None, status, rule)

                total += 1
                yield "lead", {k: lead.get(k) for k in (
                    "name", "category", "address", "distance_km", "lat", "lng", "phone",
                    "email", "email_source", "website", "status", "score", "last_verified",
                    "reason", "sources", "possible_duplicate", "maps_url")}

            set_search_status(search_id, "complete")
            yield "complete", {"total": total}
    except Exception:
        log.exception("search %s crashed", search_id)
        yield "error_event", {"message": "Something went wrong. Cards already shown are kept."}