"""Usage: python simulate_domain.py solicitud.pdf --groups config/grupos.json."""
import argparse
import json
from pathlib import Path

from app.domain_extraction import extract_document


def load_groups(path):
    if not path:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in value.items()):
        raise ValueError("El mapa de grupos debe ser un objeto JSON de área a nombre de grupo.")
    return value


def main():
    parser = argparse.ArgumentParser(description="PDF a JSON: simulación local de usuarios de dominio, sin BD ni AD.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--groups", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    destination = args.output or Path("data/domain") / (args.pdf.stem + ".json")
    try:
        if destination.resolve() == args.pdf.resolve():
            raise ValueError("La salida no puede sobrescribir el PDF de entrada.")
        result = extract_document(args.pdf.read_bytes(), args.pdf.name, load_groups(args.groups))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"JSON generado: {destination.resolve()}")
    print(f"Usuarios: {len(result['usuarios'])}; excluidos: {len(result['excluidos'])}; revisión: {result['requiere_revision']}")


if __name__ == "__main__":
    main()
