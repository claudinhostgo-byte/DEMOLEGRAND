# Alcance: portal autenticado de órdenes de trabajo para clientes externos

Un sitio donde los clientes de Legrand y Teknica inician sesión con Entra ID y consultan **sus**
órdenes de trabajo de Field Service: listado, búsqueda y filtros por fecha, estado y número.

> Estimación preliminar de W-IT, sujeta a validación con el cliente. La valorización y las
> condiciones comerciales las define el equipo Comercial de W-IT.

---

## Resumen

| Escenario | Horas |
|---|---:|
| **Completo**, con tres ambientes (desarrollo, QA y producción) | **84** |
| Reducido: invitados B2B, sin vista de detalle, dos ambientes | **64** |
| Descuento si se ejecuta junto con la API de captura de leads | **−8** |

Calendario referencial del escenario completo: **4 a 6 semanas**, condicionado a las decisiones de
identidad del cliente, que suelen ser el camino crítico.

---

## Lo primero: el problema no es el login

Autenticar es la parte resuelta. Lo que hay que construir con cuidado es **la autorización**: que
el usuario de la empresa A no vea jamás una orden de la empresa B, ni siquiera manipulando la URL.

Eso obliga a tres cosas que pesan en el alcance:

1. **Un vínculo explícito entre la identidad y el cliente en Dataverse.** Un correo no basta como
   prueba de pertenencia: hay que decidir dónde vive esa relación y quién la administra.
2. **Resolver el cliente en el servidor, desde el token.** Si el filtro por cliente viaja desde el
   navegador, cualquiera lo cambia. La API tiene que deducirlo y jamás confiar en el parámetro.
3. **Probar el aislamiento explícitamente.** Una falla acá no es un error de sistema: es entregarle
   a un cliente la información de otro.

---

## Actividades: 84 horas

### Fase 1 · Diseño y decisiones — 12 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 1 | Modelo de identidad | Elegir entre invitados B2B y Entra External ID, definir el flujo de alta y baja, y qué pasa con una persona que atiende a varias empresas | 5 |
| 2 | Vínculo identidad ↔ cliente | Dónde se guarda la relación entre el usuario externo y la cuenta de Dataverse, y quién la mantiene | 4 |
| 3 | Definición funcional | Qué campos se muestran, por cuáles se busca y —sobre todo— qué **no** se expone al cliente | 3 |

### Fase 2 · Identidad — 14 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 4 | Proveedor de identidad en los tres ambientes | Registro de aplicación, flujos de usuario, dominios de respuesta y personalización mínima de la pantalla de inicio de sesión | 6 |
| 5 | Integración del inicio de sesión | Login y cierre de sesión, manejo de la sesión y su expiración, pantalla de "tu usuario no tiene acceso" | 5 |
| 6 | Alta y baja de usuarios externos | Procedimiento operativo y la interfaz mínima o el proceso documentado para ejecutarlo | 3 |

### Fase 3 · Autorización y API de consulta — 16 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 7 | Resolución del cliente en el servidor | Del token a la cuenta de Dataverse, sin confiar en nada que venga del navegador | 5 |
| 8 | Endpoint de listado | Consulta de órdenes con filtro obligatorio por cliente, búsqueda, filtros por fecha y estado, y paginación | 7 |
| 9 | Endpoint de detalle | Una orden puntual, validando que pertenezca al cliente del usuario antes de devolverla | 4 |

### Fase 4 · Interfaz — 12 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 10 | Listado y búsqueda | Tabla con filtros por fecha, estado y número, y buscador | 7 |
| 11 | Vista de detalle | Ficha de la orden con su información y su historial visible para el cliente | 3 |
| 12 | Estados vacíos, errores y responsive | Sin resultados, sin acceso, error de servicio, y comportamiento en móvil | 2 |

### Fase 5 · Infraestructura y promoción — 8 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 13 | Hosting en los tres ambientes | Sitio y API, dominios, certificados y configuración por ambiente | 5 |
| 14 | Pipeline de promoción | Tres etapas con aprobación, incluyendo la configuración de identidad propia de cada ambiente | 3 |

### Fase 6 · Pruebas — 12 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 15 | Funcionales | Listado, búsqueda, filtros, paginación y detalle | 4 |
| 16 | **Aislamiento entre clientes** | Verificar que el usuario de una empresa no accede a órdenes de otra, ni por la interfaz ni forzando identificadores en la API | 5 |
| 17 | Sesión y accesos | Expiración, cierre de sesión, acceso sin sesión, usuario autenticado pero sin cliente asociado | 3 |

### Fase 7 · Cierre — 10 h

| # | Actividad | Qué incluye | Horas |
|---|---|---|---:|
| 18 | Documentación | Modelo de acceso, guía de alta y baja de usuarios externos, runbook de operación | 4 |
| 19 | Traspaso | Capacitación a quien vaya a administrar los accesos | 3 |
| 20 | Gestión y coordinación | Planificación, avances y control de cambios | 3 |

---

## Dos decisiones del cliente que cambian el número

### Cómo entran los externos

| Opción | Cuándo conviene | Efecto |
|---|---|---|
| **Invitados B2B** en el tenant corporativo | Pocos clientes, con su propia cuenta Microsoft corporativa | Más simple y más barato de construir. Cada invitación es un objeto en el directorio del cliente |
| **Entra External ID** | Muchos clientes, con autoservicio de registro y recuperación de clave | Más trabajo inicial y costo por usuario activo, pero escala sin tocar el directorio corporativo |

La demo actual usa el proveedor integrado de Static Web Apps, que **acepta cualquier cuenta
Microsoft del mundo**: sirve para demostrar, no para producción.

### Licenciamiento

Los usuarios externos no entran a Dynamics: consultan a través de la API, que se autentica con su
propio usuario de aplicación. Aun así, **el escenario de acceso de terceros a datos de Dynamics
mediante una aplicación propia debe validarse con Microsoft o con el área de licenciamiento antes
de comprometerlo**, junto con el costo por usuario activo del proveedor de identidad que se elija.
No lo cerramos nosotros: lo confirma el equipo Comercial.

---

## Escenario reducido: 64 horas

Se llega ahí tomando estas decisiones, todas defendibles si el universo de clientes es acotado:

- **Invitados B2B** en vez de Entra External ID: −4 h.
- **Sin vista de detalle**: toda la información en el listado expandible: −3 h.
- **Sin interfaz de administración**: las altas y bajas se gestionan con un procedimiento manual
  documentado: −2 h.
- **Dos ambientes** en vez de tres: −5 h.
- Interfaz más sobria, reutilizando los componentes de la demo: −6 h.

Lo que **no** recortaría en ninguna versión son las 5 horas de pruebas de aislamiento entre
clientes. Es la única actividad del proyecto cuyo fallo se le explica al cliente final, no a TI.

---

## Si se ejecuta junto con la API de captura de leads: −8 horas

Se comparten la infraestructura, el pipeline de promoción, la configuración por ambiente y el
usuario de aplicación contra Dataverse. Conviene proponerlos como un solo proyecto de dos entregas
en vez de dos proyectos separados.

| Combinación | Horas |
|---|---:|
| API de captura de leads (tres ambientes) | 62 |
| Portal de órdenes de trabajo (tres ambientes) | 84 |
| Ejecutados juntos | **138** |

---

## Qué NO incluye

- Que el cliente pueda **crear o modificar** órdenes de trabajo: esto es solo consulta.
- Adjuntos, fotos de terreno o documentos asociados a la orden.
- Firma del cliente en terreno, encuestas de satisfacción o pagos.
- Notificaciones por correo cuando cambia el estado de una orden.
- Aplicación móvil: el sitio es responsive, pero no es una app.
- Migración de usuarios externos desde otro portal existente.

---

## Supuestos

- Los datos de Field Service ya existen y son confiables: las órdenes tienen su cuenta de cliente
  correctamente asignada. Si no la tienen, ordenar eso es un trabajo previo y aparte.
- El cliente define quién administra los accesos externos y con qué criterio.
- Existen los tres entornos de Dynamics y la suscripción Azure, con permisos al inicio.
- El texto legal del portal y su política de privacidad los provee y valida el cliente.

---

## Riesgo principal

Que las órdenes de trabajo en Dynamics no tengan bien asignada la cuenta del cliente. El portal
filtra por ese vínculo: si el dato está sucio, un cliente ve órdenes que no le corresponden o no ve
las suyas. **Conviene revisar la calidad de ese campo antes de comprometer el proyecto**, y no
después de la primera queja.
