"""Exporta el esquema OpenAPI de la aplicación a openapi.yaml en la raíz del repo.

Uso:
    python scripts/export_openapi.py

El archivo generado (openapi.yaml) debe commitearse junto a los cambios que
añadan o modifiquen endpoints HTTP.
"""
import sys
from pathlib import Path

# Asegurar que el raíz del repo está en sys.path para importar main.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # PyYAML — ya es dependencia del proyecto
from main import app

OUTPUT = ROOT / "openapi.yaml"

schema = app.openapi()
with OUTPUT.open("w", encoding="utf-8") as fh:
    yaml.dump(schema, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)

print(f"openapi.yaml actualizado → {OUTPUT}")
