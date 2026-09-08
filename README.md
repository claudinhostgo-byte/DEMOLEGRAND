# Demo: integración de landings con Dynamics 365 — Legrand + Teknica

Demo funcional preparada por **W-IT** para responder una pregunta concreta del cliente:

> ¿Cómo se hace, y qué tan difícil es, tener **landing pages distintas por línea de negocio**
> que caigan como **leads en un mismo CRM**, sabiendo de dónde vino cada uno?

La respuesta que muestra esta demo: **una sola API** recibe los formularios de **todas** las
landings, valida el origen, lo traduce al modelo de datos de Dynamics 365 y crea el registro en la
entidad **Lead** con la trazabilidad completa (landing, campaña, UTM, referrer y campos propios de
esa línea).

---

## 1. Qué incluye

| Pieza | Archivo | Qué hace |
|---|---|---|
| Sitio maestro | `index.html` | Portada con el logo de W-IT, las 4 landings, el diagrama de la integración y la lectura de dificultad de implementación |
| Landing 1 · `LGD-DC-001` | `landings/datacenter.html` | Data Center e Infraestructura Digital (Legrand) |
| Landing 2 · `TKN-UPS-002` | `landings/ups-continuidad.html` | UPS, Power Quality y Continuidad Operacional (Teknica) |
| Landing 3 · `LGD-IND-003` | `landings/industria.html` | Distribución de energía y tableros para industria (Legrand) |
| Landing 4 · `LGD-RET-004` | `landings/retail-terciario.html` | Retail, hospitales y edificios (Bticino) |
| **API única** | `api/lead_api.py` | `POST /api/leads` — el **único** endpoint que usan las 4 landings |
| Catálogo de orígenes | `landings.json` | Fuente única de verdad: códigos, marcas, equipos y campañas |
| Consola de leads | `admin.html` | Muestra lo que llegó por la API (en producción, esto es la vista de Clientes potenciales del CRM) |
| Generador de landings | `tools/build_landings.py` | Regenera las 4 landings desde una especificación corta |

Las cuatro líneas de negocio corresponden a las que el grupo opera en Chile tras la adquisición de
Teknica y Enersafe por parte de Legrand Chile: infraestructura digital y data centers, respaldo y
calidad de energía, distribución de energía para industria y minería, y sector terciario con Bticino.

---

## 2. Cómo levantar la demo

Requisito único: **Python 3.8+** (la API usa solo biblioteca estándar, sin `pip install`).

```bash
py api/lead_api.py
```

O bien doble clic en `run-demo.cmd`. Luego abrir <http://localhost:8080/>.

El mismo proceso sirve el sitio estático **y** la API, así que no hay problemas de CORS ni de
configuración durante la demo.

| URL | Para qué |
|---|---|
| <http://localhost:8080/> | Sitio maestro con las 4 landings |
| <http://localhost:8080/admin.html> | Consola de leads capturados |
| <http://localhost:8080/api/health> | Estado y modo de la API |
| <http://localhost:8080/api/landings> | Catálogo de orígenes registrados |

---

## 3. Modos de operación

La API arranca en **MOCK** por defecto: valida y arma el payload real de Dynamics, pero lo guarda en
`api/_data/leads.json` en lugar de escribir en el CRM. Sirve para mostrar todo el flujo sin tocar
ningún entorno.

Para escribir leads reales en Dynamics 365:

1. Copiar `api/.env.example` a `api/.env`.
2. Completar `DV_URL`, `DV_TENANT_ID`, `DV_CLIENT_ID`, `DV_CLIENT_SECRET`.
3. Cambiar `LEAD_MODE=dataverse`.
4. Reiniciar la API.

> **Antes de cambiar a `dataverse`, confirmar el entorno.** El `scope` del token lleva la URL del
> entorno: ahí se decide en qué Dynamics caen los leads. `api/.env` está en `.gitignore` y **nunca**
> debe subirse al repositorio.

El App Registration necesita estar dado de alta como **Application User** en el entorno de destino,
con un rol de seguridad que permita crear registros de la entidad Lead.

---

## 4. El contrato de la API

Todas las landings envían exactamente la misma estructura. Lo único que cambia entre una y otra es
`landingCode` y el contenido de `fields`.

```http
POST /api/leads
Content-Type: application/json
```

```json
{
  "landingCode": "TKN-UPS-002",
  "firstName": "Martín",
  "lastName": "Rojas",
  "email": "m.rojas@cliente.cl",
  "phone": "+56 9 8765 4321",
  "company": "Minera Andes S.A.",
  "jobTitle": "Jefe de Mantención",
  "message": "Necesitamos respaldo para la sala eléctrica.",
  "consent": true,
  "fields": { "potencia": "50 a 200 kVA", "criticidad": "Crítica: opera 24/7" },
  "tracking": {
    "utm_source": "linkedin", "utm_medium": "paid", "utm_campaign": "UPS-2026-Q3",
    "referrer": "https://www.linkedin.com/", "landingUrl": "https://.../ups-continuidad.html"
  }
}
```

Respuesta (201):

```json
{
  "ok": true,
  "mode": "dataverse",
  "leadId": "6f0f1b2c-...",
  "recordUrl": "https://<entorno>.crm2.dynamics.com/main.aspx?pagetype=entityrecord&etn=lead&id=...",
  "landing": { "code": "TKN-UPS-002", "ownerTeam": "Teknica - Continuidad Operacional" }
}
```

Errores: `400` validación (incluye el detalle campo por campo), `404` ruta desconocida,
`502` si Dataverse rechaza la creación (el envío igual queda registrado localmente para no perderlo).

### Mapeo a la entidad Lead

| Campo del formulario | Columna en Dataverse |
|---|---|
| `firstName` / `lastName` | `firstname` / `lastname` |
| `email` | `emailaddress1` |
| `phone` | `mobilephone` y `telephone1` |
| `company` | `companyname` |
| `jobTitle` | `jobtitle` |
| (generado) | `subject` = `[CÓDIGO] Línea de negocio - Empresa` |
| origen | `leadsourcecode` = 8 (Web) |
| `landingCode`, UTM, `fields`, `message` | `description`, en un bloque de trazabilidad legible |
| opcional | columnas propias declaradas en `.env` (`FIELD_LANDING_CODE`, `FIELD_UTM_SOURCE`, `FIELD_UTM_CAMPAIGN`) |

Si el entorno tiene columnas personalizadas para el origen, se declaran en `api/.env` y la API las
llena **sin cambiar una línea de código**.

---

## 5. Cómo se agrega una landing nueva

Este es el punto que suele preocupar al cliente. Son dos pasos y **ninguno toca el CRM ni la API**:

1. Agregar el bloque del nuevo origen en `landings.json` (código, marca, equipo dueño, campaña).
2. Publicar el HTML con `data-landing-code="EL-NUEVO-CODIGO"` en su formulario, cargando
   `assets/js/config.js` y `assets/js/landing.js`.

Si el código no está registrado en `landings.json`, la API **rechaza** el envío. Así no existen
landings publicadas sin dueño ni trazabilidad.

Para regenerar las 4 landings de la demo desde su especificación:

```bash
py tools/build_landings.py
```

---

## 6. Publicación en GitHub Pages

El sitio es estático, así que se puede publicar tal cual desde este repositorio
(*Settings → Pages → Deploy from branch → `main` / root*).

Con Pages **no hay backend**: al no encontrar la API, la demo responde en modo *SIMULADO* en el
navegador y lo rotula como tal (`simulateIfUnreachable` en `assets/js/config.js`). Para que las
landings publicadas escriban en Dynamics hay que desplegar la API y apuntar `apiBaseUrl` a su URL
pública (Azure Functions, App Service o Container Apps).

---

## 7. Qué tan difícil es llevarlo a producción

Lectura honesta, para conversar y ajustar con Legrand y Teknica:

- **Simple** — la integración en sí (un endpoint + OAuth2 + `POST` a Dataverse) y agregar landings
  nuevas, que es configuración y no desarrollo.
- **Medio** — campos propios por línea de negocio, anti-spam (captcha y *rate limiting*),
  deduplicación por correo o RUT, hosting de la API y dominios permitidos por CORS.
- **Lo difícil, y no es técnico** — el gobierno: nomenclatura única de campañas, dueño comercial por
  línea, SLA de primer contacto, reglas de asignación y el consentimiento de datos personales
  (Ley 21.719). Integrando dos organizaciones, es acá donde se gana o se pierde la trazabilidad.

Los tiempos que aparecen en el sitio son estimaciones preliminares de W-IT y deben validarse con el
cliente antes de comprometer un plan.

---

## 8. Seguridad y datos

- `api/.env`, cualquier secreto y `api/_data/leads.json` están en `.gitignore`.
- La demo no usa datos reales de clientes; los formularios avisan que el ambiente es de prueba.
- Los textos de consentimiento son de demostración y requieren validación legal del cliente antes
  de usarse en producción.

---

Legrand, Bticino, Teknica y Enersafe son marcas de sus respectivos titulares. Este repositorio es un
ambiente de demostración técnica de W-IT y no es un sitio oficial de esas marcas.
