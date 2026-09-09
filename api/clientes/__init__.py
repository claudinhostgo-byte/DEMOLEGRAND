# -*- coding: utf-8 -*-
"""Clientes con ordenes de trabajo, para el selector de la consulta.

Azure Function (Static Web Apps). La logica esta en api/workorders_core.py,
compartida con el servidor local de la demo.
"""

import json
import logging
import os
import sys

import azure.functions as func

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import workorders_core  # noqa: E402


def _json(status, body):
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False, indent=2),
        status_code=status, mimetype="application/json", charset="utf-8",
        headers={"Cache-Control": "no-store"},
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        status, body = workorders_core.listar_clientes()
    except Exception as err:
        logging.exception("Error no controlado listando clientes")
        return _json(500, {"ok": False, "error": "Error interno de la API", "details": [str(err)]})
    return _json(status, body)
