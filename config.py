import os
import logging
# Importar el módulo dotenv centralizado para asegurar que las variables de entorno estén cargadas
from dotenv import load_dotenv
load_dotenv()

# Configurar logger
logger = logging.getLogger(__name__)

# ===== Configuración del Entorno =====
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_DEVELOPMENT = ENVIRONMENT == "development"

# ===== Configuración de la Base de Datos =====
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if DB_HOST:
    logger.info("Variables de base de datos cargadas correctamente")
else:
    logger.warning("Variables de base de datos no encontradas")

# ===== Configuración de Hugging Face =====
HF_API_KEY = os.getenv("HF_API_KEY")  # Token de Hugging Face
HF_MODELO_LLM = os.getenv("HF_MODELO_LLM")
HF_MODELO_TTS = os.getenv("HF_MODELO_TTS")
HF_MODELO_STT = os.getenv("HF_MODELO_STT")
HF_MODELO_IMG = os.getenv("HF_MODELO_IMG")
HF_MODELO_SIGN = os.getenv("HF_MODELO_SIGN", "RavenOnur/Sign-Language")

# ===== Configuración de CORS =====
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", 
                          "https://helpova.web.app,http://localhost:3000,https://3.15.5.52,https://3.15.5.52:8000," + 
                          "https://api.ovaonline.tech,http://api.ovaonline.tech").split(",")
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# ===== Configuración JWT =====
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Verificar configuración JWT segura
if JWT_SECRET_KEY == "supersecretkey":
    logger.warning("JWT_SECRET_KEY está usando el valor predeterminado. Se recomienda cambiarlo en producción.")

