# Contrato de API — mensajes y respuestas

Versión de aplicación: `0.1.0`. **Contrato implementado:** interfaces, recepción, validación y generación de respuestas con Azure OpenAI. La clasificación estructurada descrita en el [diseño](diseno-pasos-1-2.md) pertenece al siguiente hito.

## Entrada

`POST /api/agent/messages`, con `Content-Type: application/json` y cuerpo UTF-8. Se admite el parámetro `charset=utf-8`. No se admiten cuerpos comprimidos; `Content-Encoding` debe estar ausente o ser `identity`.

| Campo | Tipo | Regla |
| --- | --- | --- |
| `message` | string | Obligatorio; 1–4.000 caracteres después de normalizar |
| `locale_hint` | string | Opcional; `es`, `en`, `pt`; predeterminado `es` |

El cuerpo debe ser un objeto JSON sin campos adicionales ni claves duplicadas, incluidas las claves de objetos anidados. No se convierten otros tipos en texto. JSON mal formado, UTF-8 inválido y constantes no estándar como `NaN` o `Infinity` producen `400`.

El texto se normaliza a NFC, se unifican saltos de línea a `\n` y se eliminan espacios exteriores. Se conservan acentos, mayúsculas, código, tabulaciones y saltos de línea interiores. Se rechaza texto sin contenido visible y sustitutos Unicode inválidos. La longitud se comprueba después de normalizar; esta operación no modifica identidad ni permisos y no constituye moderación de contenido.

El máximo del cuerpo es 16 KiB por defecto, medidos mientras se recibe y antes de parsearlo. Funciona sin `Content-Length` y con cuerpos fragmentados; el texto y su representación JSON completa cuentan para ese límite.

La API admite únicamente acceso anónimo. Cualquier cabecera `Authorization`, incluso vacía, produce `401 INVALID_CREDENTIALS`. No existe validación real de tokens en esta entrega.

El cliente no declara `principal`, `permissions`, `request_id`, `channel` ni `received_at`. El servidor establece un principal `anonymous` con `public:read`, un UUID nuevo, fecha UTC y canal `api`. Streamlit consume este mismo endpoint; no introduce un canal o permiso mediante cabeceras del cliente.

## Respuesta

HTTP `200` indica que el mensaje fue validado y procesado durante la petición. No implica almacenamiento, encolado, clasificación estructurada ni creación de tickets.

| Campo | Tipo | Origen |
| --- | --- | --- |
| `request_id` | UUID string | Generado por el servidor; el del cliente se ignora |
| `status` | string | `answered` con Azure; `received` en el modo local sin modelo |
| `received_at` | datetime string | Fecha UTC del contexto validado |
| `user_message` | string | Respuesta del modelo o confirmación local en el idioma solicitado |

Petición:

```json
{"message":"No puedo iniciar sesión desde ayer.","locale_hint":"es"}
```

Respuesta ilustrativa:

```json
{
  "request_id": "01ecf7d9-f22d-4f8d-bbdd-60ef64a336d2",
  "status": "answered",
  "received_at": "2026-09-14T20:00:00Z",
  "user_message": "Prueba restablecer tu contraseña y confirma el mensaje de error que aparece."
}
```

El backend mantiene las instrucciones del sistema separadas del texto del usuario, limita la salida y no entrega herramientas ni credenciales al modelo. Si el proveedor agota el tiempo, no está disponible o devuelve una salida vacía/incompleta, se responde con un error temporal seguro.

Todas las respuestas incluyen `X-Request-ID` generado en el servidor y `Cache-Control: no-store`, también los errores anteriores al parseo. El identificador de la cabecera coincide con el del cuerpo cuando existe el sobre JSON.

## Errores

Las respuestas de error no incluyen el cuerpo recibido ni valores inválidos:

```json
{
  "request_id": "72056fbd-87c1-452a-808c-d4b3980139bc",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Envía un mensaje visible de 1 a 4.000 caracteres y un idioma válido (es, en o pt). Solo se admiten los campos message y locale_hint.",
    "retryable": false
  }
}
```

| HTTP | Código | Caso | `retryable` |
| --- | --- | --- | --- |
| `400` | `MALFORMED_JSON` | JSON inválido, UTF-8 inválido o claves duplicadas | false |
| `401` | `INVALID_CREDENTIALS` | Cabecera de credenciales presente | false |
| `413` | `BODY_TOO_LARGE` | Cuerpo excede el límite configurado | false |
| `415` | `UNSUPPORTED_MEDIA_TYPE` | Tipo de contenido no admitido | false |
| `415` | `UNSUPPORTED_CONTENT_ENCODING` | Cuerpo comprimido | false |
| `422` | `INVALID_REQUEST` | Tipo, longitud, contenido visible, idioma o campos incorrectos | false |
| `429` | `RATE_LIMITED` | Cuota por IP excedida | true |
| `500` | `INTERNAL_ERROR` | Fallo interno sin detalles ni trazas | true |
| `502` | `MODEL_INVALID_RESPONSE` | Azure devolvió una salida vacía, incompleta o excesiva | true |
| `503` | `MODEL_UNAVAILABLE` | No se pudo conectar o Azure rechazó la llamada | true |
| `504` | `MODEL_TIMEOUT` | La llamada al modelo agotó el plazo configurado | true |

Los errores se muestran en español. Una ruta o método inexistente usa su estado HTTP (`404` o `405`) y código `HTTP_ERROR`.

`401` incluye `WWW-Authenticate: Bearer`. `429` incluye `Retry-After` en segundos, calculado a partir de la ventana deslizante. El cliente Streamlit muestra el error y no reintenta automáticamente.

## Cuota y orden de comprobación

Por defecto se permiten 10 solicitudes por IP del transporte en una ventana deslizante de 60 segundos. Se usa el reloj monotónico y un contador en memoria por proceso. Los comandos de ejecución desactivan la interpretación de cabeceras de proxy en Uvicorn; la aplicación no usa `X-Forwarded-For` ni `Forwarded` para calcular la cuota.

Orden: reservar cuota, rechazar credenciales presentadas, comprobar tipo y codificación, recibir el cuerpo con límite, parsear JSON, validar y normalizar, crear contexto, llamar a Azure OpenAI y devolver la respuesta. Las solicitudes inválidas consumen cuota. Salud y documentación no consumen cuota de mensajes.

Todos los usuarios de un mismo servidor Streamlit comparten la IP de ese servidor. Reiniciar el backend reinicia los contadores. Varios procesos o un despliegue distribuido requerirán un limitador compartido y una estrategia de identidad/proxy.

## Servicio y documentación

- `GET /health`: HTTP `200`, `{"status":"ok","response_mode":"azure_openai"}` cuando el modelo está habilitado; no hace una llamada facturable.
- `GET /docs`: documentación interactiva.
- `GET /openapi.json`: esquemas de entrada estricta, recepción y errores.

## Contrato futuro de clasificación

`intent`, `entities`, `decision`, `reason_code` y `policy_version` no se devuelven actualmente. Su incorporación se hará junto con el clasificador y evaluador de políticas descritos en el diseño, con revisión explícita del contrato. La respuesta generativa actual no clasifica ni autoriza operaciones sobre tickets.
