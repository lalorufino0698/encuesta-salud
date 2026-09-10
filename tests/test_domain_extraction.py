import json
import subprocess
import sys
from types import SimpleNamespace

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from app.domain_extraction import aligned_table_rows, build_payload, extract_pdf
from app.domain_main import app


TEXT = "A : DESTINATARIO\nDE : SOLICITANTE\nGERENCIA DE DESARROLLO EDUCATIVO\nASUNTO : CREACION DE USUARIOS\nSolicito usuarios de DOMINIO, SGD y SIGA."
HEADER = ["N°", "APELLIDOS Y NOMBRES", "DNI", "USUARIO"]


def test_per_row_services_override_body():
    result = build_payload(TEXT, [(1, [HEADER,
        ["1", "APELLIDO UNO, NOMBRE", "01234567", "SGD (CON ACCESO TOTAL) Y SIGA"],
        ["2", "APELLIDO DOS, ANA\nMARIA", "00123456", "DOMINIO, SGD"],
        ["3", "APELLIDO TRES, LUIS", "12345678", "DOMINO"]])],
        {"GERENCIA DE DESARROLLO EDUCATIVO": "GDE"})
    assert len(result["usuarios"]) == 2
    assert len(result["excluidos"]) == 1
    user = result["usuarios"][0]
    assert user["nombres"] == "ANA MARIA"
    assert user["dni"] == "00123456"
    assert user["grupo_ad"] == "GDE"
    assert user["insert_simulado"]["ejecutado"] is False
    assert not result["requiere_revision"]


def test_no_service_column_uses_document_and_preserves_ambiguous_name():
    result = build_payload(TEXT, [(1, [["APELLIDOS Y NOMBRES", "DNI", "E – MAIL"],
        ["CALLE ESCALANTE\nDIONE VERENESSE", "71956572", "prueba@example.test"]])])
    user = result["usuarios"][0]
    assert user["nombres"] is None
    assert user["apellidos"] is None
    assert user["dominio_explicito"]
    assert user["grupo_ad"] is None
    assert user["estado"] == "pendiente_revision"
    assert user["email"] == "prueba@example.test"


def test_access_alone_and_missing_metadata_require_review():
    result = build_payload("ASUNTO: ACCESO", [(1, [HEADER, ["1", "PEREZ, ANA", "12345678", "ACCESO"]])])
    assert result["requiere_revision"]
    assert result["usuarios"][0]["dominio_explicito"] is False
    assert result["usuarios"][0]["area"] is None


def test_no_recognized_rows_is_not_success():
    assert build_payload(TEXT, [])["requiere_revision"]


def test_invalid_dni_duplicate_and_ocr():
    result = build_payload(TEXT, [(1, [HEADER,
        ["1", "PEREZ, ANA", "12", "DOMINIO"],
        ["2", "PEREZ, ANA", "12", "DOMINIO"]])], ocr=True)
    assert any("repetida" in s for s in result["usuarios"][1]["observaciones"])
    assert any("OCR" in s for s in result["usuarios"][0]["observaciones"])


def make_pdf():
    # In-memory integration fixture, not a reproduction of the supplied images.
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), TEXT, fontsize=10)
    xs, ys = [40, 65, 285, 365, 550], [160, 190, 225, 260]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    rows = [HEADER, ["1", "PEREZ RAMOS, ANA", "00123456", "DOMINIO"],
            ["2", "LOPEZ SOLIS, JUAN", "12345678", "SIGA"]]
    for y, row in zip(ys, rows):
        for x, value in zip(xs, row):
            page.insert_text((x + 3, y + 17), value, fontsize=8)
    data = doc.tobytes()
    doc.close()
    return data


def test_real_pdf_extraction():
    result = extract_pdf(make_pdf(), "prueba.pdf", {"GERENCIA DE DESARROLLO EDUCATIVO": "GDE"})
    assert len(result["usuarios"]) == 1
    assert len(result["excluidos"]) == 1
    assert result["usuarios"][0]["nombres"] == "ANA"
    assert result["solicitud"]["area"] == "GERENCIA DE DESARROLLO EDUCATIVO"


def test_upload_returns_json_without_database(monkeypatch):
    monkeypatch.delenv("DOMAIN_GROUPS_FILE", raising=False)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        response = client.post("/api/simular", files={"file": ("prueba.pdf", make_pdf(), "application/pdf")})
        assert response.status_code == 200
        result = json.loads(response.content)
        assert result["conexion_ad"] is False
        assert result["escritura_bd"] is False
        assert len(result["usuarios"]) == 1
        assert client.post("/api/simular", files={"file": ("x.pdf", b"invalid")}).status_code == 400


def test_invalid_and_encrypted_pdf():
    with pytest.raises(ValueError, match="válido"):
        extract_pdf(b"bad")
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    doc.close()
    with pytest.raises(ValueError, match="contraseña"):
        extract_pdf(data)


def test_cli_writes_json(tmp_path):
    source = tmp_path / "solicitud.pdf"
    destination = tmp_path / "resultado.json"
    source.write_bytes(make_pdf())
    completed = subprocess.run(
        [sys.executable, "simulate_domain.py", str(source), "--output", str(destination)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(destination.read_text(encoding="utf-8"))
    assert result["usuarios"][0]["dni"] == "00123456"
    assert result["usuarios"][0]["insert_simulado"]["ejecutado"] is False


def test_header_subcolumns_align_merged_cells_without_shifting_blanks():
    header = ["", "N°", "", "", "APELLIDOS Y NOMBRES", "", "", "DNI", "", "", "USUARIO", ""]
    body = ["1", None, None, "PEREZ RAMOS, ANA\nMARIA", None, None,
            "00123456", None, None, "DOMINIO Y SGD", None, None]
    blank_dni = ["2", None, None, "LOPEZ, LUIS", None, None,
                 "", None, None, "DOMINIO", None, None]
    def body_cells(y):
        return [(0, y, 30, y + 20), None, None, (30, y, 60, y + 20), None, None,
                (60, y, 90, y + 20), None, None, (90, y, 120, y + 20), None, None]
    table = SimpleNamespace(
        extract=lambda: [header, body, blank_dni],
        rows=[SimpleNamespace(cells=[(i * 10, 0, (i + 1) * 10, 20) for i in range(12)]),
              SimpleNamespace(cells=body_cells(20)), SimpleNamespace(cells=body_cells(40))],
    )
    aligned = aligned_table_rows(table)
    assert aligned[1] == ["1", "PEREZ RAMOS, ANA\nMARIA", "00123456", "DOMINIO Y SGD"]
    assert aligned[2] == ["2", "LOPEZ, LUIS", "", "DOMINIO"]
    result = build_payload(TEXT, [(1, aligned)])
    assert len(result["usuarios"]) == 2
    assert result["usuarios"][0]["nombres"] == "ANA MARIA"
    assert result["usuarios"][1]["dni"] == ""


@pytest.mark.parametrize("format_name", ["png", "jpeg"])
def test_screenshot_conversion_preserves_source(monkeypatch, format_name):
    import hashlib
    from app import domain_extraction

    with fitz.open(stream=make_pdf(), filetype="pdf") as doc:
        data = doc[0].get_pixmap().tobytes(format_name)
    def fake_extract(pdf, source, groups):
        with fitz.open(stream=pdf, filetype="pdf") as converted:
            assert len(converted) == 1
            assert converted[0].get_images()
        return {"archivo": source, "sha256": "converted", "metodo": "ocr"}
    monkeypatch.setattr(domain_extraction, "extract_pdf", fake_extract)
    result = domain_extraction.extract_document(data, "captura." + format_name)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["formato_origen"] == "imagen"
    assert result["archivo"] == "captura." + format_name


def test_screenshot_reports_missing_ocr(monkeypatch):
    with fitz.open(stream=make_pdf(), filetype="pdf") as doc:
        data = doc[0].get_pixmap().tobytes("png")
    def unavailable(*args, **kwargs):
        raise RuntimeError("OCR unavailable")
    monkeypatch.setattr(fitz.Pixmap, "pdfocr_tobytes", unavailable)
    with TestClient(app) as client:
        response = client.post("/api/simular", files={"file": ("captura.png", data, "image/png")})
    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


@pytest.mark.parametrize("separator", [" | ", "\t", "   "])
def test_plain_text_endpoint(separator, monkeypatch):
    monkeypatch.delenv("DOMAIN_GROUPS_FILE", raising=False)
    text = TEXT + "\n" + separator.join(["APELLIDOS Y NOMBRES", "DNI", "USUARIO"])
    text += "\n" + separator.join(["PEREZ RAMOS, ANA MARIA", "00123456", "DOMINIO"])
    text += "\n" + separator.join(["LOPEZ, LUIS", "12345678", "SIGA"])
    with TestClient(app) as client:
        response = client.post("/api/simular-texto", json={"texto": text})
    assert response.status_code == 200
    result = response.json()
    assert result["metodo"] == "texto_plano"
    assert len(result["usuarios"]) == 1
    assert len(result["excluidos"]) == 1
    assert result["usuarios"][0]["dni"] == "00123456"


def test_empty_or_unstructured_text(monkeypatch):
    monkeypatch.delenv("DOMAIN_GROUPS_FILE", raising=False)
    with TestClient(app) as client:
        assert client.post("/api/simular-texto", json={"texto": "  "}).status_code == 422
        result = client.post("/api/simular-texto", json={"texto": "solicitud sin tabla"}).json()
    assert result["requiere_revision"]
    assert not result["usuarios"]


def test_bordered_image_ocr_reads_cells():
    from pathlib import Path
    from app.domain_image import image_tables
    from app.domain_extraction import parse_tables

    model = Path("data/tessdata/spa.traineddata")
    if not model.exists():
        pytest.skip("Requires local Spanish OCR model")
    with fitz.open(stream=make_pdf(), filetype="pdf") as doc:
        tables = image_tables(doc[0].get_pixmap(dpi=200), str(model.parent))
    people, warnings = parse_tables([(1, table) for table in tables])
    assert not warnings
    assert len(people) == 2
    assert people[0]["dni"] == "00123456"
    assert "ANA" in people[0]["nombre_completo_original"]


@pytest.mark.parametrize("services", [["dominio"], ["sgd"], ["dominio", "sgd"]])
def test_whatsapp_selection_and_duplicate(services):
    from app.domain_extraction import extract_plain_text
    text = "40461585\nFIDEL CENTENO UTANI\nFCENTENO\n[14:45, 7/9/2026] Martin Gore Perales: 40461585\nFIDEL CENTENO UTANI\nFCENTENO\n[14:45, 7/9/2026] Martin Gore Perales: solo dominio x ahora"
    result = extract_plain_text(text, services=services)
    assert len(result["usuarios"]) == 1
    user = result["usuarios"][0]
    assert user["usuario_propuesto"] == "FCENTENO"
    assert user["dni"] == "40461585"
    assert user["nombre_completo_original"] == "FIDEL CENTENO UTANI"
    assert user["nombres"] is None
    assert user["servicios_a_crear"] == services
    assert [i["servicio"] for i in user["inserts_simulados"]] == services
    assert all(i["ejecutado"] is False for i in user["inserts_simulados"])
    assert "insert_simulado" not in user


def test_whatsapp_requires_valid_selection():
    text = "40461585\nFIDEL CENTENO UTANI\nFCENTENO"
    with TestClient(app) as client:
        for services in [[], ["siga"]]:
            assert client.post("/api/simular-texto", json={"texto": text, "servicios": services}).status_code == 422
        assert client.post("/api/simular-texto", json={"texto": text}).status_code == 422


def test_whatsapp_fourth_line_area_per_person():
    from app.domain_extraction import extract_plain_text
    text = "40461585\nFIDEL CENTENO UTANI\nFCENTENO\nlogística\n12345678\nPEREZ, ANA\nAPEREZ\nÁrea: Tesoreria"
    result = extract_plain_text(text, groups={"LOGISTICA": "GRP_LOG", "TESORERIA": "GRP_TES"}, services=["dominio", "sgd"])
    first, second = result["usuarios"]
    assert first["area"] == "logística"
    assert first["grupo_ad"] == "GRP_LOG"
    assert second["area"] == "Tesoreria"
    assert second["grupo_ad"] == "GRP_TES"
    assert all(i["datos"]["department"] == "logística" for i in first["inserts_simulados"])
    assert not any("determinar el área" in warning for warning in first["observaciones"])


@pytest.mark.parametrize("last_line", ["solo dominio x ahora", "12345678", "SGD", "gracias"])
def test_whatsapp_does_not_use_service_or_next_dni_as_area(last_line):
    from app.domain_extraction import extract_plain_text
    result = extract_plain_text("40461585\nFIDEL CENTENO UTANI\nFCENTENO\n" + last_line, services=["dominio"])
    assert result["usuarios"][0]["area"] is None
