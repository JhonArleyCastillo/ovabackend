from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Importar configuración y funciones de configuración
from config import ALLOWED_ORIGINS, CORS_MAX_AGE, HF_API_KEY # Asegurarse que HF_API_KEY se importe si se usa aquí (aunque no debería)
from logging_config import setup_logging

# Importar routers
from routers import status_router, websocket_router, image_router

# Configurar el logging ANTES de cualquier otra cosa
setup_logging()
logger = logging.getLogger(__name__)

# Crear la instancia de la aplicación FastAPI
app = FastAPI(
    title="API Asistente Inteligente Multimodal",
    description="API para interactuar con un asistente IA usando voz, texto e imágenes.",
    version="1.0.0"
)

# Configurar CORS
logger.info(f"Configurando CORS con orígenes permitidos: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://helpova.web.app", "http://localhost:3000"],  # Permitir tanto producción como desarrollo
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],  # Añadir todos los métodos posibles
    allow_headers=["*"],  # Permitir todos los encabezados
    expose_headers=["*"], # Exponer todos los encabezados (útil para algunos casos)
    max_age=CORS_MAX_AGE, # Tiempo de caché para preflight
)

# Incluir los routers en la aplicación principal
logger.info("Incluyendo routers en la aplicación")
app.include_router(status_router.router, tags=["Estado"])
app.include_router(websocket_router.router, prefix="/api", tags=["WebSockets y Audio"])
app.include_router(image_router.router, prefix="/api", tags=["Análisis de Imágenes"])

# Ya no se necesita la inicialización del cliente aquí, se maneja en el servicio
# from huggingface_hub import InferenceClient
# client = InferenceClient(api_key=HF_API_KEY)

# Los endpoints definidos aquí son redundantes porque ya están en los routers
# Se eliminan las siguientes definiciones:
# @app.websocket("/api/detect") ...
# @app.get("/") ...
# @app.get("/status") ...
# @app.websocket("/ws/chat") ...
# @app.post("/analyze-sign-language") ...
# @app.post("/detect-objects") ...
# @app.post("/describe-image") ...

# Opcional: Añadir un manejador global de excepciones
# @app.exception_handler(Exception)
# async def generic_exception_handler(request, exc):
#     logger.error(f"Error no manejado: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={"error": "Error interno del servidor", "status": "error"}
#     )

# Mensaje de inicio
logger.info("Aplicación FastAPI configurada y lista para iniciar.")

# Nota: Uvicorn se ejecutará externamente (ej: `uvicorn backend.main:app --reload`)
# Por lo tanto, no incluimos `if __name__ == "__main__": uvicorn.run(...)` aquí
