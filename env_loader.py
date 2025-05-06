"""
Módulo para cargar variables de entorno desde el archivo .env
Este módulo centraliza la carga de variables de entorno y asegura que
esté disponible para todos los módulos que lo importen.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_env_vars():
    """
    Carga las variables de entorno desde el archivo .env.
    Busca el archivo .env en el directorio actual y en los directorios padres.
    """
    try:
        # Encuentra la ruta del archivo .env - primero busca en el directorio actual
        env_path = Path('.env')
        
        # Si no está en el directorio actual, intenta buscar en el directorio backend
        if not env_path.exists():
            # Buscar en el directorio del backend (asumiendo que este script está en backend/)
            backend_dir = Path(__file__).parent.absolute()
            env_path = backend_dir / '.env'
        
        # Si aún no se encuentra, intenta buscar en el directorio raíz del proyecto
        if not env_path.exists():
            # Buscar en el directorio raíz del proyecto
            project_root = Path(__file__).parent.parent.absolute()
            env_path = project_root / '.env'
        
        # Cargar las variables desde el archivo .env encontrado
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            logger.info(f"Variables de entorno cargadas desde {env_path}")
            return True
        else:
            logger.warning("Archivo .env no encontrado. Usando variables de entorno del sistema.")
            return False
    except Exception as e:
        logger.error(f"Error al cargar variables de entorno: {e}")
        return False

# Cargar variables de entorno al importar este módulo
loaded = load_env_vars()