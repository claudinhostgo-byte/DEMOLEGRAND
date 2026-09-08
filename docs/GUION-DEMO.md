# Guion de la demo — 12 a 15 minutos

Objetivo de la reunión: que Legrand y Teknica entiendan **cómo funciona** la captura de leads desde
varias landings hacia un mismo CRM y **qué implica** implementarlo. No es una demo de producto: es
una demo de arquitectura y de gobierno del dato.

## Antes de empezar

1. Levantar la demo: doble clic en `run-demo.cmd` (o `py api/lead_api.py`).
2. Abrir <http://localhost:8080/> y confirmar que el chip diga **API en línea · Modo MOCK**.
3. Vaciar leads previos si quieres partir limpio: borrar `api/_data/leads.json`.
4. Tener abierta en otra pestaña la consola: <http://localhost:8080/admin.html>.
5. Si vas a mostrar leads reales en Dynamics, **confirmar antes el entorno** y cambiar
   `LEAD_MODE=dataverse` en `api/.env`.

## Minuto a minuto

**1. El problema (1 min).** Cuatro líneas de negocio, cuatro públicos distintos, cuatro landings con
identidad propia. La pregunta del cliente no es si se puede, sino cómo no perder de vista de dónde
vino cada lead.

**2. El sitio maestro (2 min).** Mostrar la portada. Señalar que cada landing tiene un **código de
origen** visible (`LGD-DC-001`, `TKN-UPS-002`, `LGD-IND-003`, `LGD-RET-004`) y que ese código es el
que amarra todo el flujo.

**3. Simular una campaña (1 min).** En "Cómo funciona", hacer clic en *LinkedIn pagado → UPS*.
Mostrar en la landing el panel de **origen capturado**: los `utm_*` viajan solos, sin que el usuario
haga nada. Ese es el dato que hoy normalmente se pierde.

**4. Llenar el formulario (3 min).** Completar la landing de Teknica con datos de prueba. Antes de
apretar enviar, mostrar el panel de trazabilidad: **este es el JSON que sale de la landing**.
Enviar. Mostrar la respuesta: `leadid`, código de origen, equipo dueño.

**5. El punto clave (2 min).** Repetir el envío en otra landing (por ejemplo Retail). Hacer notar
que el formulario es distinto, los campos propios son distintos… **y el endpoint es el mismo**.
Una API, cuatro landings, un solo lugar donde se mantiene el mapeo.

**6. La consola (2 min).** Abrir `admin.html`. Los dos leads con su origen, su campaña y sus campos
propios. En producción esta pantalla es simplemente la vista de Clientes potenciales de Dynamics, y
el enlace abre el registro real.

**7. La dificultad (3 min).** Volver a la portada, sección *¿Qué tan difícil es implementarlo de
verdad?*. Ser explícito: la integración es la parte fácil; lo que toma tiempo es acordar el catálogo
de orígenes, los dueños comerciales, el SLA y el consentimiento. Aquí es donde W-IT aporta como
consultor, no solo como desarrollador.

## Preguntas que probablemente aparezcan

**¿Y si mañana quiero 10 landings más?** Se registra el código en el catálogo y se publica el HTML.
No se toca la API ni el CRM. Se puede mostrar en vivo agregando un bloque a `landings.json`.

**¿Sirve si las landings viven en nuestro CMS o en HubSpot/WordPress?** Sí. La landing solo necesita
poder hacer un `POST` con su código de origen. Lo que hay que definir es el dominio permitido en la
API.

**¿Podemos usar Power Pages o formularios de marketing en vez de esto?** Sí, y en varios escenarios
conviene. La diferencia es el control: con una API propia se controla la validación, la
deduplicación y el mapeo antes de que el dato entre al CRM. Es una decisión a evaluar caso a caso.

**¿Cómo evitamos spam?** Captcha, *rate limiting* por IP y reglas de duplicados en el CRM. No está
en la demo a propósito, para no esconder que es trabajo adicional.

**¿Y la protección de datos?** El consentimiento se pide explícitamente y queda registrado con el
lead. El texto definitivo lo debe validar el área legal del cliente (Ley 21.719).

## Qué NO prometer en la reunión

- Plazos o precios cerrados: los esfuerzos que muestra el sitio son referenciales y deben validarse.
- Que la demo es el producto final: es un ambiente de demostración, sin captcha, sin deduplicación y
  sin las reglas de asignación reales.
- Integraciones con sistemas del cliente que todavía no hemos revisado.
