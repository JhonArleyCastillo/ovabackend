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
import os
import sqlite3
from importlib import import_module

# Configurar logger
logger = logging.getLogger(__name__)

# Importar las variables de configuración directamente desde config.py
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, IS_DEVELOPMENT

# Comprobar si estamos en entorno de desarrollo con SQLite
try:
    from config import USE_SQLITE, SQLITE_PATH
except ImportError:
    USE_SQLITE = False

# Base de datos SQLite para desarrollo
if IS_DEVELOPMENT and USE_SQLITE:
    logger.info(f"Usando SQLite para desarrollo: {SQLITE_PATH}")
    
    # Crear el directorio para SQLite si no existe
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    
    # Función para obtener conexión SQLite
    def get_sqlite_connection():
        return sqlite3.connect(SQLITE_PATH)
    
    # Configurar manejo de contexto para SQLite
    @contextmanager
    def db_session():
        """
        Proporciona un contexto para usar la conexión SQLite.
        """
        conn = None
        try:
            conn = get_sqlite_connection()
            # Configurar para que devuelva diccionarios en las consultas
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error en la sesión SQLite: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_db():
        """
        Versión de get_db para SQLite, compatible con FastAPI.
        """
        conn = None
        try:
            conn = get_sqlite_connection()
            # Configurar para que devuelva diccionarios en las consultas
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    # Crear un objeto connection_pool ficticio para compatibilidad
    connection_pool = True

# MySQL para producción o desarrollo con MySQL
else:
    # Verificar que las variables estén definidas
    if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
        logger.error("Variables de conexión a BD incompletas o no definidas")

    # Configuración del pool de conexiones MySQL
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
        logger.info("Pool de conexiones MySQL creado correctamente")
    except Exception as e:
        logger.error(f"Error al crear el pool de conexiones MySQL: {e}")
        # Crear un objeto falso para evitar errores en tiempo de ejecución
        connection_pool = None

    @contextmanager
    def db_session():
        """
        Proporciona un contexto para usar la conexión de la base de datos MySQL.
        
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

    def get_db():
        """
        Proporciona una conexión de base de datos MySQL y asegura que se cierre después de usarse.
        
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

def setup_database():
    """
    Configura la base de datos creando las tablas necesarias si no existen.
    """
    try:
        with db_session() as conn:
            if IS_DEVELOPMENT and USE_SQLITE:
                # SQLite no tiene soporte para algunos tipos específicos de MySQL
                # Adaptamos las sentencias para SQLite
                cursor = conn.cursor()
                
                # Crear tabla de administradores para SQLite
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS administradores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    es_superadmin INTEGER DEFAULT 0,
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Crear tabla de sesiones de administradores para SQLite
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS sesiones_admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    token TEXT NOT NULL,
                    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_expiracion TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    navegador TEXT,
                    activa INTEGER DEFAULT 1,
                    FOREIGN KEY (admin_id) REFERENCES administradores(id) ON DELETE CASCADE
                )
                """)
                
                # Crear índices para sesiones_admin
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_token ON sesiones_admin(token)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_id ON sesiones_admin(admin_id)")
                
                # Crear tabla de contactos para SQLite
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    email TEXT NOT NULL,
                    asunto TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    leido INTEGER DEFAULT 0,
                    respondido INTEGER DEFAULT 0
                )
                """)
                
                # Crear índices para contactos
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON contactos(email)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fecha_envio ON contactos(fecha_envio)")
                
            else:
                # MySQL original
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
        if IS_DEVELOPMENT:
            logger.warning("Error en desarrollo: la aplicación continuará sin base de datos completa")
        else:
            raise