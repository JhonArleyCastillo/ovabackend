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

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

logger = logging.getLogger(__name__)

# ===== Entorno =====
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
IS_DEVELOPMENT: bool = ENVIRONMENT.lower() == "development"
ASL_DEBUG: bool = os.getenv("ASL_DEBUG", "false").lower() == "true" or IS_DEVELOPMENT

# ===== Base de Datos =====
# Para desarrollo simple, se puede usar SQLite con USE_SQLITE=true
USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() == "true"
if USE_SQLITE:
    SQLITE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dev_database.sqlite')
    DB_HOST = DB_PORT = DB_USER = DB_PASSWORD = DB_NAME = None  # No se usan en SQLite
    logger.info(f"DB: SQLite en {SQLITE_PATH}")
else:
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_NAME: Optional[str] = os.getenv("DB_NAME")
    logger.info(f"DB: MySQL en host={DB_HOST}, puerto={DB_PORT}")

# ===== Hugging Face / Modelos =====
HF_API_KEY: Optional[str] = os.getenv("HF_API_KEY")  # opcional para InferenceClient
HF_MODEL: Optional[str] = os.getenv("HF_MODEL")       # opcional para texto/caption si se usa
HF_MODELO_SIGN: str = os.getenv("HF_MODELO_SIGN", "default-sign-language-model")  # legado
# Space Gradio para ASL (usado por gradio_client). Acepta URL completa.
HF_ASL_SPACE_URL: str = os.getenv(
    "HF_ASL_SPACE_URL",
    "https://jhonarleycastillov-asl-image.hf.space"
)
if not HF_ASL_SPACE_URL:
    logger.warning("HF_ASL_SPACE_URL no definido; el reconocimiento ASL no funcionará.")

# ===== CORS =====
_default_origins = [
    "https://helpova.web.app",
    "https://api.ovaonline.tech",
    "https://www.api.ovaonline.tech",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_raw_origins = os.getenv("ALLOWED_ORIGINS", ",".join(_default_origins)).split(",")
# En producción, filtrar a HTTPS + localhost; en dev, dejar lista tal cual
if not IS_DEVELOPMENT:
    ALLOWED_ORIGINS = [o.strip() for o in _raw_origins if o.strip().startswith("https://") or "localhost" in o]
else:
    ALLOWED_ORIGINS = [o.strip() for o in _raw_origins]
logger.info(f"CORS orígenes permitidos: {ALLOWED_ORIGINS}")

CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# ===== JWT =====
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if JWT_SECRET_KEY == "supersecretkey" and not IS_DEVELOPMENT:
    logger.warning("JWT_SECRET_KEY usa valor por defecto; cámbialo en producción.")
# ===== Configuración JWT =====

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
