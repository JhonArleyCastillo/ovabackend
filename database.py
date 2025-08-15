"""
Configuración y manejo de conexiones a la base de datos.

Este módulo es el corazón de las conexiones de BD. Como desarrollador fullstack,
aquí configuras si usar SQLite (perfecto para desarrollo local) o MySQL 
(para producción). Incluye pooling de conexiones y manejo automático de 
transacciones para que no tengas que preocuparte por cerrar conexiones.

Configuración típica:
- Desarrollo: SQLite (archivo local, sin configuración)
- Producción: MySQL (con pooling y reconexión automática)
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

# Logger para este módulo
logger = logging.getLogger(__name__)

# Importamos configuración desde config.py
try:
    # Cuando se importa como parte del paquete ovabackend
    from .config import (
        DB_HOST,
        DB_PORT,
        DB_USER,
        DB_PASSWORD,
        DB_NAME,
        IS_DEVELOPMENT,
    )
except ImportError:
    # Cuando se importa directamente (fallback)
    from config import (
        DB_HOST,
        DB_PORT,
        DB_USER,
        DB_PASSWORD,
        DB_NAME,
        IS_DEVELOPMENT,
    )

# Verificamos configuración SQLite
try:
    from .config import USE_SQLITE, SQLITE_PATH
except ImportError:
    try:
        from config import USE_SQLITE, SQLITE_PATH
    except ImportError:
        USE_SQLITE: bool = False
        SQLITE_PATH: Optional[str] = None

# ===== Configuración SQLite para desarrollo =====
if IS_DEVELOPMENT and USE_SQLITE:
    logger.info(f"🗃️ Usando SQLite para desarrollo: {SQLITE_PATH}")
    
    # Nos aseguramos de que el directorio existe
    if SQLITE_PATH:
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    
    def get_sqlite_connection() -> sqlite3.Connection:
        """
        Crea una conexión SQLite.
        
        SQLite es genial para desarrollo porque no necesitas instalar MySQL,
        solo crea un archivo local y listo.
        
        Returns:
            sqlite3.Connection: Conexión configurada para devolver filas como diccionarios
            
        Raises:
            sqlite3.Error: Si no puede conectar (archivo corrupto, permisos, etc.)
        """
        if not SQLITE_PATH:
            raise ValueError("SQLITE_PATH no está configurado - revisa config.py")
            
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            # Configuramos para que las filas se comporten como diccionarios (más fácil de usar)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error conectando SQLite: {e}")
            raise
    
    @contextmanager
    def db_session() -> Generator[sqlite3.Connection, None, None]:
        """
        Maneja automáticamente las transacciones SQLite.
        
        Esto es súper útil porque si algo falla, hace rollback automático.
        Si todo va bien, hace commit automático. ¡No más olvidar cerrar conexiones!
        
        Uso típico:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ...")
            # Si llega aquí sin errores, hace commit automático
            # Si hay excepción, hace rollback automático
        
        Yields:
            sqlite3.Connection: Conexión con manejo automático de transacciones
                               
        Raises:
            sqlite3.Error: Si falla alguna operación de BD
        """
        conn = None
        try:
            conn = get_sqlite_connection()
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error en sesión SQLite: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_db() -> Generator[sqlite3.Connection, None, None]:
        """
        Dependencia de FastAPI para conexiones SQLite.
        
        Esta función es la que FastAPI usa automáticamente cuando pones
        'db: Depends(get_db)' en los endpoints. Maneja todo el ciclo de vida
        de la conexión: abrir, usar, commit/rollback, cerrar.
        
        Yields:
            sqlite3.Connection: Conexión lista para usar en endpoints
            
        Raises:
            sqlite3.Error: Si falla la conexión o alguna operación
        """
        conn = None
        try:
            conn = get_sqlite_connection()
            # Configuramos para devolver filas como diccionarios (más fácil en los endpoints)
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
    
    # Objeto ficticio para compatibilidad con el código MySQL
    connection_pool = True

    def setup_database():
        """
        Configura el esquema SQLite básico compatible con MySQL de producción.
        
        Crea todas las tablas necesarias para que la app funcione. Es seguro
        llamarla varias veces porque usa CREATE IF NOT EXISTS.
        
        Esto es súper útil porque en desarrollo no necesitas configurar MySQL,
        solo corres esto una vez y ya tienes toda la estructura de BD.
        """
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                
                # Tabla de administradores (para login del admin panel)
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
                
                # Tabla de sesiones admin (para manejar tokens JWT)
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_token ON sesiones_admin(token)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_id ON sesiones_admin(admin_id)")
                
                # Tabla de contactos (para el formulario de contacto)
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON contactos(email)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fecha_envio ON contactos(fecha_envio)")
                logger.info("✅ Esquema SQLite configurado correctamente")
        except Exception as e:
            logger.error(f"Error configurando SQLite: {e}")
            raise

# ===== MySQL para producción (o desarrollo avanzado) =====
else:
    # Verificamos que todas las variables estén configuradas
    if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
        logger.error("🚨 Variables de conexión MySQL incompletas - revisa DB_HOST, DB_USER, etc.")

    # Parámetros de conexión (optimizados para RDS y conexiones cloud)
    connect_timeout_env = int(os.getenv('DB_CONNECT_TIMEOUT', '15'))
    ssl_disabled_env = os.getenv('DB_SSL_DISABLED', '').lower() in ('1', 'true', 'yes')
    ssl_ca_env = os.getenv('DB_SSL_CA')  # Ruta al bundle CA de RDS (opcional)

    db_config = {
        'host': DB_HOST,
        'port': int(DB_PORT),
        'user': DB_USER,
        'password': DB_PASSWORD,
        'database': DB_NAME,
        'connect_timeout': connect_timeout_env,
        'autocommit': False,  # Manejamos transacciones manualmente
        'raise_on_warnings': True,
    }

    # Configuración SSL (útil para RDS y conexiones seguras)
    if ssl_disabled_env:
        db_config['ssl_disabled'] = True
        logger.info("SSL deshabilitado para MySQL")
    elif ssl_ca_env:
        db_config['ssl_ca'] = ssl_ca_env
        logger.info(f"Usando certificado SSL: {ssl_ca_env}")

    def _connect_with_retry(max_retries: int = 3, delay: float = 1.0):
        """
        Conecta a MySQL con reintentos automáticos.
        
        Esto es súper útil porque las conexiones de red pueden fallar temporalmente,
        especialmente con bases de datos en la nube como RDS.
        """
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                conn = mysql.connector.connect(**db_config)
                if attempt > 1:
                    logger.info(f"✅ Conexión MySQL establecida tras {attempt-1} reintentos")
                return conn
            except Exception as e:
                last_err = e
                logger.warning(f"⚠️ Fallo conectando MySQL (intento {attempt}/{max_retries}): {e}")
                time.sleep(delay)
        logger.error(f"🚨 No se pudo conectar a MySQL después de {max_retries} intentos: {last_err}")
        raise last_err

    @contextmanager
    def db_session():
        """
        Contexto transaccional con conexión directa a MySQL.
        
        A diferencia de SQLite, aquí no usamos pooling para mantenerlo simple.
        Cada sesión abre su propia conexión, hace su trabajo, y la cierra.
        """
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
                    pass  # Si el rollback falla, no hay mucho que hacer
            logger.error(f"Error en sesión MySQL: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass  # Si el close falla, tampoco podemos hacer mucho

    def get_db():
        """
        Dependencia de FastAPI para conexiones MySQL directas.
        
        Esto es lo que FastAPI usa cuando pones 'db: Depends(get_db)' en endpoints.
        Abre conexión, la usa, hace commit/rollback, y la cierra automáticamente.
        """
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
        Inicialización de base de datos para entornos MySQL sin creación de tablas.

        Nota: La creación/gestión del esquema MySQL ha sido deshabilitada explícitamente
        porque las tablas ya existen y son gestionadas externamente (p. ej., por
        migraciones o un DBA). Esta función realiza, como máximo, una verificación
        ligera de conectividad para registrar el estado.
        """
        try:
            with db_session() as conn:
                logger.info("⏭️ Omitiendo creación/verificación de tablas MySQL; se asume que el esquema ya existe.")
                # Verificación opcional de conectividad
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    _ = cursor.fetchone()
                except Exception as ping_err:
                    logger.debug(f"Ping MySQL falló (no crítico): {ping_err}")
                logger.info("✅ Conexión MySQL verificada (sin cambios de esquema)")
        except Exception as e:
            logger.error(f"Error al verificar la base de datos: {e}")
            if IS_DEVELOPMENT:
                logger.warning("Entorno de desarrollo: la aplicación continuará incluso sin conexión MySQL")
            # En producción, no forzamos la creación ni detenemos la app aquí según solicitud