#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================================================
 CONSULTA DE ORDENES DE TRABAJO (Field Service)  |  W-IT
=========================================================================

 Segunda cara de la misma integracion: si /api/leads demuestra que se puede
 ESCRIBIR en Dynamics desde un sitio, esto demuestra que tambien se puede
 LEER, con filtros, sin exponer el CRM.

   GET /api/clientes     -> cuentas con ordenes, para el selector
   GET /api/workorders   -> ordenes filtradas por cliente, fecha y estado

 Reutiliza la conexion y el token de lead_core: un solo App Registration,
 una sola configuracion.

 NOTA DE SEGURIDAD: este endpoint es de solo lectura y devuelve unicamente
 los campos declarados en SELECT_OT. Aun asi, en produccion debe quedar
 detras de autenticacion (Static Web Apps la trae integrada con Entra ID):
 una consulta de ordenes de trabajo es informacion de clientes.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

import lead_core

# Solo estos campos salen del CRM. Lo que no esta aqui, no se expone.
SELECT_OT = ("msdyn_name,msdyn_systemstatus,msdyn_timewindowstart,msdyn_timewindowend,"
             "msdyn_completedon,msdyn_totalamount,msdyn_workordersummary,msdyn_workorderid")
EXPAND_OT = "msdyn_serviceaccount($select=name,accountid),msdyn_workordertype($select=msdyn_name)"

ESTADOS = {
    690970000: "Sin programar",
    690970001: "Programada",
    690970002: "En curso",
    690970003: "Completada",
    690970004: "Registrada",
    690970005: "Cancelada",
}

RE_GUID = re.compile(r"^[0-9a-fA-F-]{36}$")
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOPE_MAXIMO = 200


def _consultar(config, recurso, params):
    """GET contra la Web API con el token de la aplicacion."""
    url = "%s/api/data/%s/%s?%s" % (config["dv_url"], config["dv_api"], recurso,
                                    urllib.parse.urlencode(params, quote_via=urllib.parse.quote))
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + lead_core.get_token(config),
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        # Trae las etiquetas de los conjuntos de opciones y los montos formateados.
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"',
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detalle = err.read().decode("utf-8", "replace")[:600]
        raise RuntimeError("Dataverse respondio %s: %s" % (err.code, detalle))


def _fmt(registro, campo):
    """Valor formateado por Dataverse (etiqueta del estado, monto con moneda)."""
    return registro.get(campo + "@OData.Community.Display.V1.FormattedValue")


def listar_clientes(config=None):
    """Cuentas que tienen al menos una orden de trabajo, para el selector."""
    config = config or lead_core.get_config()
    if config["mode"] != "dataverse" or not config["dv_url"]:
        return 503, {"ok": False, "error": "La consulta de ordenes requiere LEAD_MODE=dataverse."}

    datos = _consultar(config, "msdyn_workorders", {
        "$select": "msdyn_workorderid",
        "$expand": "msdyn_serviceaccount($select=name,accountid)",
        "$top": "1000",
    })
    vistos = {}
    for ot in datos.get("value", []):
        cuenta = ot.get("msdyn_serviceaccount") or {}
        if cuenta.get("accountid"):
            vistos.setdefault(cuenta["accountid"], cuenta.get("name") or "(sin nombre)")

    clientes = [{"id": k, "nombre": v} for k, v in vistos.items()]
    clientes.sort(key=lambda c: c["nombre"].lower())
    return 200, {"ok": True, "count": len(clientes), "clientes": clientes,
                 "estados": [{"codigo": k, "nombre": v} for k, v in sorted(ESTADOS.items())]}


def listar_ordenes(filtros, config=None):
    """Ordenes de trabajo filtradas por cliente, rango de fechas y estado.

    Los filtros se validan antes de armar el $filter: un GUID que no es GUID o
    una fecha que no es fecha se rechazan, no se concatenan a la consulta."""
    config = config or lead_core.get_config()
    if config["mode"] != "dataverse" or not config["dv_url"]:
        return 503, {"ok": False,
                     "error": "La consulta de ordenes requiere LEAD_MODE=dataverse y un entorno configurado."}

    errores, condiciones = [], []
    aplicados = {}

    cliente = (filtros.get("cliente") or "").strip()
    if cliente:
        if not RE_GUID.match(cliente):
            errores.append("El identificador de cliente no es valido.")
        else:
            condiciones.append("_msdyn_serviceaccount_value eq %s" % cliente)
            aplicados["cliente"] = cliente

    for clave, operador, etiqueta in (("desde", "ge", "desde"), ("hasta", "le", "hasta")):
        valor = (filtros.get(clave) or "").strip()
        if not valor:
            continue
        if not RE_FECHA.match(valor):
            errores.append("La fecha '%s' debe venir como AAAA-MM-DD." % etiqueta)
            continue
        limite = valor + ("T00:00:00Z" if clave == "desde" else "T23:59:59Z")
        condiciones.append("msdyn_timewindowstart %s %s" % (operador, limite))
        aplicados[clave] = valor

    estado = (filtros.get("estado") or "").strip()
    if estado:
        if not estado.isdigit() or int(estado) not in ESTADOS:
            errores.append("El estado indicado no existe.")
        else:
            condiciones.append("msdyn_systemstatus eq %s" % estado)
            aplicados["estado"] = int(estado)

    if errores:
        return 400, {"ok": False, "error": "Filtros invalidos", "details": errores}

    try:
        tope = min(max(int(filtros.get("top") or 100), 1), TOPE_MAXIMO)
    except ValueError:
        tope = 100

    params = {"$select": SELECT_OT, "$expand": EXPAND_OT,
              "$orderby": "msdyn_timewindowstart desc", "$top": str(tope)}
    if condiciones:
        params["$filter"] = " and ".join(condiciones)

    try:
        datos = _consultar(config, "msdyn_workorders", params)
    except (RuntimeError, urllib.error.URLError) as err:
        return 502, {"ok": False, "error": "No se pudo consultar Dynamics 365", "details": [str(err)]}

    ordenes = []
    for ot in datos.get("value", []):
        cuenta = ot.get("msdyn_serviceaccount") or {}
        tipo = ot.get("msdyn_workordertype") or {}
        ordenes.append({
            "numero": ot.get("msdyn_name"),
            "cliente": cuenta.get("name"),
            "clienteId": cuenta.get("accountid"),
            "tipo": tipo.get("msdyn_name"),
            "estado": _fmt(ot, "msdyn_systemstatus") or ESTADOS.get(ot.get("msdyn_systemstatus"), "-"),
            "estadoCodigo": ot.get("msdyn_systemstatus"),
            "inicio": ot.get("msdyn_timewindowstart"),
            "fin": ot.get("msdyn_timewindowend"),
            "completada": ot.get("msdyn_completedon"),
            "monto": ot.get("msdyn_totalamount"),
            "montoTexto": _fmt(ot, "msdyn_totalamount"),
            "resumen": ot.get("msdyn_workordersummary"),
            "urlRegistro": "%s/main.aspx?pagetype=entityrecord&etn=msdyn_workorder&id=%s" % (
                config["dv_url"], ot.get("msdyn_workorderid")),
        })

    return 200, {"ok": True, "count": len(ordenes), "tope": tope,
                 "filtros": aplicados, "entorno": config["dv_url"], "ordenes": ordenes}
