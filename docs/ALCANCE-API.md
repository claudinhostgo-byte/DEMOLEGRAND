# Alcance: API de captura de leads en Azure

Implementar **solo la API**: un endpoint en Azure que reciba los formularios de varias landing
pages y cree el lead en Dynamics 365 con su origen trazable. Las landings las construye el cliente
o su agencia; W-IT entrega el contrato de datos y acompaña la conexión.

> Estimación preliminar de W-IT, sujeta a validación con el cliente. La valorización y las
> condiciones comerciales las define el equipo Comercial de W-IT.

---

## Resumen

| Escenario | Ambientes | Horas |
|---|---|---:|
| **Base** | 1 ambiente de API, Dynamics productivo más uno de pruebas | **48** |
| **Con tres ambientes** (recomendado si el cliente ya opera así) | Desarrollo, QA y producción, en Azure y en Dynamics | **62** |
| Con tres ambientes, versión recortada | Igual, pero promoción manual documentada en vez de automatizada | **54** |

---

## Base: 48 horas

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

## Módulo de tres ambientes: +14 horas

Trabajar con desarrollo, QA y producción no encarece la API —el código es el mismo— sino **mover
el modelo de datos entre entornos y repetir las pruebas**. Eso es lo que se agrega:

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 15 | Usuario de aplicación en los tres entornos | Alta del Application User y su rol de seguridad en desarrollo, QA y producción | 2 |
| 16 | Solución de Dataverse | Empaquetar las columnas de origen y la vista como solución, y el ciclo de exportar e importar entre los tres entornos | 3 |
| 17 | Infraestructura parametrizada | Un script de despliegue por parámetros: crear el tercer ambiente cuesta minutos, no horas | 3 |
| 18 | Pipeline de promoción | Tres etapas encadenadas, con aprobación antes de producción y configuración propia por ambiente | 3 |
| 19 | Pruebas por ambiente | La misma batería ejecutada en QA y una verificación de humo en producción | 2 |
| 20 | Matriz de ambientes | Qué apunta a qué, quién aprueba cada promoción y cómo se revierte | 1 |
| | | **Subtotal** | **14** |

**Total con tres ambientes: 62 horas.** Calendario referencial: 3 a 4 semanas.

### Si 50 horas es un tope firme

No alcanza para tres ambientes bien hechos. Hay dos formas de acercarse, en orden de lo que menos
duele:

1. **Promoción manual documentada** en vez de automatizada: se sacan las actividades 17 y 18 y se
   entrega un procedimiento paso a paso. Quedan **54 horas**. El costo es que cada paso a
   producción depende de que alguien siga la guía sin equivocarse.
2. **Dos ambientes en vez de tres** (QA y producción; el desarrollo se corre local contra el
   Dynamics de desarrollo). Quedan cerca de **52 horas**, y es lo que yo elegiría si el
   presupuesto no se mueve: es mejor tener dos ambientes bien gobernados que tres a medias.

Lo que **no** recomiendo recortar para llegar a 50 es la protección básica ni las pruebas: son las
dos cosas que se pagan caro después.

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

- Los entornos de Dynamics existen y están disponibles al inicio: dos en el alcance base
  (producción y pruebas), tres si se toma el módulo de ambientes.
- Las licencias y la capacidad de los entornos las provee el cliente.
- Entidad Lead estándar, sin plugins ni procesos personalizados que interfieran.
- Hasta seis landings iniciales con el mismo contrato de datos.
- Las landings pueden enviar un `POST` con JSON y se publican en dominios conocidos.
- El texto de consentimiento lo entrega y valida el área legal del cliente.

Si algo de esto cambia, cambia la estimación.

---

## Qué necesitamos del cliente

| Cuándo | Qué |
|---|---|
| Al inicio | Acceso a los entornos Dynamics y a la suscripción Azure, con permisos para crear los recursos en cada uno |
| Al inicio | Definición de quién aprueba el paso a producción, si se toma el módulo de tres ambientes |
| Al inicio | Definición de las líneas de negocio y su dueño comercial |
| Antes de las pruebas | Una landing real publicada, o al menos su dominio, para autorizarlo en CORS |
| Antes de salir a producción | Texto de consentimiento validado por su área legal |

---

## Entregables

1. API desplegada en Azure, operativa y monitoreada.
2. Código fuente en el repositorio, con el pipeline de despliegue.
3. Columnas de origen y vista de leads configuradas en Dynamics, empaquetadas como solución si se
   toma el módulo de ambientes.
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
