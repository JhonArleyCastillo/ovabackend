import os
import logging
import secrets
# Importar el módulo dotenv centralizado para asegurar que las variables de entorno estén cargadas
from dotenv import load_dotenv
load_dotenv()

# Configurar logger
logger = logging.getLogger(__name__)

# ===== Configuración del Entorno =====
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_DEVELOPMENT = ENVIRONMENT == "development"

# ===== Configuración de la Base de Datos =====
# Valores específicos para desarrollo y producción
if IS_DEVELOPMENT:
    # Valores por defecto para desarrollo local
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_NAME = os.getenv("DB_NAME", "ovaweb_dev")
    
    # SQLite como alternativa para desarrollo
    USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dev_database.sqlite')
    
    logger.info(f"Configuración de desarrollo: {'SQLite' if USE_SQLITE else 'MySQL'}")
else:
    # En producción se requieren todos los valores explícitamente
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", "3306")) 
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    # No usar SQLite en producción
    USE_SQLITE = False
    SQLITE_PATH = None

# ===== Configuración de Hugging Face =====
HF_API_KEY = os.getenv("HF_API_KEY")  # Token de Hugging Face
HF_MODELO_LLM = os.getenv("HF_MODELO_LLM")
HF_MODELO_TTS = os.getenv("HF_MODELO_TTS")
HF_MODELO_STT = os.getenv("HF_MODELO_STT")
HF_MODELO_IMG = os.getenv("HF_MODELO_IMG")
HF_MODELO_SIGN = os.getenv("HF_MODELO_SIGN", "RavenOnur/Sign-Language")

# ===== Configuración de CORS =====
# Definir orígenes permitidos según el entorno
_raw_origins = os.getenv("ALLOWED_ORIGINS", 
                          "https://helpova.web.app,http://localhost:3000,https://3.15.5.52,https://3.15.5.52:8000," + 
                          "https://api.ovaonline.tech,http://api.ovaonline.tech").split(",")

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
        'HF_MODELO_LLM': HF_MODELO_LLM,
        'HF_MODELO_TTS': HF_MODELO_TTS,
        'HF_MODELO_STT': HF_MODELO_STT,
        'HF_MODELO_IMG': HF_MODELO_IMG,
        'HF_MODELO_SIGN': HF_MODELO_SIGN
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

