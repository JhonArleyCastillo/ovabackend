"""
Database configuration and connection management for the application.

This module configures database connections using mysql-connector-python for
production and SQLite for development environments. It provides connection
pooling, context managers, and connection utilities with proper error handling
and logging.
"""

import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any
import time
import logging
import os
import sqlite3
from importlib import import_module
from mysql.connector import errorcode

# Configure module logger
logger = logging.getLogger(__name__)

# Import configuration variables from config module
from config import (
    DB_HOST, 
    DB_PORT, 
    DB_USER, 
    DB_PASSWORD, 
    DB_NAME, 
    IS_DEVELOPMENT
)

# Check for SQLite development configuration
try:
    from config import USE_SQLITE, SQLITE_PATH
except ImportError:
    USE_SQLITE: bool = False
    SQLITE_PATH: Optional[str] = None

# SQLite database configuration for development environment
if IS_DEVELOPMENT and USE_SQLITE:
    logger.info(f"Using SQLite for development: {SQLITE_PATH}")
    
    # Ensure SQLite directory exists
    if SQLITE_PATH:
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    
    def get_sqlite_connection() -> sqlite3.Connection:
        """
        Create and return a SQLite database connection.
        
        Returns:
            sqlite3.Connection: SQLite database connection with row factory.
            
        Raises:
            sqlite3.Error: If connection cannot be established.
        """
        if not SQLITE_PATH:
            raise ValueError("SQLITE_PATH not configured")
            
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            # Configure connection to return dictionary-like rows
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"SQLite connection error: {e}")
            raise
    
    @contextmanager
    def db_session() -> Generator[sqlite3.Connection, None, None]:
        """
        Provide a transactional scope for SQLite database operations.
        
        Yields:
            sqlite3.Connection: Database connection with automatic 
                               commit/rollback handling.
                               
        Raises:
            sqlite3.Error: If database operation fails.
        """
        conn = None
        try:
            conn = get_sqlite_connection()
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"SQLite session error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_db() -> Generator[sqlite3.Connection, None, None]:
        """
        FastAPI dependency for SQLite database connections.
        
        Yields:
            sqlite3.Connection: Database connection for request handling.
            
        Raises:
            sqlite3.Error: If database connection fails.
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

# MySQL para producción o desarrollo con MySQL (sin pool: conexión por solicitud)
else:
    # Verificar que las variables estén definidas
    if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
        logger.error("Variables de conexión a BD incompletas o no definidas")

    # Parámetros de conexión (ajustados para RDS)
    connect_timeout_env = int(os.getenv('DB_CONNECT_TIMEOUT', '15'))
    ssl_disabled_env = os.getenv('DB_SSL_DISABLED', '').lower() in ('1', 'true', 'yes')
    ssl_ca_env = os.getenv('DB_SSL_CA')  # path to RDS CA bundle (optional)

    db_config = {
        'host': DB_HOST,
        'port': int(DB_PORT),
        'user': DB_USER,
        'password': DB_PASSWORD,
        'database': DB_NAME,
        'connect_timeout': connect_timeout_env,
        'autocommit': False,
        'raise_on_warnings': True,
    }

    # SSL configuration (optional)
    if ssl_disabled_env:
        db_config['ssl_disabled'] = True
    elif ssl_ca_env:
        db_config['ssl_ca'] = ssl_ca_env

    def _connect_with_retry(max_retries: int = 3, delay: float = 1.0):
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                conn = mysql.connector.connect(**db_config)
                if attempt > 1:
                    logger.info(f"Conexión MySQL establecida tras reintento {attempt-1}")
                return conn
            except Exception as e:
                last_err = e
                logger.warning(f"Fallo conectando a MySQL (intento {attempt}/{max_retries}): {e}")
                time.sleep(delay)
        logger.error(f"No se pudo conectar a MySQL después de {max_retries} intentos: {last_err}")
        raise last_err

    @contextmanager
    def db_session():
        """Contexto transaccional con conexión directa a MySQL (sin pool)."""
        conn = None
        try:
            conn = _connect_with_retry()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"Error en sesión de BD: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_db():
        """Dependencia de FastAPI que retorna una conexión directa (sin pool)."""
        conn = _connect_with_retry()
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

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
                    # MySQL: crear tablas solo si no existen (consultando INFORMATION_SCHEMA)
                    cursor = conn.cursor()

                    def table_info(name: str):
                        cursor.execute(
                            """
                            SELECT TABLE_NAME, TABLE_TYPE
                            FROM information_schema.TABLES
                            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                            """,
                            (name,)
                        )
                        return cursor.fetchone()

                    def create_table(name: str, ddl: str):
                        info = table_info(name)
                        if info:
                            table_name, table_type = info
                            if table_type != 'BASE TABLE':
                                logger.error(
                                    f"No se puede crear tabla '{name}': ya existe un objeto tipo {table_type}. "
                                    f"Renombra o elimina ese objeto primero."
                                )
                                return
                            logger.info(f"Tabla '{name}' ya existe. Omitiendo creación.")
                            return
                        try:
                            cursor.execute(ddl)
                            logger.info(f"Tabla '{name}' creada correctamente.")
                        except mysql.connector.Error as e:
                            if getattr(e, 'errno', None) == errorcode.ER_TABLE_EXISTS_ERROR:
                                logger.info(f"Tabla '{name}' ya existe (1050). Omitiendo.")
                            else:
                                raise

                    create_table(
                        'administradores',
                        """
                        CREATE TABLE administradores (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            nombre VARCHAR(100) NOT NULL,
                            email VARCHAR(100) UNIQUE NOT NULL,
                            hashed_password VARCHAR(255) NOT NULL,
                            es_superadmin BOOLEAN DEFAULT FALSE,
                            activo BOOLEAN DEFAULT TRUE,
                            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                            fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        )
                        """
                    )

                    create_table(
                        'sesiones_admin',
                        """
                        CREATE TABLE sesiones_admin (
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
                        """
                    )

                    create_table(
                        'contactos',
                        """
                        CREATE TABLE contactos (
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
                        """
                    )
                
                logger.info("Base de datos configurada correctamente")
                
        except Exception as e:
            logger.error(f"Error al configurar la base de datos: {e}")
            if IS_DEVELOPMENT:
                logger.warning("Error en desarrollo: la aplicación continuará sin base de datos completa")
            else:
                raise