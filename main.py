from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os

# Añadir el directorio raíz del proyecto al path de Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importaciones de la aplicación
from backend.config import ALLOWED_ORIGINS, CORS_MAX_AGE, IS_DEVELOPMENT
from backend.routers import status_router, websocket_router, image_router, auth_router, usuarios_router, contact_router
from backend.logging_config import configure_logging
from backend.database import setup_database
import backend.db_models as db_models

# Configurar logging
logger = logging.getLogger(__name__)
configure_logging()

app = FastAPI(
    title="API Asistente Inteligente Multimodal",
    description="API para interactuar con un asistente IA usando voz, texto e imágenes.",
    version="1.0.0"
)

# Configurar CORS con diferentes configuraciones según el entorno
logger.info(f"Configurando CORS con orígenes permitidos: {ALLOWED_ORIGINS}")
logger.info(f"Entorno de ejecución: {'Desarrollo' if IS_DEVELOPMENT else 'Producción'}")

# Headers específicos que realmente necesita la aplicación
allowed_headers = ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"]
exposed_headers = ["Content-Length", "Content-Type"]

# Métodos HTTP que realmente utiliza la aplicación
allowed_methods = ["GET", "POST", "OPTIONS"]
if IS_DEVELOPMENT:
    # En desarrollo podemos permitir más métodos para facilitar pruebas
    allowed_methods.extend(["PUT", "DELETE", "PATCH"])
    # En desarrollo podemos ser un poco más permisivos con los headers
    allowed_headers.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    expose_headers=exposed_headers,
    max_age=CORS_MAX_AGE,
)

# Incluir routers
# WebSocket router no lleva prefijo adicional
app.include_router(websocket_router.router, tags=["WebSockets y Audio"])
# Los routers REST no necesitan prefijo adicional ya que se incluye en las rutas
app.include_router(status_router.router, tags=["Estado"])
app.include_router(image_router.router, tags=["Análisis de Imágenes"])
# Routers para la base de datos y autenticación
app.include_router(auth_router.router)
app.include_router(usuarios_router.router)
# Nuevo router para el formulario de contacto
app.include_router(contact_router.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando servidor...")
    
    # Verificar configuraciones críticas
    if not ALLOWED_ORIGINS:
        logger.error("ALLOWED_ORIGINS no está configurado correctamente")
        sys.exit(1)
    
    # Registrar información sobre la configuración de seguridad
    logger.info(f"Métodos HTTP permitidos: {allowed_methods}")
    logger.info(f"Headers permitidos: {allowed_headers}")
    logger.info(f"Headers expuestos: {exposed_headers}")
    
    # Inicializar la base de datos
    logger.info("Inicializando base de datos...")
    try:
        setup_database()
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        if not IS_DEVELOPMENT:
            sys.exit(1)
        else:
            logger.warning("Continuando ejecución en modo desarrollo a pesar del error de BD")
    
    logger.info("Servidor iniciado correctamente")

