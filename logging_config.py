import logging
import sys

def setup_logging(level=logging.INFO):
    """Configura el sistema de logging para la aplicación."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configuración básica
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout) # Asegurar salida a stdout
        ]
    )
    
    # Obtener el logger raíz y configurarlo
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Evitar duplicación si ya hay handlers
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    # Configurar loggers específicos si es necesario (ej. uvicorn)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Sistema de logging configurado.")

# Added configure_logging function to resolve import error
def configure_logging(level=logging.INFO):
    """
    Alias para setup_logging para mantener compatibilidad con código existente.
    Configura el sistema de logging para la aplicación.
    """
    return setup_logging(level)

# Configurar al importar el módulo
# setup_logging() # Comentado para llamar explícitamente en main.py
