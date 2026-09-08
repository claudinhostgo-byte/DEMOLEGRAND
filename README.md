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
| **Lógica de la API** | `api/lead_core.py` | Validación, mapeo a la entidad Lead y escritura en Dataverse. Un solo lugar, sin lógica duplicada |
| **API en Azure** | `api/leads/`, `api/health/`, `api/landings/` | Azure Functions (Python) para Static Web Apps: `/api/leads` es el **único** endpoint que usan las 4 landings |
| Servidor local | `tools/dev_server.py` | Sirve el sitio y la misma API en `localhost:8080`, importando `lead_core` |
| Catálogo de orígenes | `api/landings.json` | Fuente única de verdad: códigos, marcas, equipos y campañas. Viaja con la API y se expone en `/api/landings` |
| Configuración de Azure | `staticwebapp.config.json` | Runtime de la API, cabeceras de seguridad y rutas |
| Consola de leads | `admin.html` | Muestra lo que llegó por la API (en producción, esto es la vista de Clientes potenciales del CRM) |
| Generador de landings | `tools/build_landings.py` | Regenera las 4 landings desde una especificación corta |

Las cuatro líneas de negocio corresponden a las que el grupo opera en Chile tras la adquisición de
Teknica y Enersafe por parte de Legrand Chile: infraestructura digital y data centers, respaldo y
calidad de energía, distribución de energía para industria y minería, y sector terciario con Bticino.

---

## 2. Cómo levantar la demo

Requisito único: **Python 3.8+** (la API usa solo biblioteca estándar, sin `pip install`).

```bash
py tools/dev_server.py
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

1. En local: copiar `api/.env.example` a `api/.env` y completar `DV_URL`, `DV_TENANT_ID`,
   `DV_CLIENT_ID`, `DV_CLIENT_SECRET`; en Azure: las mismas claves en la *Configuración de la
   aplicación* de Static Web Apps (ver [docs/DESPLIEGUE-AZURE.md](docs/DESPLIEGUE-AZURE.md)).
2. Cambiar `LEAD_MODE=dataverse`.
3. Reiniciar la API (en Azure basta guardar la configuración).

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

## 6. Publicación

### Azure Static Web Apps (recomendado)

El sitio y la API se publican juntos: Static Web Apps enruta `/api` a las *managed functions*, así
que no hay CORS que configurar ni `apiBaseUrl` que tocar. Valores del asistente:

| Campo | Valor |
|---|---|
| Ubicación de la aplicación | `/` |
| Ubicación de la API | `api` |
| Ubicación de salida | *(vacío)* |

El paso a paso completo —workflow, runtime de Python, configuración de la aplicación y verificación—
está en **[docs/DESPLIEGUE-AZURE.md](docs/DESPLIEGUE-AZURE.md)**.

### GitHub Pages (espejo estático)

Sirve para mostrar el sitio sin backend (*Settings → Pages → Deploy from branch → `main` / root*).
Al no encontrar la API, la demo responde en modo *SIMULADO* en el navegador y lo rotula como tal
(`simulateIfUnreachable` en `assets/js/config.js`).

## 7. Qué tan difícil es llevarlo a producción, y qué haría W-IT

Lectura honesta de la dificultad:

- **Simple** — la integración en sí (un endpoint + OAuth2 + `POST` a Dataverse) y agregar landings
  nuevas, que es configuración y no desarrollo.
- **Medio** — campos propios por línea de negocio, anti-spam (captcha y *rate limiting*),
  deduplicación por correo o RUT, hosting de la API y dominios permitidos por CORS.
- **Lo difícil, y no es técnico** — el gobierno: nomenclatura única de campañas, dueño comercial por
  línea, SLA de primer contacto, reglas de asignación y el consentimiento de datos personales
  (Ley 21.719). Integrando dos organizaciones, es acá donde se gana o se pierde la trazabilidad.

### Alcance propuesto de W-IT: la API y los componentes en Azure

Las landings las produce Legrand con su equipo o su agencia; nosotros entregamos el contrato de
datos y acompañamos la conexión.

| Bloque | Componente | Qué incluye | Horas |
|---|---|---|---:|
| **1. Diseño y habilitación** | Diseño de la solución y contrato de la API | Payload común, catálogo de orígenes, criterios de validación | 8 |
| | Habilitación de identidad | App Registration en Entra ID, Application User y rol de seguridad en Dataverse | 4 |
| | Modelo de datos en Dynamics 365 | Columnas de origen, catálogo de campañas, vista de leads por landing | 6 |
| | | *Subtotal* | **18** |
| **2. API única de captura** | Endpoint y validaciones | Un endpoint para todas las landings, validación de campos, consentimiento y manejo de errores | 16 |
| | Mapeo a la entidad Lead | Traducción al modelo de Dataverse y bloque de trazabilidad del origen | 10 |
| | Catálogo de orígenes configurable | Alta de landings nuevas sin desarrollo ni despliegue | 6 |
| | Anti-spam | Captcha y *rate limiting* por IP y por origen | 6 |
| | Deduplicación | Búsqueda de duplicados por correo o RUT antes de crear el lead | 8 |
| | | *Subtotal* | **46** |
| **3. Componentes en Azure** | Azure Function App | Function App y plan de hosting, entornos de desarrollo y producción | 10 |
| | Key Vault e identidad administrada | Custodia de secretos sin credenciales en el código | 6 |
| | Dominio, TLS y CORS | Dominio propio, certificado y dominios autorizados a llamar la API | 6 |
| | Application Insights | Trazas, alertas por error y tablero de salud de la API | 8 |
| | Pipeline de despliegue | CI/CD en GitHub Actions o Azure DevOps hacia ambos entornos | 8 |
| | | *Subtotal* | **38** |
| **4. Pruebas y traspaso** | Pruebas integradas | Casos de validación, errores, carga básica y reintentos | 8 |
| | UAT con landings piloto | Dos landings reales conectadas junto al equipo de marketing | 8 |
| | Documentación | Contrato de la API y guía de alta de nuevas landings | 6 |
| | Traspaso al equipo | Sesión de capacitación a TI y marketing | 6 |
| | | *Subtotal* | **28** |
| **5. Gestión** | Gestión y coordinación | Planificación, reuniones de avance y control de cambios (≈10%) | 13 |
| | | **Total estimado** | **143 h** |

Referencia de calendario: con una dedicación normal, el alcance se ejecuta en torno a **4 a 6
semanas**, condicionado a la disponibilidad de los entornos y a decisiones comerciales que no
dependen de W-IT.

### Opcionales, se cotizan aparte

| Opcional | Horas |
|---|---:|
| Taller de gobierno del origen: nomenclatura UTM, dueños y SLA | 8 |
| Componente JS de referencia y apoyo a la agencia o CMS | 16 |
| Ruteo y asignación automática por línea de negocio | 16 |
| Tablero de atribución en Power BI | 24 |
| Integración con Customer Insights – Journeys | Requiere levantamiento |

### Fuera del alcance de W-IT (queda en Legrand y Teknica)

- Diseño, maquetación y publicación de las landings en su CMS o con su agencia.
- Contenido, pauta de campañas y presupuesto de medios.
- Textos legales, política de privacidad y validación del consentimiento por su área legal.
- Definición de dueños comerciales por línea, colas y SLA de primer contacto.
- Licenciamiento de Dynamics 365 y consumo de la suscripción Azure.
- Migración de leads históricos.

### Supuestos de la estimación

Un entorno productivo y uno de pruebas; hasta seis landings iniciales con el mismo contrato de
datos; entidad Lead estándar sin procesos personalizados adicionales; landings capaces de enviar un
`POST` JSON. Si algo de esto cambia, cambia la estimación.

> Las horas son una **estimación preliminar de W-IT** y deben validarse con Legrand y Teknica antes
> de comprometer un plan. La valorización y las condiciones comerciales las define el equipo
> Comercial de W-IT.

## 8. Seguridad y datos

- `api/.env`, cualquier secreto y `api/_data/leads.json` están en `.gitignore`.
- La demo no usa datos reales de clientes; los formularios avisan que el ambiente es de prueba.
- Los textos de consentimiento son de demostración y requieren validación legal del cliente antes
  de usarse en producción.

---

Legrand, Bticino, Teknica y Enersafe son marcas de sus respectivos titulares. Este repositorio es un
ambiente de demostración técnica de W-IT y no es un sitio oficial de esas marcas.
