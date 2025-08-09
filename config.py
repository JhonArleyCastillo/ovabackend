"""
Application configuration module.

This module handles all configuration settings for the OVA Web application,
including database connections, API keys, CORS settings, and environment-specific
configurations. It uses environment variables with sensible defaults for
development environments.
"""

import os
import logging
import secrets
from typing import Optional
from dotenv import load_dotenv
# Hugging Face login - optional
try:
    from huggingface_hub import login
    HF_LOGIN_AVAILABLE = True
except ImportError:
    HF_LOGIN_AVAILABLE = False
    logging.warning("Hugging Face Hub not available - some AI features may be limited")

# Load environment variables from .env file
load_dotenv()

# Configure module logger
logger = logging.getLogger(__name__)

# ===== Environment Configuration =====
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
IS_DEVELOPMENT: bool = ENVIRONMENT == "development"

# ===== Database Configuration =====
# Environment-specific database configuration with secure defaults
if IS_DEVELOPMENT:
    # Development environment defaults for local testing
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_NAME: str = os.getenv("DB_NAME", "ovaweb_dev")
    
    # SQLite alternative for lightweight development
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() == "true"
    SQLITE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'dev_database.sqlite'
    )
    
    logger.info(
        f"Development configuration: "
        f"{'SQLite' if USE_SQLITE else 'MySQL'} database"
    )
else:
    # Production requires explicit configuration for security
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306")) 
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_NAME: Optional[str] = os.getenv("DB_NAME")
    
    # SQLite not recommended for production
    USE_SQLITE: bool = False
    SQLITE_PATH: Optional[str] = None

# ===== Hugging Face API Configuration =====
# AI model configuration for various services
HF_API_KEY: Optional[str] = os.getenv("HF_API_KEY")
HF_MODEL: Optional[str] = os.getenv("HF_MODEL")
HF_MODELO_SIGN: str = os.getenv("HF_MODELO_SIGN", "default-sign-language-model")
# ===== Configuración de CORS =====
# Definir orígenes permitidos según el entorno
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    ",".join([
        "https://helpova.web.app",
        "http://localhost:3000",
        "https://www.api.ovaonline.tech",
        "https://www.api.ovaonline.tech:8000"
    ])
).split(",")

# En producción, filtrar para permitir solo orígenes HTTPS (excepto localhost)
if not IS_DEVELOPMENT:
    ALLOWED_ORIGINS = [origin for origin in _raw_origins if origin.startswith("https://") or "localhost" in origin]
    # Registrar los orígenes filtrados
    logger.info(f"Modo producción: Filtrando orígenes para permitir solo HTTPS: {ALLOWED_ORIGINS}")
else:
    ALLOWED_ORIGINS = _raw_origins
    logger.info(f"Modo desarrollo: Permitiendo todos los orígenes configurados: {ALLOWED_ORIGINS}")

CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# ===== Configuración JWT =====
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Verificar configuración JWT segura
if JWT_SECRET_KEY == "supersecretkey":
    logger.warning("JWT_SECRET_KEY está usando el valor predeterminado. Se recomienda cambiarlo en producción.")

# ===== Validaciones en Producción =====
if not IS_DEVELOPMENT:
    # Validar configuración de base de datos
    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
        logger.error("Faltan variables de entorno de base de datos en producción.")
        raise EnvironmentError("Configuración de base de datos incompleta para producción.")
    # Validar Hugging Face
    missing_hf = [k for k,v in {
        'HF_API_KEY': HF_API_KEY,
        'HF_MODEL': HF_MODEL
    }.items() if not v]
    if missing_hf:
        logger.error(f"Faltan variables HF en producción: {missing_hf}")
        raise EnvironmentError(f"Variables HF requeridas no definidas: {missing_hf}")
    # Validar JWT
    if JWT_SECRET_KEY == "supersecretkey":
        logger.error("JWT_SECRET_KEY está usando el valor predeterminado en producción.")
        raise EnvironmentError("Debe configurar JWT_SECRET_KEY seguro en producción.")
    # Ajustar CORS para producción (solo HTTPS except localhost)
    ALLOWED_ORIGINS = [origin for origin in _raw_origins if origin.startswith("https://") or "localhost" in origin]
    logger.info(f"Modo producción: Orígenes permitidos: {ALLOWED_ORIGINS}")

