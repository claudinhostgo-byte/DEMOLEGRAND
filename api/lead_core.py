#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================================================
 NUCLEO DE LA API UNICA DE CAPTURA DE LEADS  ->  Dynamics 365 (Lead)
 W-IT  |  Demo de integracion de landings para Legrand + Teknica
=========================================================================

 Toda la logica de negocio vive aqui y la usan los dos hosts sin duplicar
 una sola linea:

   - api/leads/__init__.py    -> Azure Function (Static Web Apps, /api/leads)
   - tools/dev_server.py      -> servidor local para la demo (localhost:8080)

 Configuracion por variables de entorno. En local se leen desde api/.env
 (que esta en .gitignore); en Azure, desde la configuracion de la aplicacion
 de Static Web Apps. Las credenciales nunca viven en el repositorio.
"""

import json
import os
import re
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(API_DIR)
DATA_DIR = os.path.join(API_DIR, "_data")
MOCK_STORE = os.path.join(DATA_DIR, "leads.json")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$")

# Limites de longitud de los campos estandar de la entidad Lead en Dataverse.
MAXLEN = {
    "subject": 300, "firstname": 50, "lastname": 50, "emailaddress1": 100,
    "mobilephone": 50, "telephone1": 50, "companyname": 100, "jobtitle": 100,
    "description": 100000,
}

# En Azure el sistema de archivos de la Function es de solo lectura: si no se
# puede escribir el archivo mock, los leads quedan en memoria del proceso.
_MEMORY_STORE = []
_token_cache = {"value": None, "expires_at": 0}


# ---------------------------------------------------------------- configuracion
def load_env():
    """Carga api/.env (KEY=VALOR) sin dependencias externas. Solo aplica en
    local: en Azure la configuracion llega como variables de entorno."""
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


def get_config():
    """Se lee en cada request para que un cambio de configuracion en Azure
    tome efecto sin volver a desplegar."""
    return {
        # mock = no escribe en CRM | dataverse = crea el lead en Dynamics 365
        "mode": os.environ.get("LEAD_MODE", "mock").lower(),
        "dv_url": os.environ.get("DV_URL", "").rstrip("/"),
        "dv_tenant": os.environ.get("DV_TENANT_ID", ""),
        "dv_client_id": os.environ.get("DV_CLIENT_ID", ""),
        "dv_secret": os.environ.get("DV_CLIENT_SECRET", ""),
        "dv_api": os.environ.get("DV_API_VERSION", "v9.2"),
        # Columnas personalizadas OPCIONALES: si el entorno las tiene creadas,
        # se declaran aqui y el codigo no cambia.
        "field_landing_code": os.environ.get("FIELD_LANDING_CODE", ""),
        "field_utm_source": os.environ.get("FIELD_UTM_SOURCE", ""),
        "field_utm_campaign": os.environ.get("FIELD_UTM_CAMPAIGN", ""),
        "port": int(os.environ.get("PORT", "8080")),
    }


def landings_path():
    """El catalogo viaja junto a la API (api/landings.json) para que se
    despliegue con la Function. En local tambien se acepta en la raiz."""
    for candidate in (os.path.join(API_DIR, "landings.json"),
                      os.path.join(ROOT, "landings.json")):
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("No se encontro landings.json (catalogo de origenes).")


def load_landings():
    """Fuente unica de verdad de los origenes. Se relee en cada request para
    poder dar de alta una landing sin reiniciar ni redesplegar."""
    with open(landings_path(), "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data, {item["code"]: item for item in data.get("landings", [])}


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


def build_lead(payload, landing, defaults, config):
    """Traduce el payload comun de cualquier landing a la entidad Lead."""
    tracking = payload.get("tracking") or {}
    company = clean(payload.get("company"), MAXLEN["companyname"])

    subject_tpl = defaults.get("subject_template", "[{code}] {interes} - {company}")
    subject = subject_tpl.format(code=landing["code"], interes=landing["name"],
                                 company=company or "Sin empresa")

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

    if config["field_landing_code"]:
        lead[config["field_landing_code"]] = landing["code"]
    if config["field_utm_source"] and tracking.get("utm_source"):
        lead[config["field_utm_source"]] = clean(tracking["utm_source"], 100)
    if config["field_utm_campaign"] and tracking.get("utm_campaign"):
        lead[config["field_utm_campaign"]] = clean(tracking["utm_campaign"], 100)

    return lead


# ---------------------------------------------------------------- Dataverse
def get_token(config):
    """OAuth2 client_credentials contra Entra ID. El scope lleva la URL del
    entorno: es ahi donde se decide en que Dynamics caen los leads."""
    now = time.time()
    if _token_cache["value"] and _token_cache["expires_at"] - 120 > now:
        return _token_cache["value"]

    faltantes = [k.upper() for k in ("dv_url", "dv_tenant", "dv_client_id", "dv_secret")
                 if not config[k]]
    if faltantes:
        raise RuntimeError("Falta configurar %s" % ", ".join(faltantes))

    url = "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % config["dv_tenant"]
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": config["dv_client_id"],
        "client_secret": config["dv_secret"],
        "scope": config["dv_url"] + "/.default",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode("utf-8"))

    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = now + int(data.get("expires_in", 3600))
    return _token_cache["value"]


def create_lead_dataverse(lead, config):
    """POST /api/data/v9.2/leads. Devuelve (leadid, url_del_registro)."""
    token = get_token(config)
    endpoint = "%s/api/data/%s/leads" % (config["dv_url"], config["dv_api"])
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
    record_url = "%s/main.aspx?pagetype=entityrecord&etn=lead&id=%s" % (config["dv_url"], lead_id)
    return lead_id, record_url


# ---------------------------------------------------------------- almacen local
def save_record(record):
    """Guarda el envio para la consola de la demo. En Azure el disco es de
    solo lectura, asi que cae a memoria del proceso sin romper el flujo."""
    _MEMORY_STORE.insert(0, record)
    del _MEMORY_STORE[200:]
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        existing = read_file_store()
        existing.insert(0, record)
        with open(MOCK_STORE, "w", encoding="utf-8") as fh:
            json.dump(existing[:500], fh, ensure_ascii=False, indent=2)
    except OSError:
        pass  # entorno de solo lectura: queda la copia en memoria


def read_file_store():
    if not os.path.exists(MOCK_STORE):
        return []
    try:
        with open(MOCK_STORE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return []


def read_records():
    disco = read_file_store()
    return disco if disco else list(_MEMORY_STORE)


# ---------------------------------------------------------------- casos de uso
def health(config=None):
    config = config or get_config()
    try:
        codes = sorted(load_landings()[1].keys())
    except (OSError, ValueError) as err:
        codes = []
    return {
        "ok": True,
        "service": "API unica de captura de leads - W-IT",
        "mode": config["mode"],
        "dataverse": {
            "configured": bool(config["dv_url"] and config["dv_client_id"]),
            "url": config["dv_url"] or None,
            "apiVersion": config["dv_api"],
            "customFields": {k: v for k, v in config.items() if k.startswith("field_") and v},
        },
        "landings": codes,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def list_leads(config=None):
    config = config or get_config()
    leads = read_records()
    return {"ok": True, "mode": config["mode"], "count": len(leads), "leads": leads}


def create_lead(payload, config=None):
    """Caso de uso completo: valida, mapea y persiste. Devuelve (status, cuerpo).
    Es el unico punto donde se decide que pasa con un envio, sin importar si
    llego por Azure Functions o por el servidor local de la demo."""
    config = config or get_config()

    if not isinstance(payload, dict):
        return 400, {"ok": False, "error": "JSON invalido",
                     "details": ["Se esperaba un objeto JSON."]}

    try:
        catalog, index = load_landings()
    except (OSError, ValueError) as err:
        return 500, {"ok": False, "error": "No se pudo leer el catalogo de landings",
                     "details": [str(err)]}

    landing, errors = validate(payload, index)
    if errors:
        return 400, {"ok": False, "error": "Validacion fallida", "details": errors}

    lead = build_lead(payload, landing, catalog.get("defaults", {}), config)

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
    resumen_landing = {"code": landing["code"], "name": landing["name"],
                       "brand": landing.get("brand"), "ownerTeam": landing.get("owner_team"),
                       "campaign": landing.get("campaign")}

    if config["mode"] == "dataverse":
        try:
            lead_id, record_url = create_lead_dataverse(lead, config)
        except (RuntimeError, urllib.error.URLError, KeyError) as err:
            record.update({"leadId": None, "mode": "dataverse-error", "error": str(err)})
            save_record(record)
            return 502, {"ok": False, "error": "No se pudo crear el lead en Dynamics 365",
                         "details": [str(err)], "landing": landing["code"]}

        record.update({"leadId": lead_id, "mode": "dataverse", "recordUrl": record_url})
        save_record(record)
        return 201, {"ok": True, "mode": "dataverse", "leadId": lead_id, "recordUrl": record_url,
                     "landing": resumen_landing, "dataversePayload": lead}

    # Modo mock: misma respuesta y mismo payload, sin escribir en el CRM.
    lead_id = str(uuid.uuid4())
    record.update({"leadId": lead_id, "mode": "mock"})
    save_record(record)
    return 201, {
        "ok": True, "mode": "mock", "leadId": lead_id,
        "note": "Modo MOCK: el lead no se escribio en el CRM. "
                "Con LEAD_MODE=dataverse este mismo payload se crea en la entidad Lead.",
        "landing": resumen_landing, "dataversePayload": lead,
    }
