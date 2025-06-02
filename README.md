# Documentación del Backend de OVA Web

Este repositorio contiene la lógica de servidor de la aplicación OVA Web. Está desarrollado en Python con FastAPI y una arquitectura modular por capas.

## Tabla de Contenidos
1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Estructura de Carpetas](#estructura-de-carpetas)
4. [Flujos Principales y Árbol de Funciones](#flujos-principales-y-árbol-de-funciones)
5. [Configuración y Variables de Entorno](#configuración-y-variables-de-entorno)
6. [Dependencias](#dependencias)
7. [Ejecución](#ejecución)

## Visión General
El backend de OVA Web proporciona los servicios de:
- Autenticación y autorización de administradores (JWT, OAuth2)
- Gestión de sesiones y auditoría
- API REST para CRUD de usuarios, contactos y administradores
- Envío y procesamiento de mensajes de contacto
- Procesamiento multimodal: audio (STT/TTS), imagen, lenguaje de señas, uso de Api de chat GPT
- Resiliencia y reintentos automáticos con patrones de Circuit Breaker y Backoff exponencial
- Manejo centralizado de errores y respuestas HTTP estandarizadas

## Arquitectura

1. **Capa de Configuración** (`config.py`)
   - Carga de variables de entorno (.env)
   - Ajuste de CORS, JWT y base de datos según entorno (desarrollo/producción)

2. **Capa de Persistencia** (`database.py`, `db_models.py`)
   - Conexión a MySQL (o SQLite en desarrollo)
   - Modelos de datos con operaciones CRUD básicas

3. **Capa de Utilidades Comunes** (`common/`)
   - `database_utils.py`: gestor de cursores y ejecución de consultas
   - `auth_utils.py`: dependencias y validaciones de token
   - `error_handlers.py`: decoradores y utilidades para manejar errores
   - `router_utils.py`: fábrica y respuestas HTTP comunes
   - `service_utils.py`: mixins y decoradores para servicios con reintentos/timeout

4. **Capa de Servicios** (`services/`)
   - `audio_service.py`: Speech-to-Text y Text-to-Speech (STT/TTS)
   - `chat_service.py`: interacción con modelos LLM (OpenAI, Mistral, etc.)
   - `image_service.py`: detección de objetos y generación de captions
   - `resilience_service*.py`: implementaciones de patrones de resiliencia (Hyx)

5. **Capa de Rutas / Routers** (`routers/`)
   - Endpoints para autenticación, usuarios, contactos, imagen, estado y websocket
   - Versiones refactorizadas con utilidades comunes para reducir duplicación

6. **Punto de Entrada** (`main.py`)
   - Inicialización de FastAPI, CORS, routers y middlewares

```
                                       ┌──────────┐
                                       │  main.py │
                                       └────┬─────┘
                                            │
              ┌─────────────────────────────┼────────────────────────────┐
              │                             │                            │
        ┌─────▼─────┐               ┌───────▼───────┐            ┌───────▼───────┐
        │ routers/   │               │ services/     │            │ common/       │
        └─────┬─────┘               └───────┬───────┘            └───────┬───────┘
              │                              │                            │
   ┌──────────▼─────────┐      ┌─────────────▼───────────┐     ┌──────────▼─────────┐
   │ auth_router.py      │      │ chat_service.py         │     │ database_utils.py   │
   │ usuarios_router_*.py│      │ audio_service.py        │     │ auth_utils.py       │
   │ contact_router_*.py │      │ image_service.py        │     │ error_handlers.py   │
   │ websocket_router.py │      │ resilience_service*.py  │     │ router_utils.py     │
   │ status_router.py    │      └─────────────────────────┘     │ service_utils.py    │
   └─────────────────────┘                                       └─────────────────────┘
```

## Flujos Principales y Árbol de Funciones

1. **Envío de Mensaje de Contacto**
```
enviar_mensaje()
└─ database_error_handler()
└─ validation_error_handler()
└─ ContactoModel.crear()
└─ ContactoModel.obtener_por_id()
```

2. **Marcar Mensaje como Leído**
```
marcar_como_leido()
└─ CommonResponses.not_found()
└─ ContactoModel.actualizar()
└─ ContactoModel.obtener_por_id()
```

3. **Procesamiento de Imagen**
```
analyze_image_async()
└─ detect_objects_async()
   └─ ResilienceService.simple_retry()
└─ describe_image_captioning_async()
   └─ ResilienceService.simple_retry()
```

4. **WebSocket (chat + audio)**
```
websocket_endpoint()
└─ speech_to_text()
└─ get_llm_response()
└─ text_to_speech()
```

## Configuración y Variables de Entorno
Clonar este repositorio, copiar `.env.example` a `.env` y definir:
```dotenv
ENVIRONMENT=production
DB_HOST=
DB_PORT=3306
DB_USER=
DB_PASSWORD=
DB_NAME=
HF_API_KEY=
HF_MODELO_LLM=
HF_MODELO_TTS=
HF_MODELO_STT=
HF_MODELO_IMG=
HF_MODELO_SIGN=
JWT_SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=https://tudominio.com
```

## Dependencias
```bash
pip install -r requirements.txt
```

## Ejecución
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
