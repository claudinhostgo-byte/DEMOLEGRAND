#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de las 4 landings de la demo.

Todas las landings comparten la misma estructura, el mismo CSS y el mismo
JavaScript: lo unico que cambia es el contenido y el codigo de origen. Este
script deja eso explicito -> agregar una landing nueva es agregar un bloque a
SPECS (y su entrada en api/landings.json), no escribir una pagina desde cero.

    py tools/build_landings.py     ->  escribe landings/*.html
"""

import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "landings")

BRAND_WORDMARK = {
    "legrand": ("legrand", ".26em"),
    "teknica": ("teknica", ".22em"),
    "bticino": ("bticino", ".20em"),
}

SPECS = [
    {
        "code": "LGD-DC-001",
        "slug": "datacenter",
        "brand": "legrand",
        "eyebrow": "Infraestructura digital",
        "title": "Data centers que no se caen,<br>desde el rack hasta la última toma",
        "lead": "Cableado estructurado LCS³, racks de comunicaciones, distribución de energía y "
                "monitoreo para salas eléctricas y data centers. Diseñamos con el estándar de "
                "Legrand y ejecutamos con la experiencia de Teknica en infraestructura crítica.",
        "bullets": [
            "Cableado estructurado LCS³ en cobre y fibra, certificado extremo a extremo",
            "Racks, gabinetes y gestión térmica para alta densidad",
            "Distribución de energía en rack (PDU) y tableros de sala eléctrica",
            "Continuidad operacional integrada: UPS, clima de precisión y detección de incendios",
        ],
        "cards": [
            ("Cableado estructurado LCS³", "Soluciones de cobre y fibra óptica con garantía de sistema y desempeño certificado."),
            ("Racks y gabinetes", "Gabinetes de piso y murales, organización de cables y accesorios para alta densidad."),
            ("Distribución de energía", "PDU en rack, tableros de distribución y protección modular para la sala eléctrica."),
            ("Salas eléctricas modulares", "Diseño, fabricación e instalación de salas eléctricas y contenedores para faenas."),
        ],
        "form_title": "Cotiza tu proyecto de data center",
        "form_lead": "Un especialista de infraestructura digital te contacta con el levantamiento inicial.",
        "cta": "Solicitar contacto de un especialista",
        "extras": [
            ("tipoProyecto", "Tipo de proyecto", ["Data center nuevo", "Ampliación de un data center existente",
                                                   "Migración o consolidación", "Sala eléctrica o contenedor"], True),
            ("racks", "Racks estimados", ["1 a 10", "11 a 40", "41 a 100", "Más de 100", "Aún por definir"], False),
            ("plazo", "Plazo estimado", ["Inmediato (menos de 1 mes)", "1 a 3 meses", "3 a 6 meses",
                                          "Más de 6 meses / evaluando"], False),
        ],
    },
    {
        "code": "TKN-UPS-002",
        "slug": "ups-continuidad",
        "brand": "teknica",
        "eyebrow": "Teknica · Continuidad operacional",
        "title": "Cuando cae la energía,<br>tu operación sigue.",
        "lead": "UPS, calidad de energía, grupos generadores, clima de precisión y detección de "
                "incendios para infraestructura crítica. Expertos en soluciones y continuidad "
                "operacional para minería, telecomunicaciones, transporte y utilities.",
        "bullets": [
            "UPS y sistemas de respaldo de energía con servicio y repuestos en Chile",
            "Diagnóstico de calidad de energía y corrección de armónicos",
            "Mantención preventiva y correctiva con SLA, en faena o en planta",
            "Monitoreo integrado del estado de los equipos críticos",
        ],
        "cards": [
            ("UPS y power quality", "Equipos de respaldo, bancos de baterías, rectificadores y corrección de calidad de energía."),
            ("Clima de precisión", "Climatización industrial y de precisión, chillers y manejadoras para salas técnicas."),
            ("Detección y extinción", "Detección temprana y extinción de incendios para salas eléctricas y data centers."),
            ("Mantención y monitoreo", "Contratos de mantención con SLA y monitoreo integrado de equipamiento crítico."),
        ],
        "form_title": "Habla con un especialista en continuidad",
        "form_lead": "Cuéntanos qué necesitas respaldar y te contactamos con un diagnóstico inicial.",
        "cta": "Quiero un diagnóstico",
        "extras": [
            ("potencia", "Potencia requerida", ["Hasta 10 kVA", "10 a 50 kVA", "50 a 200 kVA",
                                                 "Más de 200 kVA", "No lo tengo definido"], True),
            ("criticidad", "Nivel de criticidad", ["Crítica: opera 24/7 sin margen de corte",
                                                    "Alta: tolera minutos", "Media: tolera horas",
                                                    "Baja"], True),
            ("servicio", "Tipo de requerimiento", ["Equipo nuevo", "Reemplazo o upgrade",
                                                     "Mantención y soporte",
                                                     "Diagnóstico de calidad de energía"], False),
        ],
    },
    {
        "code": "LGD-IND-003",
        "slug": "industria",
        "brand": "legrand",
        "eyebrow": "Industria y proyectos",
        "title": "Distribución y protección<br>a la altura de la faena",
        "lead": "Protección modular, ductos de barra, canalización industrial, bandejas y tableros "
                "para minería, manufactura, energía y transporte. Soporte técnico para tableristas, "
                "integradores, proyectistas y distribuidores.",
        "bullets": [
            "Protección modular, comandos y contactores para tablero industrial",
            "Ductos de barra y canalización para distribución de alta corriente",
            "Bandejas y soportería de cables para ambientes exigentes",
            "Apoyo en especificación técnica y capacitación al canal",
        ],
        "cards": [
            ("Protección modular", "Interruptores, diferenciales y protecciones para tablero de distribución."),
            ("Ductos de barra", "Sistemas de barra para distribución de energía en planta e industria."),
            ("Canalización y bandejas", "Bandejas portacables, soportería y canalización para ambientes severos."),
            ("Tableros y gabinetes", "Envolventes, gabinetes y accesorios para tablero de fuerza y control."),
        ],
        "form_title": "Solicita apoyo técnico o comercial",
        "form_lead": "Atendemos a tableristas, integradores, distribuidores, proyectistas y usuarios finales.",
        "cta": "Solicitar apoyo técnico",
        "extras": [
            ("perfil", "Tu perfil", ["Tablerista", "Integrador", "Distribuidor",
                                      "Proyectista o especificador", "Usuario final / mantención"], True),
            ("industria", "Industria", ["Minería", "Manufactura", "Energía y utilities",
                                         "Transporte", "Telecomunicaciones", "Otra"], True),
            ("familia", "Familia de producto de interés", ["Protección modular", "Ductos de barra",
                                                            "Canalización y bandejas",
                                                            "Tableros y gabinetes",
                                                            "Comandos y contactores"], False),
        ],
    },
    {
        "code": "LGD-RET-004",
        "slug": "retail-terciario",
        "brand": "bticino",
        "eyebrow": "Bticino · Sector terciario",
        "title": "Retail, salud y edificios<br>con instalaciones a la vista",
        "lead": "Mecanismos, conectividad y control Bticino para retail, clínicas, hoteles, "
                "oficinas y educación. Terminaciones que se ven, infraestructura que se mantiene "
                "y soluciones conectadas para operar el edificio.",
        "bullets": [
            "Líneas de mecanismos Living Now, Livinglight y Matix",
            "Conectividad de datos y cargadores USB integrados al mecanismo",
            "Control de iluminación, persianas y clima para espacios comunes",
            "Videoporteros y control de acceso para edificios y recintos de salud",
        ],
        "cards": [
            ("Mecanismos y terminaciones", "Living Now, Livinglight y Matix para distintos niveles de terminación."),
            ("Conectividad", "Tomas de datos, cargadores USB y puntos de conexión para áreas de atención."),
            ("Control del edificio", "Iluminación, persianas, clima y escenas para espacios comunes y salas."),
            ("Videoportería y acceso", "Videoporteros, control de acceso y comunicación interna del recinto."),
        ],
        "form_title": "Conversemos tu proyecto de edificación",
        "form_lead": "Te contactamos con el equipo de terciario y retail para revisar especificación y volúmenes.",
        "cta": "Quiero que me contacten",
        "extras": [
            ("tipoEdificacion", "Tipo de edificación", ["Retail o tienda", "Hospital o clínica",
                                                         "Hotel", "Oficinas", "Educación", "Otro"], True),
            ("superficie", "Superficie aproximada", ["Menos de 500 m²", "500 a 2.000 m²",
                                                      "2.000 a 10.000 m²", "Más de 10.000 m²"], False),
            ("etapa", "Etapa del proyecto", ["Idea o anteproyecto", "Diseño y especificación",
                                              "Licitación", "En ejecución"], True),
        ],
    },
]

TEMPLATE = """<!DOCTYPE html>
<html lang="es-CL" data-brand="{brand}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} | Demo landings W-IT</title>
<meta name="description" content="{tagline}">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%230D3445'/%3E%3Cpath d='M6 10h4l2 8 2-8h4l2 8 2-8h4l-4 14h-5l-1-5-1 5H10z' fill='%2374E507'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/css/site.css">
<!-- Landing generada por tools/build_landings.py - no editar a mano -->
</head>
<body>

<div class="demobar">
  Landing de DEMOSTRACIÓN de W-IT. Código de origen <b>{code}</b>. Los datos ingresados son de prueba.
</div>

<header class="topbar">
  <div class="wrap">
    <span class="brandmark" style="font-size:1.05rem;letter-spacing:{wordmark_ls}">{wordmark}</span>
    <span class="chip" style="background:transparent;border-color:rgba(255,255,255,.25);color:rgba(255,255,255,.75)">{eyebrow}</span>
    <nav>
      <a href="#soluciones" class="hide-sm">Soluciones</a>
      <a href="#formulario" class="hide-sm">Contacto</a>
      <a class="pill" href="../index.html" data-keep-utm>&larr; Sitio maestro</a>
    </nav>
  </div>
</header>

<section class="hero" id="formulario">
  <div class="wrap">
    <div class="hero-grid">
      <div>
        <span class="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p class="lead">{lead}</p>
        <ul class="bullets">
{bullets_html}
        </ul>
      </div>

      <div class="form-shell">
        <h3>{form_title}</h3>
        <p class="small muted">{form_lead}</p>

        <form data-landing-code="{code}" novalidate>
          <div class="form-grid">
            <div class="field">
              <label for="f-nombre-{slug}">Nombre <span class="req">*</span></label>
              <input id="f-nombre-{slug}" name="firstName" type="text" autocomplete="given-name" required>
              <span class="err"></span>
            </div>
            <div class="field">
              <label for="f-apellido-{slug}">Apellido <span class="req">*</span></label>
              <input id="f-apellido-{slug}" name="lastName" type="text" autocomplete="family-name" required>
              <span class="err"></span>
            </div>
            <div class="field">
              <label for="f-email-{slug}">Correo corporativo <span class="req">*</span></label>
              <input id="f-email-{slug}" name="email" type="email" autocomplete="email" required>
              <span class="err"></span>
            </div>
            <div class="field">
              <label for="f-fono-{slug}">Teléfono</label>
              <input id="f-fono-{slug}" name="phone" type="tel" autocomplete="tel" placeholder="+56 9 ...">
              <span class="err"></span>
            </div>
            <div class="field">
              <label for="f-empresa-{slug}">Empresa <span class="req">*</span></label>
              <input id="f-empresa-{slug}" name="company" type="text" autocomplete="organization" required>
              <span class="err"></span>
            </div>
            <div class="field">
              <label for="f-cargo-{slug}">Cargo</label>
              <input id="f-cargo-{slug}" name="jobTitle" type="text" autocomplete="organization-title">
              <span class="err"></span>
            </div>

{extras_html}

            <div class="field full">
              <label for="f-msg-{slug}">Cuéntanos brevemente qué necesitas</label>
              <textarea id="f-msg-{slug}" name="message"></textarea>
              <span class="err"></span>
            </div>

            <div class="field full">
              <label class="consent">
                <input type="checkbox" name="consent" required>
                <span>Autorizo el tratamiento de mis datos personales para ser contactado con fines
                comerciales, conforme a la política de privacidad y a la Ley 21.719.
                <span class="req">*</span></span>
              </label>
              <span class="err"></span>
            </div>

            <div class="full">
              <button class="btn btn-primary btn-block" type="submit">{cta}</button>
            </div>
          </div>

          <div class="form-status"></div>
        </form>

        <p class="small muted" style="margin-top:14px;margin-bottom:0">
          Este formulario envía a <span class="mono">POST /api/leads</span> con el código de origen
          <span class="mono">{code}</span>. Es el mismo endpoint que usan las otras tres landings.
        </p>
      </div>
    </div>
  </div>
</section>

<section id="soluciones">
  <div class="wrap">
    <div class="section-head">
      <h2>{name}</h2>
      <p class="muted">{tagline}</p>
    </div>
    <div class="grid grid-4">
{cards_html}
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <div class="grid grid-2">
      <div>
        <h2>Trazabilidad del envío</h2>
        <p class="muted">
          Todo lo que esta landing manda al CRM está a la vista. Antes de enviar se muestra el
          origen capturado; al enviar, el JSON del <span class="mono">POST</span> y la respuesta
          de la API con el <span class="mono">leadid</span> creado.
        </p>
        <div class="chiprow" style="margin:18px 0">
          <span class="chip chip-accent">Código de origen: {code}</span>
          <span class="chip">Equipo: {owner_team}</span>
          <span class="chip">Campaña: {campaign}</span>
          <span class="chip">Entidad destino: Lead</span>
        </div>
        <p class="small muted">
          Los campos propios de esta landing ({extra_labels}) viajan en el bloque
          <span class="mono">fields</span> y quedan registrados en el lead.
        </p>
        <p><a class="btn btn-dark btn-sm" href="../admin.html">Ver la consola de leads</a></p>
      </div>
      <div>
        <div class="trace-head">
          <span class="t">Origen capturado / payload</span>
          <span class="chip mono">{code}</span>
        </div>
        <pre class="trace" id="trace-{code}" data-origin-preview>{{}}</pre>
      </div>
    </div>
  </div>
</section>

<footer class="site">
  <div class="wrap">
    <img class="logo" src="../assets/img/logo-wit-blanco.svg" alt="W-IT">
    <span class="disclaimer">
      Landing de demostración creada por W-IT para ilustrar la captura de leads de distintas líneas
      de negocio en una sola API con destino Dynamics 365. Legrand, Bticino, Teknica y Enersafe son
      marcas de sus respectivos titulares; este ambiente no es un sitio oficial de esas marcas.
    </span>
    <span style="margin-left:auto"><a href="../index.html" data-keep-utm>Volver al sitio maestro</a></span>
  </div>
</footer>

<script src="../assets/js/config.js"></script>
<script src="../assets/js/landing.js"></script>
</body>
</html>
"""


def field_extra(slug, key, label, options, required):
    req = ' required' if required else ''
    star = ' <span class="req">*</span>' if required else ''
    opts = ['<option value="">Selecciona…</option>']
    opts += ['<option>%s</option>' % o for o in options]
    return (
        '            <div class="field">\n'
        '              <label for="f-%s-%s">%s%s</label>\n'
        '              <select id="f-%s-%s" name="extra:%s"%s>\n'
        '                %s\n'
        '              </select>\n'
        '              <span class="err"></span>\n'
        '            </div>' % (key, slug, label, star, key, slug, key, req,
                                "\n                ".join(opts))
    )


def build():
    with io.open(os.path.join(ROOT, "api", "landings.json"), encoding="utf-8") as fh:
        catalog = {l["code"]: l for l in json.load(fh)["landings"]}

    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    for spec in SPECS:
        meta = catalog[spec["code"]]
        wordmark, ls = BRAND_WORDMARK[spec["brand"]]
        html = TEMPLATE.format(
            brand=spec["brand"],
            code=spec["code"],
            slug=spec["slug"],
            name=meta["name"],
            tagline=meta["tagline"],
            owner_team=meta.get("owner_team", "-"),
            campaign=meta.get("campaign", "-"),
            wordmark=wordmark,
            wordmark_ls=ls,
            eyebrow=spec["eyebrow"],
            title=spec["title"],
            lead=spec["lead"],
            form_title=spec["form_title"],
            form_lead=spec["form_lead"],
            cta=spec["cta"],
            bullets_html="\n".join("          <li>%s</li>" % b for b in spec["bullets"]),
            cards_html="\n".join(
                '      <div class="card"><h3>%s</h3><p class="small muted">%s</p></div>' % c
                for c in spec["cards"]),
            extras_html="\n".join(field_extra(spec["slug"], *e) for e in spec["extras"]),
            extra_labels=", ".join(f["label"] for f in meta.get("extra_fields", [])),
        )
        path = os.path.join(OUT_DIR, spec["slug"] + ".html")
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)
        written.append(os.path.relpath(path, ROOT))

    print("Landings generadas:")
    for w in written:
        print("  - " + w.replace("\\", "/"))


if __name__ == "__main__":
    build()
