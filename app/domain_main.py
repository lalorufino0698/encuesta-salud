"""Standalone PDF simulation server. Does not import the database application."""
import json
import os
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.concurrency import run_in_threadpool         
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.domain_extraction import extract_document, extract_plain_text
from simulate_domain import load_groups
from app import ad_registration
from app import sgd_registration
from app.dni_lookup import fetch_dni_data
from pydantic import ValidationError

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
    return FileResponse(Path(__file__).parent / "static" / "domain.html", headers={'Cache-Control': 'no-store'})


@app.get('/directorio')
def directory_page():
    return FileResponse(Path(__file__).parent / 'static' / 'directory.html')


@app.get('/historial')
def history_page():
    return FileResponse(Path(__file__).parent / 'static' / 'history.html', headers={'Cache-Control': 'no-store'})


@app.get('/registro-ad.js')
def registration_script():
    return FileResponse(Path(__file__).parent / 'static' / 'registration.js', media_type='text/javascript', headers={'Cache-Control': 'no-store'})


@app.get('/styles.css')
def styles():
    return FileResponse(Path(__file__).parent / 'static' / 'styles.css', media_type='text/css', headers={'Cache-Control': 'no-store'})


@app.get('/favicon.ico')
def favicon():
    return FileResponse(Path(__file__).parent / 'static' / 'favicon.ico', media_type='image/x-icon', headers={'Cache-Control': 'max-age=86400'})


@app.get('/ui.js')
def ui_script():
    return FileResponse(Path(__file__).parent / 'static' / 'ui.js', media_type='text/javascript', headers={'Cache-Control': 'no-store'})


def check_registration_access(request):
    if request.headers.get('X-AD-Review') != '1':
        raise HTTPException(403, 'Inicia el registro desde la pantalla de revision.')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Origen no permitido.')


@app.get('/api/registro-ad/catalogo')
def registration_catalog(request: Request):
    check_registration_access(request)
    try:
        data = ad_registration.registration_directory()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(json.dumps(data, ensure_ascii=False), media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.post('/api/registro-ad/{action}')
async def registration_action(action: str, request: Request):
    check_registration_access(request)
    if action not in ('comprobar', 'crear', 'crear-generado', 'automatico'):
        raise HTTPException(404)
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'Se requiere JSON.')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 16384:
            raise HTTPException(413, 'Solicitud demasiado grande.')
    try:
        model = {'comprobar': ad_registration.AccountDraft, 'crear': ad_registration.Confirmation,
                 'crear-generado': ad_registration.GeneratedConfirmation, 'automatico': ad_registration.AutomaticAccount}[action]
        data = model.model_validate_json(body)
        fn = {'comprobar': ad_registration.prepare, 'crear': ad_registration.create,
              'crear-generado': ad_registration.start_generated, 'automatico': ad_registration.start_automatic}[action]
        result = await run_in_threadpool(fn, data)
    except ValidationError:
        # Do not echo submitted values: the create request includes a password.
        raise HTTPException(422, 'Revisa los campos obligatorios y el formato del usuario (maximo 20 caracteres).')
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(json.dumps(result, ensure_ascii=False), media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.post('/api/dni')
async def dni_lookup(request: Request):
    try:
        body = await request.json()
        dni = body.get('dni', '')
        result = await run_in_threadpool(fetch_dni_data, dni)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, 'No se pudo consultar el DNI en los servicios externos.') from exc
    return Response(json.dumps(result, ensure_ascii=False), media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/api/registro-ad/progreso/{job_id}')
def registration_progress(job_id: str, request: Request):
    check_registration_access(request)
    try:
        result = ad_registration.job_status(job_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(json.dumps(result, ensure_ascii=False), media_type='application/json',
                    headers={'Cache-Control': 'no-store'})


@app.get('/api/directorio')
def directory_list(request: Request):
    try:
        data = ad_registration.registration_directory()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(json.dumps(data, ensure_ascii=False), media_type='application/json',
                    headers={'Cache-Control': 'no-store'})


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


class CiudadanoValidation(BaseModel):
    dni: str = Field(pattern=r'^[0-9]{8}$')


@app.post('/api/sgd/validar-ciudadano')
def validate_sgd(data: CiudadanoValidation, request: Request):
    check_registration_access(request)
    events = []
    try:
        result = sgd_registration.validate_ciudadano(data.dni, events.append)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(json.dumps(dict(result, events=events), ensure_ascii=False),
                    media_type='application/json', headers={'Cache-Control': 'no-store'})
