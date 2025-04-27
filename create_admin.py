"""
Script para crear un administrador en el sistema OVA.

Este script inicializa la base de datos (si es necesario) y crea un usuario
administrador con privilegios de superadministrador.

Uso:
    python create_admin.py --email admin@ejemplo.com --nombre "Nombre Admin" --password "contraseña"
"""

import argparse
import sys
import os
import datetime
import mysql.connector
import hashlib
import secrets
from security_utils import get_password_hash  # Importamos la función de security_utils

# Importaciones absolutas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Utilizamos valores específicos para la producción en RDS
# En lugar de usar config.py directamente
DB_HOST = os.getenv("DB_HOST")
DB_PORT = 3306  # Ya como entero
DB_USER = "root"  # Debes usar tu usuario de RDS real aquí
DB_PASSWORD = "contraseña"  # Debes usar tu contraseña de RDS real aquí
DB_NAME = "basedatos"  # Debes usar el nombre de tu base de datos real aquí

def init_db():
    """Inicializa la base de datos y crea las tablas."""
    print(f"Inicializando base de datos con host: {DB_HOST}, puerto: {DB_PORT}, base de datos: {DB_NAME}")
    
    try:
        # Verificar conexión - Usamos los valores definidos arriba
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,  # Ya está como entero
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = cnx.cursor()
        
        # No necesitamos crear la base de datos en RDS, solo seleccionarla
        cursor.execute(f"USE {DB_NAME}")
        
        # Crear tablas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS administradores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            nombre VARCHAR(100),
            hashed_password VARCHAR(255),
            es_superadmin BOOLEAN DEFAULT FALSE,
            activo BOOLEAN DEFAULT TRUE,
            INDEX (email)
        )
        """)
        
        # Verificar tablas creadas
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        print(f"Tablas en la base de datos: {', '.join(tables)}")
        
        return cnx
    except mysql.connector.Error as err:
        print(f"Error al inicializar la base de datos: {err}")
        sys.exit(1)

def create_superadmin(cnx, email, nombre, password):
    """
    Crea un superadministrador en la base de datos.
    
    Args:
        cnx: Conexión a MySQL
        email: Correo electrónico del administrador
        nombre: Nombre completo del administrador
        password: Contraseña en texto plano (será hasheada)
    """
    cursor = cnx.cursor(dictionary=True)
    
    try:
        # Verificar si ya existe un admin con este correo
        cursor.execute("SELECT * FROM administradores WHERE email = %s", (email,))
        existing_admin = cursor.fetchone()
        if existing_admin:
            print(f"Error: Ya existe un administrador con el correo '{email}'.")
            return False
        
        # Hashear la contraseña usando nuestra nueva función
        hashed_password = get_password_hash(password)
        
        # Crear el superadmin
        cursor.execute("""
        INSERT INTO administradores (email, nombre, hashed_password, es_superadmin, activo)
        VALUES (%s, %s, %s, %s, %s)
        """, (email, nombre, hashed_password, True, True))
        
        cnx.commit()
        nuevo_admin_id = cursor.lastrowid
        
        # Obtener el admin creado
        cursor.execute("SELECT * FROM administradores WHERE id = %s", (nuevo_admin_id,))
        nuevo_admin = cursor.fetchone()
        
        print(f"\n¡Superadministrador creado con éxito!")
        print(f"ID: {nuevo_admin['id']}")
        print(f"Email: {nuevo_admin['email']}")
        print(f"Nombre: {nuevo_admin['nombre']}")
        print(f"Es superadmin: Sí")
        
        return True
    except Exception as e:
        print(f"Error al crear el superadministrador: {str(e)}")
        cnx.rollback()
        return False
    finally:
        cursor.close()

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Crea un superadministrador en el sistema")
    parser.add_argument("--email", required=True, help="Correo electrónico del superadministrador")
    parser.add_argument("--nombre", required=True, help="Nombre completo del superadministrador")
    parser.add_argument("--password", required=True, help="Contraseña del superadministrador")
    
    args = parser.parse_args()
    
    # Inicializar la base de datos
    cnx = init_db()
    
    # Crear el superadmin
    success = create_superadmin(cnx, args.email, args.nombre, args.password)
    
    # Cerrar la conexión
    cnx.close()
    
    # Salir con código de estado apropiado
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()