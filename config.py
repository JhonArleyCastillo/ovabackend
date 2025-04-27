from dotenv import load_dotenv
import os

# Cargar variables desde .env
load_dotenv()

# Variables de entorno
HF_API_KEY = os.getenv("HF_API_KEY")  # Token de Hugging Face
HF_MODELO_LLM = os.getenv("HF_MODELO_LLM")
HF_MODELO_TTS = os.getenv("HF_MODELO_TTS")
HF_MODELO_STT = os.getenv("HF_MODELO_STT")
HF_MODELO_IMG = os.getenv("HF_MODELO_IMG")
HF_MODELO_SIGN = os.getenv("HF_MODELO_SIGN", "RavenOnur/Sign-Language")  
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://helpova.web.app,http://localhost:3000,http://3.15.5.52:8000,http://3.15.5.52").split(",")
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# Configuración de la base de datos
# Valores predeterminados para MySQL - Se pueden sobrescribir con variables de entorno
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Construir DATABASE_URL para MySQL
# Formato: mysql+mysqlconnector://usuario:contraseña@host:puerto/nombre_db
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Configuración para SQLite como fallback si MySQL no está disponible
SQLITE_URL = "sqlite:///./ova_app.db"
# Si DATABASE_URL no contiene información de MySQL, usar SQLite
if not ("mysql" in DATABASE_URL or "postgres" in DATABASE_URL):
    DATABASE_URL = SQLITE_URL

# Configuración JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

