"""
Configuración de la base de datos para la aplicación.

Este archivo configura la conexión a la base de datos usando mysql-connector-python
y proporciona funciones para gestionar las conexiones.
"""

import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
import time
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Importar las variables de configuración directamente desde config.py
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# Verificar que las variables estén definidas
if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
    logger.error("Variables de conexión a BD incompletas o no definidas")

# Configuración del pool de conexiones
db_config = {
    'host': DB_HOST,
    'port': int(DB_PORT),
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'connect_timeout': 10,  # Segundos para el timeout de conexión
    'autocommit': False
}

# Crear un pool de conexiones
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="ova_pool",
        pool_size=5,
        **db_config
    )
    logger.info("Pool de conexiones creado correctamente")
except Exception as e:
    logger.error(f"Error al crear el pool de conexiones: {e}")
    # Crear un objeto falso para evitar errores en tiempo de ejecución
    connection_pool = None

def get_db():
    """
    Proporciona una conexión de base de datos y asegura que se cierre después de usarse.
    
    Para usar con FastAPI como dependencia:
    @app.get("/items/")
    def read_items(db: mysql.connector.connection.MySQLConnection = Depends(get_db)):
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()
        cursor.close()
        return items
    """
    if connection_pool is None:
        # Fallar rápidamente si el pool no está disponible
        raise RuntimeError("El pool de conexiones de base de datos no está disponible.")
    
    # Obtener una conexión del pool
    conn = connection_pool.get_connection()
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def db_session():
    """
    Proporciona un contexto para usar la conexión de la base de datos.
    
    Uso:
    with db_session() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()
    """
    # Verificar si el pool está disponible antes de intentar conexiones
    if connection_pool is None:
        raise RuntimeError("El pool de conexiones de base de datos no está disponible.")
    
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Obtener una conexión del pool
            conn = connection_pool.get_connection()
                
            try:
                yield conn
                conn.commit()
                return
            except mysql.connector.Error as e:
                conn.rollback()
                last_error = e
                raise
            finally:
                conn.close()
                
        except (mysql.connector.errors.PoolError, 
                mysql.connector.errors.InterfaceError,
                mysql.connector.errors.OperationalError) as e:
            retry_count += 1
            last_error = e
            logger.warning(f"Error de conexión (intento {retry_count}/{max_retries}): {e}")
            time.sleep(1)  # Esperar antes de reintentar
    
    # Si llegamos aquí, todos los reintentos fallaron
    raise mysql.connector.errors.OperationalError(f"No se pudo establecer conexión después de {max_retries} intentos: {last_error}")

def setup_database():
    """
    Configura la base de datos creando las tablas necesarias si no existen.
    """
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            
            # Crear tabla de administradores
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS administradores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                es_superadmin BOOLEAN DEFAULT FALSE,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)
            
            # Crear tabla de sesiones de administradores
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sesiones_admin (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                token VARCHAR(255) NOT NULL,
                fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_expiracion DATETIME NOT NULL,
                ip_address VARCHAR(45),
                navegador VARCHAR(255),
                activa BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (admin_id) REFERENCES administradores(id) ON DELETE CASCADE,
                INDEX (token),
                INDEX (admin_id)
            )
            """)
            
            # Crear tabla de contactos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS contactos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                asunto VARCHAR(200) NOT NULL,
                mensaje TEXT NOT NULL,
                fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
                leido BOOLEAN DEFAULT FALSE,
                respondido BOOLEAN DEFAULT FALSE,
                INDEX (email),
                INDEX (fecha_envio)
            )
            """)
            
            logger.info("Base de datos configurada correctamente")
            
    except Exception as e:
        logger.error(f"Error al configurar la base de datos: {e}")
        raise