from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os

# Necesitamos agregar nuestro directorio al path para que Python encuentre nuestros módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importando toda la configuración y routers que hemos creado
from ovabackend.config import ALLOWED_ORIGINS, CORS_MAX_AGE, IS_DEVELOPMENT
from ovabackend.routers import status_router, websocket_router, image_router, auth_router, usuarios_router, contact_router, resilience_router
from ovabackend.logging_config import configure_logging
from ovabackend.database import setup_database
from ovabackend.middleware import https_security_middleware, validate_cors_origin
import ovabackend.db_models

# Configuramos el logging antes que nada para tener visibilidad de todo
logger = logging.getLogger(__name__)
configure_logging()

app = FastAPI(
    title="API Asistente Inteligente Multimodal",
    description="API para interactuar con un asistente IA usando voz, texto e imágenes.",
    version="1.0.0"
)

# Ya no necesitamos este registro duplicado, lo removimos arriba
# app.include_router(image_router.router)

# Configurar CORS es crítico para que el frontend pueda hablar con nosotros
logger.info(f"Configurando CORS con orígenes permitidos: {ALLOWED_ORIGINS}")
logger.info(f"Entorno de ejecución: {'Desarrollo' if IS_DEVELOPMENT else 'Producción'}")

# Solo permitimos los headers que realmente usamos, por seguridad
allowed_headers = ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"]
exposed_headers = ["Content-Length", "Content-Type"]

# En producción somos estrictos con los métodos HTTP
allowed_methods = ["GET", "POST", "OPTIONS"]
if IS_DEVELOPMENT:
    # En desarrollo dejamos más libertad para poder hacer pruebas fácilmente
    allowed_methods.extend(["PUT", "DELETE", "PATCH"])
    # También somos más permisivos con headers en desarrollo
    allowed_headers.append("*")

# Es importante verificar que no tengamos orígenes inseguros en producción
logger.info(f"Configurando CORS con {len(ALLOWED_ORIGINS)} orígenes permitidos")
for origin in ALLOWED_ORIGINS:
    if not IS_DEVELOPMENT and not (origin.startswith("https://") or "localhost" in origin):
        logger.warning(f"Origen inseguro en producción: {origin}")

# MIDDLEWARE DE SEGURIDAD HTTPS - DEBE IR ANTES QUE CORS
logger.info("🔒 Configurando middleware de seguridad HTTPS...")
app.middleware("http")(https_security_middleware)

# CORS con validación adicional de orígenes
filtered_origins = []
for origin in ALLOWED_ORIGINS:
    if validate_cors_origin(origin):
        filtered_origins.append(origin)
    else:
        logger.warning(f"🚫 Origin filtrado por seguridad: {origin}")

logger.info(f"✅ Origins validados para CORS: {filtered_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=filtered_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    expose_headers=exposed_headers,
    max_age=CORS_MAX_AGE,
)

# Registramos todos nuestros routers - cada uno maneja una parte específica de la API
# WebSocket para el chat en tiempo real
app.include_router(websocket_router.router, tags=["WebSockets y Audio"])
# Status para verificar que todo funciona
app.include_router(status_router.router, tags=["Estado"])
# El corazón de la app: análisis de imágenes ASL
app.include_router(image_router.router, tags=["Análisis de Imágenes"])
# Autenticación y usuarios
app.include_router(auth_router.router)
app.include_router(usuarios_router.router)
# Formulario de contacto
app.include_router(contact_router.router)
# Monitoreo para saber cómo va todo
app.include_router(resilience_router.resilience_router, tags=["Resiliencia"])

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando servidor...")
    
    # Verificamos que la configuración básica esté bien antes de continuar
    if not ALLOWED_ORIGINS:
        logger.error("❌ ALLOWED_ORIGINS no está configurado - esto romperá CORS")
        sys.exit(1)
    
    # Verificación de seguridad en producción
    if not IS_DEVELOPMENT:
        logger.info("🔒 Modo PRODUCCIÓN detectado - aplicando configuración de seguridad")
        https_only_origins = [origin for origin in ALLOWED_ORIGINS if origin.startswith("https://")]
        if len(https_only_origins) != len(ALLOWED_ORIGINS):
            logger.warning("⚠️ Algunos orígenes pueden ser inseguros en producción")
        logger.info(f"🛡️ Middleware HTTPS activo - solo se permitirán conexiones seguras")
        logger.info(f"🔐 Headers de seguridad aplicados automáticamente")
    else:
        logger.info("🔧 Modo DESARROLLO - permitiendo HTTP para localhost")
    
    # Logging de configuración para debugging
    logger.info(f"✅ Métodos HTTP permitidos: {allowed_methods}")
    logger.info(f"✅ Headers permitidos: {allowed_headers}")
    logger.info(f"✅ Headers expuestos: {exposed_headers}")
    
    # Intentamos conectar la base de datos
    logger.info("🔌 Inicializando base de datos...")
    try:
        setup_database()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error al inicializar la base de datos: {e}")
        # No paramos el servidor - el WebSocket y análisis de imágenes pueden funcionar sin BD
        logger.warning("⚠️ Continuando sin BD completa. WebSocket y ASL seguirán funcionando.")
    
    logger.info("🎉 Servidor listo para recibir peticiones")

