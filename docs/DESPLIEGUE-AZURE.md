# Despliegue en Azure Static Web Apps

Static Web Apps publica el sitio **y** la API en el mismo dominio: la ruta `/api` queda enrutada a
las *managed functions* sin necesidad de reglas de CORS. Por eso `apiBaseUrl` en
`assets/js/config.js` se deja vacío: el front-end llama a `/api/leads` en su propio origen.

## 1. Valores del asistente de creación

| Campo | Valor |
|---|---|
| Origen | GitHub · `claudinhostgo-byte/DEMOLEGRAND` · rama `main` |
| Valores preestablecidos de compilación | **Custom** |
| Ubicación de la aplicación | `/` |
| **Ubicación de la API** | `api` |
| Ubicación de salida | *(vacío)* — el sitio es estático, no hay build |
| Plan | **Gratis** alcanza para la demo (incluye managed functions y dominio propio con SSL). Estándar aporta SLA, *bring your own functions* y private endpoints, con costo mensual por app |

> Si creaste la app **antes** de que existiera la Functions app en el repo y dejaste la API vacía,
> no hay que rehacer nada: basta editar el workflow (paso 2).

## 2. Workflow de GitHub Actions

Al conectar el repositorio, Azure crea `.github/workflows/azure-static-web-apps-*.yml` y hace push a
`main`. Verifica que tenga estas tres líneas:

```yaml
          app_location: "/"
          api_location: "api"
          output_location: ""
```

Si `api_location` quedó vacío, cámbialo a `api`, haz commit y el propio push dispara el despliegue.

## 3. Runtime de la API

`staticwebapp.config.json` ya fija el runtime:

```json
"platform": { "apiRuntime": "python:3.10" }
```

Las managed functions de Static Web Apps admiten Python 3.8, 3.9 y 3.10 (además de Node.js y .NET).
Si Azure retira 3.10, se baja a 3.9 en esa misma línea o se pasa a *bring your own functions*.

## 4. Configuración de la aplicación (los secretos NO van en el repo)

En el portal: **Static Web App → Configuración → Configuración de la aplicación**. Agregar:

| Nombre | Valor | Obligatorio |
|---|---|---|
| `LEAD_MODE` | `mock` o `dataverse` | Sí |
| `DV_URL` | `https://<entorno>.crm2.dynamics.com` | Solo en modo `dataverse` |
| `DV_TENANT_ID` | Id. del directorio (inquilino) | Solo en modo `dataverse` |
| `DV_CLIENT_ID` | Id. de aplicación del App Registration | Solo en modo `dataverse` |
| `DV_CLIENT_SECRET` | Secreto del App Registration | Solo en modo `dataverse` |
| `DV_API_VERSION` | `v9.2` | No (valor por defecto) |
| `FIELD_LANDING_CODE` | Nombre lógico de la columna de origen, si existe | No |
| `FIELD_UTM_SOURCE` / `FIELD_UTM_CAMPAIGN` | Columnas de campaña, si existen | No |

Recomendación: **partir en `mock`**, verificar que el sitio y la API responden, y recién ahí pasar a
`dataverse` con el entorno confirmado. El `scope` del token lleva la URL del entorno: ahí se decide
en qué Dynamics caen los leads.

> Las managed functions no soportan referencias a Key Vault ni identidad administrada. Si el cliente
> exige custodia en Key Vault, hay que pasar a *bring your own functions* (plan Estándar) — está
> contemplado en la estimación como parte del bloque de Azure.

## 5. Verificación después del despliegue

```bash
curl https://<tu-app>.azurestaticapps.net/api/health
```

Debe responder `"ok": true`, el modo activo y los cuatro códigos de landing. Luego:

1. Abrir el sitio y confirmar que el chip diga **API en línea**.
2. Enviar un formulario de prueba y revisar que la respuesta traiga `leadId`.
3. En modo `dataverse`, abrir el `recordUrl` que devuelve la API: lleva al lead en el CRM.

## 6. Nota sobre la consola de leads en Azure

En modo `mock` sobre Azure, los envíos quedan en memoria del proceso (el sistema de archivos de la
Function es de solo lectura), así que `admin.html` puede mostrar menos registros de los esperados si
la instancia se recicla. Es un artificio de la demo: en modo `dataverse` los leads viven en Dynamics
y esa pantalla se reemplaza por la vista de Clientes potenciales del CRM.

## 7. Qué pasa con GitHub Pages

Sigue sirviendo como espejo estático del sitio, pero **sin backend**: al no encontrar la API, la demo
responde en modo *SIMULADO* en el navegador y lo rotula como tal. Para una demo con leads reales,
usar la URL de Static Web Apps.
