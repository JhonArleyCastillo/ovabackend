# Guía para colaborar con HelpOVA (backend FastAPI)

Este documento resume cómo contribuir de forma segura y consistente en el backend de HelpOVA (FastAPI en Python) y cómo interactuar con las piezas clave del proyecto.

## Arquitectura y estructura

- Framework: FastAPI + Uvicorn
- Carpeta backend: `ovabackend/`
	- `main.py`: punto de entrada de la app (registra middleware, CORS, routers, logging, DB)
	- `routers/`: endpoints (WebSocket chat, auth, contacto, etc.)
	- `services/`: lógica de negocio (ej. integración robusta con Gradio/HF Spaces)
	- `middleware/`: seguridad HTTPS y manejadores de errores (incluye errores de Gradio)
	- `common/`: utilidades compartidas y helpers de routers
	- `models.py`: modelos Pydantic para mensajes y WebSocket
	- `database.py`: conexión SQLite (dev) y MySQL (prod) sin creación de tablas en MySQL
	- `config.py`: configuración centralizada (CORS, flags de entorno, DB, tokens)
	- `tests/`: pruebas unitarias e integración (p. ej., middleware de Gradio)

## Reglas de oro (Do/Don’t)

- Seguridad
	- Producción: solo HTTPS. El middleware `https_security_middleware` fuerza HTTPS y aplica headers de seguridad (HSTS, X-Frame-Options, etc.).
	- CORS: usa únicamente orígenes definidos en `config.py`. No añadir `*` en producción.
- Integración con Gradio/Hugging Face
	- Siempre usar `services/gradio_robust_client.py` desde servicios que invocan Spaces.
	- No consumas Gradio directamente desde los routers.
	- Errores de Gradio (como “bool is not iterable”) deben quedar contenidas por el cliente robusto y, a nivel app, por `GradioErrorMiddleware`. O directamente solucionados con 
Causas comunes del error:

    Iterar sobre un booleano directamente:
    Esto es lo más común. Por ejemplo, si tienes una variable x = True y luego intentas iterar sobre ella con un bucle for, obtendrás este error.
    Pasar un booleano a una función que espera un iterable:
    Algunas funciones en Python esperan objetos iterables como listas, tuplas o diccionarios, y si les pasas un booleano, recibirás este error.
    Reasignar una variable a un booleano después de ser iterable:
    Si declaras una variable como iterable (ej. una lista) y luego le asignas un valor booleano, el tipo de la variable cambiará a booleano, y no será iterable. 

Cómo solucionar el error:

    1. Identifica la causa:
    Revisa el código donde se produce el error y determina si estás iterando sobre un booleano o si estás pasando un booleano a una función que espera un iterable. 

2. Corrige la lógica del programa:
Si estás iterando sobre un booleano, cambia la lógica del programa para que opere con un objeto iterable válido. 
3. Verifica el tipo de objeto:
Usa la función type() o isinstance() para verificar el tipo de objeto antes de iterar, asegurándote de que sea iterable. 
4. Utiliza iterables válidos:
Si necesitas iterar, utiliza una lista, tupla, diccionario, cadena u otro objeto iterable adecuado. 

Ejemplos:
Error.
Python

x = True
for i in x:
    print(i)

Solución.
Python

x = [1, 2, 3]  # Cambiar a una lista
for i in x:
    print(i)

Error.
Python

def mi_funcion(iterable_object):
    for item in iterable_object:
        print(item)

x = True
mi_funcion(x)

Solución.
Python

def mi_funcion(iterable_object):
    for item in iterable_object:
        print(item)

x = [1, 2, 3]
mi_funcion(x)


- Base de datos
	- Dev: SQLite permitido (tablas `CREATE TABLE IF NOT EXISTS` se manejan para dev).
	- Prod: MySQL sin creación de tablas. `setup_database()` ya no crea tablas en MySQL; solo verifica conectividad. No agregar migraciones implícitas aquí.
- Estilo de cambios
	- Cambios pequeños y focalizados; respeta APIs públicas existentes.
	- Reutiliza utilidades en `common/` y patrones de routers (pydantic, manejo de errores, logging).
	- No incluir secretos en código ni logs (ej. `HF_TOKEN`). Usa variables de entorno.

## Cómo ejecutar localmente

1) Requisitos: Python 3.10+, entorno virtual en `env/` ya presente en el repo.
2) Activar el entorno (PowerShell en Windows):
	 - `env\Scripts\Activate.ps1`
3) Variables de entorno mínimas (dev):
	 - `ENVIRONMENT=development`
	 - `USE_SQLITE=true` y `SQLITE_PATH` apuntando a `dev_database.sqlite` si aplica.
4) Ejecutar API:
	 - `python -m uvicorn ovabackend.main:app --reload --port 8000`

Endpoints útiles:
- Salud WebSocket: `GET /api/chat/health`
- Salud API: `GET /status` (según routers configurados)

## WebSocket de chat

- Router: `routers/websocket_router.py`
- Rutas: `WS_CHAT` (de `routes.py`) y `/ws/chat` (alias)
- Modelos de mensajes: definidos en `models.py` (TextMessage, TypingMessage, ErrorMessage, etc.)
- Importación de modelos: usa `from ovabackend.models import ...` (hay fallbacks en el router para ejecuciones directas).

## Integración con Gradio/HF Spaces

- Cliente robusto: `services/gradio_robust_client.py` (reintentos, timeouts, fallbacks, parseo defensivo)
- Servicio de compatibilidad: `services/gradio_compatibility_service.py`
- Middleware de errores: `middleware/gradio_error_middleware.py` (devuelve JSON controlado `GRADIO_BOOL_ERROR` en fallos conocidos)

Buenas prácticas:
- No expongas trazas crudas al cliente. Usa respuestas controladas desde middleware/servicios.
- Loguea con contexto (IDs de correlación si hay), sin datos sensibles.
- Evita cambiar el codigo si ya es funcional

## Base de datos

- `database.py` selecciona SQLite en dev y MySQL en prod.
- MySQL (prod): no crea tablas ni modifica esquema. Asegura conectividad únicamente.
- SQLite (dev): helpers con `CREATE TABLE IF NOT EXISTS` para acelerar pruebas locales.

## Logging y observabilidad

- Configura logging con `ovabackend.logging_config.configure_logging()`.
- Evita logs con datos sensibles. Prefiere niveles INFO/ERROR y mensajes claros.

## Pruebas

- Ubicación: `ovabackend/tests/`
- Pruebas incluidas (ejemplos):
	- `test_gradio_middleware.py`: valida captura de “bool is not iterable”.
	- `test_gradio_integration.py`: prueba de integración del middleware.
- Ejecutar una prueba:
	- `python ovabackend\tests\test_gradio_middleware.py`

## Añadir un nuevo endpoint

1) Crea/edita un archivo en `routers/` y define un `APIRouter`.
2) Usa modelos Pydantic (en `models.py` o módulo nuevo bajo `ovabackend/`).
3) Maneja errores con utilidades en `common/` o lanza `HTTPException` acorde.
4) Registra el router en `main.py`.
5) Añade pruebas mínimas (unitarias/integración) si cambia comportamiento público.

## CORS y dominios

- Edita orígenes en `config.py`.
- Producción: usa solo HTTPS y dominios canónicos (ej. `https://www.api.ovaonline.tech`).

## Frontend (referencia rápida)

- Frontend en `frontend/` (React). Admin en `/admin` (login) y `/admin` (dashboard protegido).
- El frontend utiliza `services/auth.service.js` y rutas en `src/config/api.routes.js`.

## Checklist antes de subir cambios

- [ ] El servidor inicia sin errores y sin crear tablas MySQL.
- [ ] Los endpoints/WS nuevos usan modelos y manejo de errores coherente.
- [ ] No hay datos sensibles en código ni logs.
- [ ] Las pruebas relevantes corren en local.
- [ ] Documentaste cualquier nuevo flag/env requerido.

## Contacto rápido

Si un Space falla o cambia su firma, usa/ajusta `gradio_robust_client.py` y confirma que `GradioErrorMiddleware` esté activo en `main.py`.

-Si se registra una entrada de un json desde los modelos en Hugginface, se debe extraer solo el texto relevante que se le mostrara al cliente.