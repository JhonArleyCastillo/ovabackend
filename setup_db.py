"""
Script para inicializar la base de datos y crear un usuario administrador.

Este script configura las tablas necesarias y crea un administrador inicial.
"""

import argparse
import sys
import os
from backend.database import setup_database, db_session
from backend.db_models import AdministradorModel

def crear_admin_inicial(nombre: str, email: str, password: str):
    """
    Crea un administrador inicial con permisos de superadmin.
    
    Args:
        nombre: Nombre del administrador.
        email: Email del administrador.
        password: Contraseña sin encriptar.
    
    Returns:
        ID del administrador creado.
    """
    try:
        # Verificar si ya existe un admin con ese email
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM administradores WHERE email = %s", (email,))
            admin_existente = cursor.fetchone()
            
        if admin_existente:
            print(f"Ya existe un administrador con el email {email}")
            return admin_existente["id"]
            
        # Crear el administrador como superadmin
        admin_id = AdministradorModel.crear(
            nombre=nombre,
            email=email,
            password=password,
            es_superadmin=True
        )
        
        print(f"Administrador creado con ID: {admin_id}")
        return admin_id
        
    except Exception as e:
        print(f"Error al crear el administrador: {e}")
        return None

def main():
    """
    Función principal que inicializa la base de datos y crea un admin inicial.
    """
    parser = argparse.ArgumentParser(description='Configuración inicial de la base de datos')
    parser.add_argument('--nombre', type=str, help='Nombre del administrador')
    parser.add_argument('--email', type=str, help='Email del administrador')
    parser.add_argument('--password', type=str, help='Contraseña del administrador')
    
    args = parser.parse_args()
    
    # Configurar la base de datos
    try:
        print("Configurando la base de datos...")
        setup_database()
        print("Base de datos configurada correctamente.")
    except Exception as e:
        print(f"Error al configurar la base de datos: {e}")
        sys.exit(1)
    
    # Crear un administrador inicial si se proporcionaron los argumentos
    if args.nombre and args.email and args.password:
        crear_admin_inicial(args.nombre, args.email, args.password)
    else:
        # Solicitar datos para crear un administrador
        print("\nCreación de administrador inicial (presiona Ctrl+C para cancelar):")
        try:
            nombre = input("Nombre: ")
            email = input("Email: ")
            password = input("Contraseña: ")
            
            if nombre and email and password:
                crear_admin_inicial(nombre, email, password)
            else:
                print("No se ha creado ningún administrador. Se requieren todos los campos.")
        except KeyboardInterrupt:
            print("\nCreación de administrador cancelada.")

if __name__ == "__main__":
    main()