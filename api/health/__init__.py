# -*- coding: utf-8 -*-
"""Estado de la API: modo, entorno Dataverse y origenes registrados.

Azure Function (Static Web Apps). Toda la logica esta en api/lead_core.py,
compartida con el servidor local de la demo: aqui solo se traduce HTTP.
"""

import json
import logging
import os
import sys

import azure.functions as func

# La raiz de la Functions app no siempre queda en sys.path segun como se
# empaquete el despliegue: lo aseguramos antes de importar el nucleo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lead_core  # noqa: E402


def _json(status, body):
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False, indent=2),
        status_code=status,
        mimetype="application/json",
        charset="utf-8",
        headers={"Cache-Control": "no-store"},
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    return _json(200, lead_core.health())
