# -*- coding: utf-8 -*-
"""Endpoint unico de captura de leads: GET lista, POST crea.

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
    if req.method == "GET":
        return _json(200, lead_core.list_leads())

    try:
        payload = req.get_json()
    except ValueError as err:
        return _json(400, {"ok": False, "error": "JSON invalido", "details": [str(err)]})

    try:
        status, body = lead_core.create_lead(payload)
    except Exception as err:  # el envio no se pierde por un error inesperado
        logging.exception("Error no controlado al crear el lead")
        return _json(500, {"ok": False, "error": "Error interno de la API",
                           "details": [str(err)]})

    logging.info("Lead %s | landing %s | modo %s",
                 body.get("leadId"), payload.get("landingCode"), body.get("mode"))
    return _json(status, body)
