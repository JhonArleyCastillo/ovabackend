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
from bcrypt import bcrypt  # Cambiado de passlib a bcrypt

# Importaciones absolutas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
from db_models import AdministradorModel

def get_password_hash(password: str) -> str:
    """Genera un hash seguro de la contraseña."""
    # Convertir password a bytes si es string
    password_bytes = password.encode('utf-8') if isinstance(password, str) else password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Devolver como string para almacenar en la base de datos
    return hashed.decode('utf-8') if isinstance(hashed, bytes) else hashed

def init_db():
    """Inicializa la base de datos y crea las tablas."""
    print(f"Inicializando base de datos con host: {DB_HOST}, puerto: {DB_PORT}, base de datos: {DB_NAME}")
    
    try:
        # Verificar conexión
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = cnx.cursor()
        
        # Crear la base de datos si no existe
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        # Seleccionar la base de datos
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
        
        # Hashear la contraseña
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