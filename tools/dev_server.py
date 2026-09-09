#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================================================
 SERVIDOR LOCAL DE LA DEMO  |  W-IT  |  Legrand + Teknica
=========================================================================

 Sirve el sitio estatico y expone la MISMA API que Azure Static Web Apps,
 en el mismo origen (sin CORS). No duplica logica: importa api/lead_core.py,
 exactamente el mismo modulo que usan las Azure Functions.

   POST /api/leads      -> crea el lead
   GET  /api/leads      -> leads capturados (alimenta admin.html)
   GET  /api/clientes   -> clientes con ordenes de trabajo
   GET  /api/workorders -> ordenes de trabajo filtradas (Field Service)
   GET  /api/health     -> modo y configuracion visible
   GET  /api/landings   -> catalogo de origenes
   GET  /*              -> sitio estatico

 Ejecucion:  py tools/dev_server.py     (o doble clic en run-demo.cmd)
 Requisitos: solo Python 3.8+ (biblioteca estandar, sin pip install).
"""

import json
import os
import sys
import urllib.parse
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "api"))

import lead_core  # noqa: E402
import workorders_core  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    server_version = "WIT-DemoServer/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # ---- helpers de respuesta
    def _cors(self):
        # En Static Web Apps el sitio y la API comparten origen y esto no hace
        # falta. Aqui se deja abierto para poder probar una landing servida
        # desde otro puerto o desde el CMS del cliente.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s  %s\n" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    # ---- verbos
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        route = urllib.parse.urlparse(self.path).path
        if route == "/api/health":
            return self._json(200, lead_core.health())
        if route == "/api/landings":
            try:
                return self._json(200, lead_core.load_landings()[0])
            except (OSError, ValueError) as err:
                return self._json(500, {"ok": False, "error": "No se pudo leer el catalogo",
                                        "details": [str(err)]})
        if route == "/api/leads":
            return self._json(200, lead_core.list_leads())
        if route == "/api/clientes":
            return self._json(*workorders_core.listar_clientes())
        if route == "/api/workorders":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            filtros = {k: (q.get(k) or [""])[0] for k in ("cliente", "desde", "hasta", "estado", "top")}
            return self._json(*workorders_core.listar_ordenes(filtros))
        if route.startswith("/api/"):
            return self._json(404, {"ok": False, "error": "Ruta no encontrada: " + route})
        if route == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        route = urllib.parse.urlparse(self.path).path
        if route != "/api/leads":
            return self._json(404, {"ok": False, "error": "Ruta no encontrada: " + route})

        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 200000:
                return self._json(400, {"ok": False, "error": "Cuerpo vacio o demasiado grande."})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as err:
            return self._json(400, {"ok": False, "error": "JSON invalido", "details": [str(err)]})

        status, body = lead_core.create_lead(payload)
        return self._json(status, body)


def main():
    config = lead_core.get_config()
    port = config["port"]
    try:
        codes = sorted(lead_core.load_landings()[1].keys())
    except (OSError, ValueError) as err:
        print("ERROR: no se pudo leer el catalogo de landings -> %s" % err)
        return 1

    print("")
    print("=" * 66)
    print(" DEMO LEGRAND + TEKNICA  |  W-IT  |  sitio + API unica de leads")
    print("=" * 66)
    print(" Sitio      : http://localhost:%d/" % port)
    print(" Endpoint   : POST http://localhost:%d/api/leads" % port)
    print(" Salud      : GET  http://localhost:%d/api/health" % port)
    print(" Consola    : http://localhost:%d/admin.html" % port)
    print(" Modo       : %s" % config["mode"].upper())
    if config["mode"] == "dataverse":
        print(" Entorno D365: %s" % (config["dv_url"] or "(sin configurar)"))
    else:
        print(" Entorno D365: no se escribe en CRM (leads en api/_data/leads.json)")
    print(" Landings   : %s" % ", ".join(codes))
    print("-" * 66)
    print(" Ctrl+C para detener")
    print("")

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Servidor detenido.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
