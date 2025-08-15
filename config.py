"""
Configuración de la aplicación OVA Web.

Este archivo maneja toda la configuración del backend - desde la base de datos
hasta las APIs de Hugging Face y configuraciones de CORS. Se basa en variables 
de entorno pero tiene valores por defecto sensatos para desarrollo.

Como desarrollador fullstack, aquí es donde cambias cosas como:
- URLs del Gradio Space para ASL
- Configuración de base de datos (SQLite para dev, MySQL para prod)
- Tokens y claves de API
- Configuración de CORS para permitir el frontend
"""

import os
import logging
import secrets
from typing import Optional
from dotenv import load_dotenv

# Intentamos cargar Hugging Face hub si está disponible
try:
    from huggingface_hub import login
    HF_LOGIN_AVAILABLE = True
except ImportError:
    HF_LOGIN_AVAILABLE = False
    logging.warning("Hugging Face Hub no disponible - algunas funciones de AI pueden estar limitadas")

# Cargamos variables de entorno desde .env
load_dotenv()

# Logger para este módulo
logger = logging.getLogger(__name__)

# ===== Configuración de entorno =====
# Determina si estamos en desarrollo o producción
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
IS_DEVELOPMENT: bool = ENVIRONMENT.lower() == "development"

# Debug para ASL - se activa automáticamente en desarrollo o manualmente con ASL_DEBUG=true
ASL_DEBUG: bool = os.getenv("ASL_DEBUG", "false").lower() == "true" or IS_DEVELOPMENT

# ===== Configuración de base de datos =====
# En desarrollo usamos SQLite por simplicidad, en producción MySQL
USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    # SQLite: archivo local, perfecto para desarrollo
    SQLITE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dev_database.sqlite')
    DB_HOST = DB_PORT = DB_USER = DB_PASSWORD = DB_NAME = None  # No necesarios para SQLite
    logger.info(f"Usando SQLite: {SQLITE_PATH}")
else:
    # MySQL: para producción o desarrollo avanzado
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_NAME: Optional[str] = os.getenv("DB_NAME")
    logger.info(f"Usando MySQL: {DB_HOST}:{DB_PORT} base={DB_NAME}")

# ===== Configuración de Hugging Face y modelos de AI =====
# Token opcional para APIs privadas de Hugging Face (nombre histórico HF_API_KEY)
# Unificamos bajo HF_TOKEN para uso consistente (Gradio + InferenceClient)
HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")
HF_API_KEY: Optional[str] = os.getenv("HF_API_KEY")  # Backward compatibility

# Alias: si solo uno existe, usarlo para ambos
if not HF_TOKEN and HF_API_KEY:
    HF_TOKEN = HF_API_KEY
if not HF_API_KEY and HF_TOKEN:
    HF_API_KEY = HF_TOKEN

if ENVIRONMENT.lower() == "production" and not HF_TOKEN:
    logger.warning("⚠️  No se encontró HF_TOKEN en producción - acceso a Spaces privados fallará")
elif HF_TOKEN:
    logger.info("🔐 HF_TOKEN detectado - listo para autenticación Hugging Face")

# Modelos opcionales para features adicionales (caption, etc.)
HF_MODEL: Optional[str] = os.getenv("HF_MODEL")

# NOTA: Eliminado soporte de "modelo sign" directo (HF_MODELO_SIGN).
# Ahora el reconocimiento ASL usa exclusivamente el Space de Hugging Face
# configurado en HF_ASL_SPACE_URL con autenticación via HF_TOKEN.

# ¡IMPORTANTE! Esta es la URL del Gradio Space que hace el reconocimiento ASL
# Si no funciona ASL, revisa que esta URL esté correcta y el Space esté activo
HF_ASL_SPACE_URL: Optional[str] = os.getenv(
    "HF_ASL_SPACE_URL",
    "https://jhonarleycastillov-asl-image.hf.space"
)

if not HF_ASL_SPACE_URL:
    logger.warning("⚠️  HF_ASL_SPACE_URL no está configurado - el reconocimiento ASL NO funcionará!")

# ===== Configuración CORS =====
# Estos son los dominios que pueden hacer peticiones al backend
# En desarrollo permitimos localhost, en producción SOLO HTTPS
_default_origins = [
    "https://helpova.web.app",           # Producción principal
    "https://api.ovaonline.tech",        # API en producción
    "https://www.api.ovaonline.tech",    # API con www
]

_raw_origins = os.getenv("ALLOWED_ORIGINS", ",".join(_default_origins)).split(",")

# Filtro de seguridad ESTRICTO: en producción solo HTTPS, sin excepciones
if not IS_DEVELOPMENT:
    # PRODUCCIÓN: Solo HTTPS, sin localhost, sin HTTP
    ALLOWED_ORIGINS = [
        o.strip() for o in _raw_origins 
        if o.strip().startswith("https://") and not "localhost" in o.lower() and not "127.0.0.1" in o
    ]
    logger.info("🔒 Modo producción: SOLO orígenes HTTPS permitidos (HTTP BLOQUEADO)")
    
    # Validación adicional: asegurar que no hay URLs HTTP
    if any(origin.startswith("http://") for origin in ALLOWED_ORIGINS):
        raise ValueError("🚨 SEGURIDAD: URLs HTTP detectadas en producción - esto NO está permitido")
        
else:
    # DESARROLLO: Permitir localhost HTTP para testing local
    _dev_origins = [
        "http://localhost:3000",             # Frontend local React
        "http://127.0.0.1:3000",            # Frontend local alternativo
        "https://localhost:3000",            # HTTPS local si se configura
    ]
    ALLOWED_ORIGINS = [o.strip() for o in _raw_origins + _dev_origins]
    logger.info("🛠️ Modo desarrollo: localhost HTTP permitido para testing")

logger.info(f"CORS configurado para: {ALLOWED_ORIGINS}")
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))  # Cache preflight requests

# ===== Configuración de Seguridad HTTPS =====
# Forzar HTTPS en producción
FORCE_HTTPS = not IS_DEVELOPMENT
if FORCE_HTTPS:
    logger.info("🔒 HTTPS forzado en producción - HTTP requests serán rechazados")

# Headers de seguridad para producción
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin"
} if not IS_DEVELOPMENT else {}

# ===== Configuración JWT (autenticación) =====
# Clave secreta para firmar tokens JWT - ¡CAMBIAR EN PRODUCCIÓN!
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Advertencia de seguridad para producción
if JWT_SECRET_KEY == "supersecretkey" and not IS_DEVELOPMENT:
    logger.warning("🚨 USAR CLAVE JWT POR DEFECTO EN PRODUCCIÓN ES INSEGURO! Cambia JWT_SECRET_KEY")
