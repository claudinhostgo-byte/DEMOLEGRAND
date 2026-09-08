#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================================================
 API UNICA DE CAPTURA DE LEADS  ->  Dynamics 365 (entidad Lead / leads)
 W-IT  |  Demo de integracion de landings para Legrand + Teknica
=========================================================================

 Una sola API recibe los datos de TODAS las landings. Cada landing se
 identifica con su codigo (landingCode) y ese codigo:
   1) valida que el origen exista en landings.json,
   2) queda escrito en el lead (campana, equipo, descripcion trazable y,
      opcionalmente, columnas personalizadas de Dataverse).

 Endpoints
 ---------
   POST /api/leads      -> crea el lead (unico endpoint que usan las landings)
   GET  /api/health     -> estado, modo (mock/dataverse) y configuracion visible
   GET  /api/landings   -> catalogo de landings registradas
   GET  /api/leads      -> leads capturados en modo mock (alimenta admin.html)
   GET  /*              -> sirve el sitio estatico (mismo origen = sin CORS)

 Ejecucion
 ---------
   py api/lead_api.py            (o doble clic en run-demo.cmd)
   -> http://localhost:8080

 Requisitos: solo Python 3.8+ (biblioteca estandar, sin pip install).
"""

import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(ROOT, "api")
DATA_DIR = os.path.join(API_DIR, "_data")
MOCK_STORE = os.path.join(DATA_DIR, "leads.json")
LANDINGS_FILE = os.path.join(ROOT, "landings.json")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$")

# Limites de longitud de los campos estandar de la entidad Lead en Dataverse.
MAXLEN = {
    "subject": 300, "firstname": 50, "lastname": 50, "emailaddress1": 100,
    "mobilephone": 50, "telephone1": 50, "companyname": 100, "jobtitle": 100,
    "description": 100000,
}


# ---------------------------------------------------------------- configuracion
def load_env():
    """Carga api/.env (KEY=VALOR) sin dependencias externas. El archivo esta
    en .gitignore: las credenciales NUNCA se suben al repositorio."""
    path = os.path.join(API_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

CONFIG = {
    # mock = guarda en api/_data/leads.json | dataverse = escribe en Dynamics 365
    "mode": os.environ.get("LEAD_MODE", "mock").lower(),
    "dv_url": os.environ.get("DV_URL", "").rstrip("/"),
    "dv_tenant": os.environ.get("DV_TENANT_ID", ""),
    "dv_client_id": os.environ.get("DV_CLIENT_ID", ""),
    "dv_secret": os.environ.get("DV_CLIENT_SECRET", ""),
    "dv_api": os.environ.get("DV_API_VERSION", "v9.2"),
    # Columnas personalizadas OPCIONALES. Si el entorno las tiene creadas,
    # se declaran aqui y el codigo no cambia.
    "field_landing_code": os.environ.get("FIELD_LANDING_CODE", ""),
    "field_utm_source": os.environ.get("FIELD_UTM_SOURCE", ""),
    "field_utm_campaign": os.environ.get("FIELD_UTM_CAMPAIGN", ""),
    "port": int(os.environ.get("PORT", "8080")),
}

_token_cache = {"value": None, "expires_at": 0}


def load_landings():
    """El catalogo de landings es la fuente unica de verdad, compartida con el
    front-end. Se relee en cada request para poder agregar landings en vivo."""
    with open(LANDINGS_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    index = {item["code"]: item for item in data.get("landings", [])}
    return data, index


# ---------------------------------------------------------------- validacion
def clean(value, limit=None):
    text = "" if value is None else str(value).strip()
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text[:limit] if limit else text


def validate(payload, landing_index):
    """Devuelve (landing, errores). Valida obligatorios, formato y origen."""
    errors = []
    code = clean(payload.get("landingCode"))
    landing = landing_index.get(code)
    if not code:
        errors.append("landingCode es obligatorio.")
    elif not landing:
        errors.append("landingCode '%s' no esta registrado en landings.json." % code)

    for key, label in (("firstName", "el nombre"), ("lastName", "el apellido"),
                       ("email", "el correo"), ("company", "la empresa")):
        if not clean(payload.get(key)):
            errors.append("Falta %s." % label)

    email = clean(payload.get("email"))
    if email and not EMAIL_RE.match(email):
        errors.append("El correo '%s' no tiene formato valido." % email)

    phone_digits = re.sub(r"\D", "", clean(payload.get("phone")))
    if phone_digits and len(phone_digits) < 8:
        errors.append("El telefono debe tener al menos 8 digitos.")

    if not payload.get("consent"):
        errors.append("Se requiere el consentimiento de tratamiento de datos (Ley 21.719).")

    return landing, errors


# ---------------------------------------------------------------- mapeo a Lead
def build_description(payload, landing):
    """Bloque de trazabilidad que el vendedor ve dentro del lead en Dynamics."""
    tracking = payload.get("tracking") or {}
    fields = payload.get("fields") or {}
    labels = {f["key"]: f.get("label", f["key"]) for f in landing.get("extra_fields", [])}

    lines = []
    if clean(payload.get("message")):
        lines += ["MENSAJE DEL CONTACTO", clean(payload.get("message")), ""]

    lines += ["ORIGEN DEL LEAD",
              "  Landing        : %s (%s)" % (landing["name"], landing["code"]),
              "  Linea/marca    : %s" % landing.get("brand", "-"),
              "  Equipo asignado: %s" % landing.get("owner_team", "-"),
              "  Campana        : %s" % landing.get("campaign", "-"),
              "  URL            : %s" % clean(tracking.get("landingUrl"), 400),
              "  Referrer       : %s" % clean(tracking.get("referrer"), 400), ""]

    utms = [(k, v) for k, v in tracking.items()
            if k.startswith("utm_") or k in ("gclid", "fbclid", "msclkid", "src")]
    if utms:
        lines.append("PARAMETROS DE CAMPANA")
        lines += ["  %-15s: %s" % (k, clean(v, 200)) for k, v in sorted(utms)]
        lines.append("")

    if fields:
        lines.append("DATOS ESPECIFICOS DE LA LANDING")
        lines += ["  %-25s: %s" % (labels.get(k, k), clean(v, 400)) for k, v in fields.items()]
        lines.append("")

    lines += ["REGISTRO TECNICO",
              "  Recibido por   : API unica de captura W-IT",
              "  Fecha (UTC)    : %s" % datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "  Enviado desde  : %s" % clean((payload.get("client") or {}).get("submittedAt"))]
    return "\n".join(lines)


def build_lead(payload, landing, defaults):
    """Traduce el payload comun de cualquier landing a la entidad Lead."""
    tracking = payload.get("tracking") or {}
    company = clean(payload.get("company"), MAXLEN["companyname"])

    subject_tpl = defaults.get("subject_template", "[{code}] {interes} - {company}")
    subject = subject_tpl.format(code=landing["code"], interes=landing["name"], company=company or "Sin empresa")

    lead = {
        "subject": clean(subject, MAXLEN["subject"]),
        "firstname": clean(payload.get("firstName"), MAXLEN["firstname"]),
        "lastname": clean(payload.get("lastName"), MAXLEN["lastname"]),
        "emailaddress1": clean(payload.get("email"), MAXLEN["emailaddress1"]),
        "companyname": company,
        "jobtitle": clean(payload.get("jobTitle"), MAXLEN["jobtitle"]),
        "description": clean(build_description(payload, landing), MAXLEN["description"]),
        # 8 = Web en el conjunto de opciones estandar leadsourcecode.
        "leadsourcecode": int(landing.get("leadsourcecode", defaults.get("leadsourcecode", 8))),
    }

    phone = clean(payload.get("phone"), MAXLEN["mobilephone"])
    if phone:
        lead["mobilephone"] = phone
        lead["telephone1"] = phone

    # Columnas personalizadas opcionales (solo si estan configuradas en .env).
    if CONFIG["field_landing_code"]:
        lead[CONFIG["field_landing_code"]] = landing["code"]
    if CONFIG["field_utm_source"] and tracking.get("utm_source"):
        lead[CONFIG["field_utm_source"]] = clean(tracking["utm_source"], 100)
    if CONFIG["field_utm_campaign"] and tracking.get("utm_campaign"):
        lead[CONFIG["field_utm_campaign"]] = clean(tracking["utm_campaign"], 100)

    return lead


# ---------------------------------------------------------------- Dataverse
def get_token():
    """OAuth2 client_credentials contra Entra ID. El scope lleva la URL del
    entorno: es ahi donde se decide en que Dynamics caen los leads."""
    now = time.time()
    if _token_cache["value"] and _token_cache["expires_at"] - 120 > now:
        return _token_cache["value"]

    for key in ("dv_url", "dv_tenant", "dv_client_id", "dv_secret"):
        if not CONFIG[key]:
            raise RuntimeError("Falta configurar %s en api/.env" % key.upper())

    url = "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % CONFIG["dv_tenant"]
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CONFIG["dv_client_id"],
        "client_secret": CONFIG["dv_secret"],
        "scope": CONFIG["dv_url"] + "/.default",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode("utf-8"))

    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = now + int(data.get("expires_in", 3600))
    return _token_cache["value"]


def create_lead_dataverse(lead):
    """POST /api/data/v9.2/leads. Devuelve (leadid, url_del_registro)."""
    token = get_token()
    endpoint = "%s/api/data/%s/leads" % (CONFIG["dv_url"], CONFIG["dv_api"])
    body = json.dumps(lead, ensure_ascii=False).encode("utf-8")  # UTF-8 explicito por los acentos
    req = urllib.request.Request(endpoint, data=body, method="POST", headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Prefer": "return=representation",
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            created = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:900]
        raise RuntimeError("Dataverse respondio %s: %s" % (err.code, detail))

    lead_id = created.get("leadid")
    record_url = "%s/main.aspx?pagetype=entityrecord&etn=lead&id=%s" % (CONFIG["dv_url"], lead_id)
    return lead_id, record_url


# ---------------------------------------------------------------- modo mock
def save_mock(record):
    os.makedirs(DATA_DIR, exist_ok=True)
    existing = []
    if os.path.exists(MOCK_STORE):
        try:
            with open(MOCK_STORE, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
        except (ValueError, OSError):
            existing = []
    existing.insert(0, record)
    with open(MOCK_STORE, "w", encoding="utf-8") as fh:
        json.dump(existing[:500], fh, ensure_ascii=False, indent=2)


def read_mock():
    if not os.path.exists(MOCK_STORE):
        return []
    try:
        with open(MOCK_STORE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return []


# ---------------------------------------------------------------- HTTP
class Handler(SimpleHTTPRequestHandler):
    server_version = "WIT-LeadAPI/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # ---- helpers de respuesta
    def _cors(self):
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
        # Evita cache del sitio estatico durante la demo.
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
            return self._json(200, {
                "ok": True,
                "service": "API unica de captura de leads - W-IT",
                "mode": CONFIG["mode"],
                "dataverse": {
                    "configured": bool(CONFIG["dv_url"] and CONFIG["dv_client_id"]),
                    "url": CONFIG["dv_url"] or None,
                    "apiVersion": CONFIG["dv_api"],
                    "customFields": {k: v for k, v in CONFIG.items()
                                     if k.startswith("field_") and v},
                },
                "landings": sorted(load_landings()[1].keys()),
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
        if route == "/api/landings":
            return self._json(200, load_landings()[0])
        if route == "/api/leads":
            leads = read_mock()
            return self._json(200, {"ok": True, "mode": CONFIG["mode"],
                                    "count": len(leads), "leads": leads})
        if route.startswith("/api/"):
            return self._json(404, {"ok": False, "error": "Ruta no encontrada: " + route})
        if route == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        route = urllib.parse.urlparse(self.path).path
        if route != "/api/leads":
            return self._json(404, {"ok": False, "error": "Ruta no encontrada: " + route})

        # 1. Leer y parsear el cuerpo
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 200_000:
                return self._json(400, {"ok": False, "error": "Cuerpo vacio o demasiado grande."})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("se esperaba un objeto JSON")
        except (ValueError, UnicodeDecodeError) as err:
            return self._json(400, {"ok": False, "error": "JSON invalido", "details": [str(err)]})

        # 2. Validar contra el catalogo de landings
        try:
            catalog, index = load_landings()
        except (OSError, ValueError) as err:
            return self._json(500, {"ok": False, "error": "No se pudo leer landings.json",
                                    "details": [str(err)]})
        landing, errors = validate(payload, index)
        if errors:
            return self._json(400, {"ok": False, "error": "Validacion fallida", "details": errors})

        # 3. Mapear a la entidad Lead
        lead = build_lead(payload, landing, catalog.get("defaults", {}))

        # 4. Persistir: Dataverse o mock
        record = {
            "receivedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "landingCode": landing["code"],
            "landingName": landing["name"],
            "brand": landing.get("brand"),
            "ownerTeam": landing.get("owner_team"),
            "campaign": landing.get("campaign"),
            "contact": {
                "name": (lead["firstname"] + " " + lead["lastname"]).strip(),
                "email": lead["emailaddress1"],
                "phone": lead.get("mobilephone", ""),
                "company": lead["companyname"],
                "jobTitle": lead["jobtitle"],
            },
            "tracking": payload.get("tracking") or {},
            "fields": payload.get("fields") or {},
            "dataversePayload": lead,
        }

        if CONFIG["mode"] == "dataverse":
            try:
                lead_id, record_url = create_lead_dataverse(lead)
            except (RuntimeError, urllib.error.URLError, KeyError) as err:
                record.update({"leadId": None, "mode": "dataverse-error", "error": str(err)})
                save_mock(record)
                return self._json(502, {"ok": False, "error": "No se pudo crear el lead en Dynamics 365",
                                        "details": [str(err)], "landing": landing["code"]})
            record.update({"leadId": lead_id, "mode": "dataverse", "recordUrl": record_url})
            save_mock(record)
            return self._json(201, {
                "ok": True, "mode": "dataverse", "leadId": lead_id, "recordUrl": record_url,
                "landing": {"code": landing["code"], "name": landing["name"],
                            "brand": landing.get("brand"), "ownerTeam": landing.get("owner_team"),
                            "campaign": landing.get("campaign")},
                "dataversePayload": lead,
            })

        # Modo mock: misma respuesta, sin escribir en CRM.
        lead_id = str(uuid.uuid4())
        record.update({"leadId": lead_id, "mode": "mock"})
        save_mock(record)
        return self._json(201, {
            "ok": True, "mode": "mock", "leadId": lead_id,
            "note": "Modo MOCK: el lead se guardo en api/_data/leads.json. "
                    "Con LEAD_MODE=dataverse este mismo payload se crea en la entidad Lead.",
            "landing": {"code": landing["code"], "name": landing["name"],
                        "brand": landing.get("brand"), "ownerTeam": landing.get("owner_team"),
                        "campaign": landing.get("campaign")},
            "dataversePayload": lead,
        })


def main():
    port = CONFIG["port"]
    try:
        codes = sorted(load_landings()[1].keys())
    except (OSError, ValueError) as err:
        print("ERROR: no se pudo leer landings.json -> %s" % err)
        return 1

    print("")
    print("=" * 66)
    print(" API UNICA DE CAPTURA DE LEADS  |  W-IT  |  Demo Legrand + Teknica")
    print("=" * 66)
    print(" Sitio      : http://localhost:%d/" % port)
    print(" Endpoint   : POST http://localhost:%d/api/leads" % port)
    print(" Salud      : GET  http://localhost:%d/api/health" % port)
    print(" Consola    : http://localhost:%d/admin.html" % port)
    print(" Modo       : %s" % CONFIG["mode"].upper())
    if CONFIG["mode"] == "dataverse":
        print(" Entorno D365: %s" % (CONFIG["dv_url"] or "(sin configurar)"))
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
