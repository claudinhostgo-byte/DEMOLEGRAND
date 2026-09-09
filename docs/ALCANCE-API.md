# Alcance: API de captura de leads en Azure

Implementar **solo la API**: un endpoint en Azure que reciba los formularios de varias landing
pages y cree el lead en Dynamics 365 con su origen trazable. Las landings las construye el cliente
o su agencia; W-IT entrega el contrato de datos y acompaña la conexión.

> Estimación preliminar de W-IT, sujeta a validación con el cliente. La valorización y las
> condiciones comerciales las define el equipo Comercial de W-IT.

---

## Total: 48 horas

Estimadas **trabajando con asistencia de IA**, y partiendo de la implementación de referencia que
ya está funcionando y verificada en la demo.

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 1 | Contrato de la API | Payload común, catálogo de códigos de origen, campos obligatorios y propios por línea | 3 |
| 2 | Habilitación de identidad | App Registration en Entra ID, Application User en el entorno y rol de seguridad mínimo | 3 |
| 3 | Modelo de origen en Dataverse | Columnas de código de landing, campaña y UTM, más la vista de leads que las muestra | 3 |
| 4 | Endpoint de captura | Validación de campos y consentimiento, mapeo a la entidad Lead, manejo de errores y reintento ante fallas transitorias | 8 |
| 5 | Catálogo configurable | Dar de alta una landing nueva sin desarrollo ni despliegue | 2 |
| 6 | Protección básica | Captcha, *rate limiting* por IP y CORS restringido a los dominios autorizados | 5 |
| 7 | Infraestructura Azure | Function App en plan consumo, dominio, TLS y configuración de aplicación con los secretos | 5 |
| 8 | Observabilidad mínima | Application Insights con traza por envío y una alerta cuando la creación falla | 2 |
| 9 | Despliegue automatizado | Pipeline desde el repositorio hacia un entorno productivo | 2 |
| 10 | Pruebas funcionales | Casos válidos, campos faltantes, formatos inválidos, acentos y ñ, códigos de origen no registrados | 4 |
| 11 | Prueba integrada | Una landing real del cliente conectada extremo a extremo, verificando el lead en el CRM | 3 |
| 12 | Documentación | Contrato para quien construya las landings, guía de alta de una landing nueva y runbook de operación | 3 |
| 13 | Traspaso | Sesión con TI y marketing | 2 |
| 14 | Gestión y coordinación | Planificación, avances y control de cambios | 3 |
| | | **Total** | **48** |

Calendario referencial: **2 a 3 semanas**, condicionado a la disponibilidad de los entornos y de
las personas del cliente para validar.

---

## Qué aporta trabajar con IA, y qué no

**Se comprime**: escribir el endpoint y sus validaciones, generar la batería de casos de prueba,
redactar el contrato y el runbook, y armar los scripts de despliegue. Ahí es donde bajan las horas
respecto de una estimación tradicional.

**No se comprime**, y por eso sigue pesando en el total:

- Esperar accesos: Application User en el entorno, permisos sobre la suscripción Azure.
- Las decisiones de negocio: qué campos se capturan, quién es dueño de cada lead, qué dice el texto
  de consentimiento.
- La validación del cliente y las pruebas con su gente.
- La revisión humana de lo que la IA produce. Está incluida en las horas de cada actividad: nada
  se entrega sin que un consultor lo lea y lo pruebe.

---

## Qué NO incluye

- Diseño, maquetación y publicación de las landings.
- Deduplicación de leads y reglas de duplicados en el CRM.
- Ruteo y asignación automática por línea de negocio.
- Reportería o tableros de atribución.
- Key Vault, API Management y arquitecturas de red avanzadas.
- Migración de leads históricos.
- Licenciamiento de Dynamics 365 y consumo de la suscripción Azure.

---

## Supuestos

- Un entorno productivo de Dynamics y uno de pruebas, ambos disponibles al inicio.
- Entidad Lead estándar, sin plugins ni procesos personalizados que interfieran.
- Hasta seis landings iniciales con el mismo contrato de datos.
- Las landings pueden enviar un `POST` con JSON y se publican en dominios conocidos.
- El texto de consentimiento lo entrega y valida el área legal del cliente.

Si algo de esto cambia, cambia la estimación.

---

## Qué necesitamos del cliente

| Cuándo | Qué |
|---|---|
| Al inicio | Acceso al entorno Dynamics y a la suscripción Azure, con permisos para crear los recursos |
| Al inicio | Definición de las líneas de negocio y su dueño comercial |
| Antes de las pruebas | Una landing real publicada, o al menos su dominio, para autorizarlo en CORS |
| Antes de salir a producción | Texto de consentimiento validado por su área legal |

---

## Entregables

1. API desplegada en Azure, operativa y monitoreada.
2. Código fuente en el repositorio, con el pipeline de despliegue.
3. Columnas de origen y vista de leads configuradas en Dynamics.
4. Documento de contrato de la API, con ejemplos listos para copiar.
5. Guía de alta de una landing nueva y runbook de operación.
6. Sesión de traspaso al equipo del cliente.

---

## Riesgo que conviene declarar

Cortar bajo estas 48 horas obliga a sacar la **protección básica** (actividad 6), y ese es el
recorte que no recomiendo: un formulario público sin captcha ni *rate limiting* llena el CRM de
basura en semanas, y limpiarlo después cuesta más que las cinco horas que ahorra. Observabilidad y
pipeline sí se pueden postergar a una fase 2 si el presupuesto aprieta, asumiendo que nadie se
entera si la API deja de crear leads y que cada cambio se sube a mano.
