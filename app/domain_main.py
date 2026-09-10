"""Standalone PDF simulation server. Does not import the database application."""
import json
import os
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.domain_extraction import extract_document, extract_plain_text
from simulate_domain import load_groups

app = FastAPI(title="Simulación de usuarios de dominio")


class TextRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=100000)
    servicios: list[Literal["dominio", "sgd"]] | None = None


@app.post("/api/simular-texto")
def simulate_text(request: TextRequest):
    try:
        result = extract_plain_text(request.texto, load_groups(os.environ.get("DOMAIN_GROUPS_FILE")), request.servicios)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Cache-Control": "no-store"})


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "domain.html")


@app.post("/api/simular")
async def simulate(file: UploadFile = File(...)):
    data = await file.read(20 * 1024 * 1024 + 1)
    await file.close()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "El límite es 20 MB por archivo.")
    if not data.startswith((b"%PDF-", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
        raise HTTPException(400, "Seleccione un PDF o una captura PNG/JPG válida.")
    try:
        groups = load_groups(os.environ.get("DOMAIN_GROUPS_FILE"))
        result = await run_in_threadpool(extract_document, data, file.filename or "documento", groups)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Cache-Control": "no-store"})
