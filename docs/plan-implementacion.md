# Estado de implementación y próximos hitos

## Entrega actual: interfaces, recepción y Azure OpenAI

**Implementado:** chat de Streamlit y API de FastAPI ejecutables localmente. El usuario envía texto y recibe una respuesta de soporte generada por el despliegue configurado en Azure OpenAI. La clasificación estructurada sigue pendiente.

| Componente | Entrega |
| --- | --- |
| Entorno | Python 3.14, `pyproject.toml`, `uv.lock`, ejemplo de configuración y ejecución local |
| Interfaz | Chat con límite de caracteres, historial por sesión, limpieza e indicador de envío |
| Cliente HTTP | URL configurable, plazo de cuarenta segundos y errores comprensibles sin reintentos automáticos |
| Recepción | Endpoint `POST /api/agent/messages` y respuesta sin campos de clasificación |
| Validación | JSON estricto, claves duplicadas rechazadas, normalización Unicode y límite real del cuerpo |
| Acceso | Contexto anónimo establecido por el servidor; credenciales presentadas rechazadas |
| Modelo | Responses API v1, Azure OpenAI, instrucciones separadas y límite de salida |
| Identidad Azure | Microsoft Entra ID mediante Azure CLI o Managed Identity; clave opcional no versionada |
| Consumo | Cuota configurable por IP en ventana deslizante, en memoria y para un único proceso |
| Telemetría | UUID, código de resultado, estado HTTP y duración; sin mensajes ni credenciales |
| Servicio | Salud y documentación OpenAPI |
| Pruebas | Contratos, límites, cuota, fallos del modelo, chat con AppTest e integración con transporte de prueba |

La [guía de ejecución](../README.md) y el [contrato vigente](contrato-api.md) describen lo entregado. El historial de Streamlit es visual; no equivale a memoria del agente. La respuesta no crea ni guarda una solicitud de soporte.

## Validar esta entrega

Desde la raíz del proyecto:

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Demo con los dos procesos del README:

| Caso | Resultado |
| --- | --- |
| «No puedo iniciar sesión desde ayer» | Respuesta técnica generada por Azure OpenAI |
| Texto invisible enviado por API | `422`, sin eco del cuerpo |
| Campo adicional `permissions` | `422`; no establece permisos |
| Cabecera `Authorization` | `401` |
| Cuerpo mayor de 16 KiB, incluso fragmentado | `413` antes del parseo |
| Más de diez solicitudes por IP en un minuto | `429` y `Retry-After` |
| Backend detenido | Error visible en el chat, sin reintento automático |
| Limpiar el historial o actualizar la pantalla | No se repiten peticiones anteriores |

Las pruebas de integración de interfaz utilizan el backend con un transporte de prueba. Los resultados de ejecución se observan al correr los comandos; todavía no se presenta una medición formal de calidad ni protección de contenido como parte de esta entrega.

Verificación del 2026-09-14: 83 pruebas aprobadas; Ruff aprobó código y formato. Una petición HTTP real recorrió FastAPI y el despliegue `rag-manual-generico-dev-general` y devolvió `answered`. Los servicios continúan disponibles en `8010` y `8510`.

## Próximo hito: clasificación y políticas

La [especificación del paso 2](diseno-pasos-1-2.md) conserva el diseño futuro. Azure OpenAI ya es el proveedor del texto generado; aún debe diseñarse y evaluarse el contrato separado de clasificación.

1. Añadir controles de contenido y un adaptador del clasificador sin herramientas ni autoridad sobre permisos.
2. Validar su salida contra el catálogo de intenciones y entidades explícitas del mensaje.
3. Implementar el evaluador determinista de alcance y capacidades en el servidor.
4. Elegir e integrar identidad real antes de habilitar capacidades privadas de tickets.
5. Ampliar los errores de dependencia ya implementados para el contrato de clasificación; ninguno permitirá avanzar.
6. Evaluar clasificación con un proveedor real y mensajes etiquetados, distinguiendo resultados de modelo y pruebas simuladas.

El primer conjunto de evaluación propuesto tendrá al menos 60 mensajes sintéticos, 10 por intención, con separación de ajuste y evaluación y un conjunto independiente de ataques y peticiones legítimas. Se reportarán precisión/recall por intención, matriz de confusión, salidas inválidas, aclaraciones, latencia y tokens/coste cuando estén disponibles. No existen esas mediciones en la entrega actual.

## Etapas posteriores

Memoria persistente, RAG, consulta o creación de tickets, herramientas y un ciclo de evaluación operativo pertenecen a otros hitos. El despliegue público queda pendiente; antes se definirá identidad de usuarios, límite compartido y configuración confiable de proxies.

No se necesita un framework de agentes. Para usar respuestas generadas se requiere acceso al despliegue de Azure; el modo local sin modelo se mantiene disponible al desactivar `SUPPORTFLOW_AZURE_OPENAI_ENABLED`.
