"""Thin API layer. Logic lives in pipeline.py."""
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from app.db import init_db, list_searches, load_leads, save_search

from app import pipeline
from app.db import init_db, load_leads, save_search
from app.output.export import leads_to_csv
from app.schemas import AreaChoice, SearchIn


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="BLD Agent", lifespan=lifespan)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/searches")
def create_search(data: SearchIn):
    search_id = uuid.uuid4().hex[:8]
    save_search(search_id, data.model_dump())
    pipeline.register(search_id)
    return {"search_id": search_id}


@app.post("/api/searches/{search_id}/area")
def choose_area(search_id: str, body: AreaChoice):
    if not pipeline.provide_choice(search_id, body.choice_id):
        raise HTTPException(status_code=404, detail="Search not found")
    return {"ok": True}


@app.get("/api/searches/{search_id}/stream")
async def stream(search_id: str):
    async def events():
        async for event, data in pipeline.run_search(search_id):
            yield sse(event, data)
    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/searches/{search_id}/export.csv")
def export_csv(search_id: str):
    text = leads_to_csv(load_leads(search_id))
    return Response(
        content="\ufeff" + text,  # BOM so Excel shows special characters correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="bld-leads-{search_id}.csv"'},
    )

@app.get("/api/searches")
def search_history():
    return list_searches()


@app.get("/api/searches/{search_id}/leads")
def search_leads(search_id: str):
    return load_leads(search_id)

# Serve the frontend. Keep this LAST.
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")