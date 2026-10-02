"""Extract memorandum requests into a local, reviewable AD simulation."""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFD", clean(value).upper())
                   if unicodedata.category(c) != "Mn")


def domain_requested(value):
    return bool(re.search(r"\b(?:DOMINIO|DOMINO)\b", normalized(value)))


def metadata(text):
    # Labels can be separate lines in the PDF reading order.
    match = re.search(r"(?mi)^\s*DE\s*:?[ \t]*(.*?)^\s*ASUNTO\s*:?[ \t]*", text, re.S)
    sender, area = None, None
    if match:
        lines = [clean(line).strip(": ") for line in match.group(1).splitlines()]
        lines = [line for line in lines if line]
        if lines:
            sender = lines[0]
            area = clean(" ".join(lines[1:])) or None
    subject = re.search(r"(?mi)^\s*ASUNTO\s*:?[ \t]*(.*)", text)
    return {"solicitante": sender, "area": area,
            "asunto_primera_linea": clean(subject.group(1)) if subject else None}


def aligned_table_rows(table):
    """Map merged body cells to visible header columns using PDF coordinates.

    Some PDFs introduce extra edges inside the header. Their body cells span
    several detector columns, so text and header indexes no longer coincide.
    Keep empty cells in place rather than compacting each row independently.
    """
    rows = table.extract() or []
    header_index = next((i for i, row in enumerate(rows) if any(
        "APELLIDOS" in normalized(str(c)) and "NOMBRES" in normalized(str(c))
        for c in row)), None)
    if header_index is None:
        return rows
    header_cells = table.rows[header_index].cells
    columns = [(clean(str(value)), (cell[0] + cell[2]) / 2)
               for value, cell in zip(rows[header_index], header_cells)
               if clean(str(value)) and cell is not None]
    aligned: list[list[str]] = [[label for label, _ in columns]]
    for row, geometry in zip(rows[header_index + 1:], table.rows[header_index + 1:]):
        aligned.append([
            next((str(value) for value, cell in zip(row, geometry.cells)
                  if cell is not None and cell[0] <= center < cell[2]), None)
            for _, center in columns
        ])
    return aligned


def parse_tables(tables):
    people = []
    warnings = []
    for page, rows in tables:
        header = None
        for row in rows:
            cells = [clean(c) for c in row]
            keys = [normalized(c) for c in cells]
            if any("APELLIDOS" in c and "NOMBRES" in c for c in keys):
                header = keys
                continue
            if header is None or not any(cells):
                continue
            def column(predicate):
                index = next((i for i, key in enumerate(header) if predicate(key)), None)
                return cells[index] if index is not None and index < len(cells) else None
            name = column(lambda k: "APELLIDOS" in k and "NOMBRES" in k)
            dni = column(lambda k: k == "DNI")
            if not name and not dni:
                continue
            people.append({"nombre_completo_original": name, "dni": dni,
                           "area_declarada": column(lambda k: k == "AREA"),
                           "servicios_solicitados": column(lambda k: k in ("USUARIO", "USUARIOS", "ACCESO", "ACCESOS")),
                           "tiene_columna_servicios": any(k in ("USUARIO", "USUARIOS", "ACCESO", "ACCESOS") for k in header),
                           "email": column(lambda k: k in ("E-MAIL", "E – MAIL", "E –MAIL", "EMAIL", "CORREO", "E – MAIL" ) or "MAIL" in k),
                           "telefono": column(lambda k: "TELEFONO" in k), "pagina": page})
    if not people:
        warnings.append("No se reconocieron filas de usuarios. Revise la tabla del documento y la legibilidad del texto.")
    return people, warnings


def build_payload(text, tables, groups=None, source="documento.pdf", digest=None, ocr=False, services=None):
    meta = metadata(text)
    people, warnings = parse_tables(tables)
    group_map = {normalized(k): v for k, v in (groups or {}).items()}
    group = group_map.get(normalized(meta["area"]))
    users, excluded = [], []
    seen = set()
    for person in people:
        area = person.pop("area_declarada", None) or meta["area"]
        group = group_map.get(normalized(area))
        scope = person["servicios_solicitados"] if person.pop("tiene_columna_servicios") else text
        requested = domain_requested(scope)
        uncertain = not requested and (not clean(scope) or (
            bool(re.search(r"\bACCESO\b", normalized(scope)))
            and not re.search(r"\b(?:SGD|SIGA|SIAF)\b", normalized(scope))))
        if not requested and not uncertain and services is None:
            excluded.append({**person, "motivo": "La fila no solicita dominio."})
            continue
        issues = []
        name = person["nombre_completo_original"] or ""
        surname, first = None, None
        if name.count(",") == 1:
            surname, first = [clean(part) or None for part in name.split(",", 1)]
        if not surname or not first:
            issues.append("Confirmar separación de apellidos y nombres: falta una coma inequívoca.")
        if not area:
            issues.append("No se pudo determinar el área debajo de DE.")
        if not isinstance(group, str) or not group.strip():
            group = None
            issues.append("Falta configurar el grupo AD correspondiente al área.")
        if not requested and services is None:
            issues.append("Confirmar si ACCESO o el servicio no especificado corresponde a dominio.")
        if not re.fullmatch(r"\d{8}", person["dni"] or ""):
            issues.append("DNI ausente o inválido; revisar sin corregir automáticamente.")
        if ocr:
            issues.append("Datos leídos mediante OCR: verificar contra el documento.")
        if person["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", person["email"]):
            issues.append("Correo con formato inválido: verificar contra el documento sin completar caracteres automáticamente.")
        key = person["dni"] or normalized(name)
        if key in seen:
            issues.append("Identidad repetida en el documento; comprobar duplicado.")
        seen.add(key)
        users.append({**person, "apellidos": surname, "nombres": first,
                      "area": area, "grupo_ad": group,
                      "dominio_explicito": requested,
                      "estado": "pendiente_revision" if issues else "listo_para_simulacion",
                      "observaciones": issues,
                      "insert_simulado": {"operacion": "INSERT", "destino": "usuarios_active_directory",
                                           "ejecutado": False,
                                           "datos": {"givenName": first, "sn": surname,
                                                     "displayName": clean(f"{first} {surname}") if first and surname else name,
                                                     "department": area, "grupo": group,
                                                     "dni": person["dni"]}}})
    if not users and people:
        warnings.append("No se identificaron usuarios con solicitud de dominio o acceso pendiente de revisión.")
    return {"version": 1, "modo": "simulacion", "escritura_bd": False, "conexion_ad": False,
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "archivo": source, "sha256": digest, "metodo": "ocr" if ocr else "texto_pdf",
            "solicitud": meta, "usuarios": users, "excluidos": excluded,
            "advertencias": warnings,
            "requiere_revision": bool(warnings or any(u["observaciones"] for u in users))}


def extract_plain_text(text, groups=None, services=None):
    """Read a pasted table with explicit column separators, without guessing."""
    if not text.strip():
        raise ValueError("Pegue el texto de la solicitud.")
    if services is not None and (not services or any(s not in ("dominio", "sgd") for s in services)):
        raise ValueError("Seleccione al menos un servicio: Dominio o SGD.")
    rows = []
    separator = None
    for line in text.splitlines():
        key = normalized(line)
        if "APELLIDOS" in key and "NOMBRES" in key:
            separator = r"\s*\|\s*" if "|" in line else r"\t+" if "\t" in line else r" {2,}"
        if separator and line.strip():
            cells = [clean(c) for c in re.split(separator, line.strip().strip("|"))]
            if len(cells) > 1:
                rows.append(cells)
    accounts = {}
    if not rows:
        # Strip WhatsApp envelope only; the sender is not the account owner.
        lines = [clean(re.sub(r"^\s*\[[^\]]+\]\s*[^:]+:\s*", "", line)) for line in text.splitlines()]
        lines = [line for line in lines if line]
        rows = [["APELLIDOS Y NOMBRES", "DNI", "AREA"]]
        seen = set()
        for i, line in enumerate(lines):
            if not re.fullmatch(r"\d{8}", line) or i + 1 >= len(lines):
                continue
            name = lines[i + 1]
            if len(name.split()) < 2 or any(c.isdigit() for c in name) or ":" in name:
                continue
            account = lines[i + 2] if i + 2 < len(lines) and re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{1,63}", lines[i + 2]) else None
            area = None
            if account and i + 3 < len(lines):
                candidate = re.sub(r"(?i)^área\s*:\s*|^area\s*:\s*", "", lines[i + 3]).strip()
                if (candidate and not any(c.isdigit() for c in candidate)
                        and ":" not in candidate
                        and not re.search(r"\b(DOMINIO|DOMINO|SGD|SIGA|SIAF|SOLO|AHORA|GRACIAS|CREAR|ACCESO)\b", normalized(candidate))):
                    area = candidate
            identity = (line, normalized(name), account, normalized(area))
            if identity in seen:
                continue
            seen.add(identity)
            rows.append([name, line, area or ""])
            accounts[(line, name)] = account
        if len(rows) > 1 and services is None:
            raise ValueError("Para un mensaje de WhatsApp seleccione Dominio, SGD o ambos.")
    result = build_payload(text, [(1, rows)], groups, "texto-pegado.txt",
                           hashlib.sha256(text.encode("utf-8")).hexdigest(), services=services)
    if services is not None:
        selected = list(dict.fromkeys(services))
        result["servicios_seleccionados"] = selected
        result["origen_servicios"] = "seleccion_manual"
        for user in result["usuarios"]:
            user["usuario_propuesto"] = accounts.get((user["dni"], user["nombre_completo_original"]))
            user["servicios_a_crear"] = selected
            base = user.pop("insert_simulado")["datos"]
            base["usuario"] = user["usuario_propuesto"]
            user["inserts_simulados"] = [
                {"operacion": "INSERT", "servicio": service,
                 "destino": "usuarios_active_directory" if service == "dominio" else "usuarios_sgd",
                 "ejecutado": False, "datos": dict(base)} for service in selected]
    result["metodo"] = "texto_plano"
    result["formato_origen"] = "texto"
    if not result["usuarios"] and not result["excluidos"]:
        result["advertencias"].append("Use una fila por persona y columnas separadas por |, tabulaciones o dos o más espacios, con encabezado APELLIDOS Y NOMBRES.")
    return result


def extract_document(data: bytes, source="documento.pdf", groups=None):
    """Accept PDF or PNG/JPEG screenshots, preserving original provenance."""
    if data.startswith(b"%PDF-"):
        return extract_pdf(data, source, groups)
    if not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")):
        raise ValueError("Seleccione un PDF o una captura PNG/JPG válida.")
    import pymupdf as fitz

    try:
        with fitz.open(stream=data, filetype="png" if data.startswith(b"\x89PNG") else "jpeg") as image:
            if image[0].rect.width * image[0].rect.height > 25_000_000:
                raise ValueError("La imagen es demasiado grande; reduzca su resolución.")
            pdf_data = image.convert_to_pdf()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("No se pudo leer la imagen. Verifique que no esté dañada.") from exc
    result = extract_pdf(pdf_data, source, groups)
    result["sha256"] = hashlib.sha256(data).hexdigest()
    result["formato_origen"] = "imagen"
    return result


def extract_pdf(data: bytes, source="documento.pdf", groups=None):
    import pymupdf as fitz

    texts, tables = [], []
    used_ocr = False
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("No se pudo abrir el PDF. Verifique que sea válido.") from exc
    with document:
        if document.needs_pass:
            raise ValueError("El PDF está protegido con contraseña.")
        if len(document) > 50:
            raise ValueError("La prueba admite como máximo 50 páginas por PDF.")
        for number, original_page in enumerate(document, 1):
            page = original_page
            ocr_document = None
            raster_tables = []
            try:
                if len(clean(page.get_text())) < 30:
                    used_ocr = True
                    try:
                        raster = page.get_pixmap(dpi=200)
                        local_data = Path(__file__).resolve().parent.parent / "data" / "tessdata"
                        tessdata = os.environ.get("TESSDATA_PREFIX")
                        if not tessdata and (local_data / "spa.traineddata").is_file():
                            tessdata = str(local_data)
                        ocr_document = fitz.open("pdf", raster.pdfocr_tobytes(language="spa", tessdata=tessdata))
                        page = ocr_document[0]
                    except Exception as exc:
                        raise ValueError(f"La imagen o PDF escaneado requiere OCR: configure Tesseract con idioma español y TESSDATA_PREFIX. Detalle: {str(exc)}") from exc
                    from app.domain_image import image_tables
                    raster_tables = image_tables(raster, tessdata)
                texts.append(page.get_text(sort=True))
                found = page.find_tables()
                extracted = [aligned_table_rows(table) for table in found.tables]
                if not extracted or not any("APELLIDOS" in normalized(str(t)) for t in extracted):
                    extracted = [aligned_table_rows(table) for table in page.find_tables(strategy="text").tables]
                if any(parse_tables([(number, rows)])[0] for rows in raster_tables):
                    extracted = raster_tables
                tables.extend((number, rows) for rows in extracted)
            finally:
                if ocr_document:
                    ocr_document.close()
    return build_payload("\n".join(texts), tables, groups, Path(source).name,
                         hashlib.sha256(data).hexdigest(), used_ocr)
