"""
Script para crear un administrador en el sistema OVA.

Este script utiliza la infraestructura existente de la aplicación para crear
un usuario administrador con privilegios de superadministrador.

Uso:
    python create_admin.py --email admin@ejemplo.com --nombre "Nombre Admin" --password "contraseña"
"""

import argparse
import sys
import os

# Importaciones absolutas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar las dependencias necesarias de la aplicación
from database import db_session, setup_database
from db_models import AdministradorModel
from security_utils import get_password_hash
# Importar config para asegurarnos de que todas las variables de entorno estén disponibles
import config

def create_superadmin(email, nombre, password):
    """
    Crea un superadministrador en la base de datos.
    
    Args:
        email: Correo electrónico del administrador
        nombre: Nombre completo del administrador
        password: Contraseña en texto plano (será hasheada)
        
    Returns:
        bool: True si se creó con éxito, False en caso contrario
    """
    try:
        # Primero, verificar si ya existe un admin con este correo
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM administradores WHERE email = %s", (email,))
            existing_admin = cursor.fetchone()
            
        if existing_admin:
            print(f"Error: Ya existe un administrador con el correo '{email}'.")
            return False
        
        # Crear el superadmin usando el modelo existente
        admin_id = AdministradorModel.crear(
            nombre=nombre,
            email=email,
            password=password,
            es_superadmin=True
        )
        
        # Obtener el admin creado para mostrar información
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM administradores WHERE id = %s", (admin_id,))
            nuevo_admin = cursor.fetchone()
        
        print(f"\n¡Superadministrador creado con éxito!")
        print(f"ID: {nuevo_admin['id']}")
        print(f"Email: {nuevo_admin['email']}")
        print(f"Nombre: {nuevo_admin['nombre']}")
        print(f"Es superadmin: Sí")
        
        return True
    except Exception as e:
        print(f"Error al crear el superadministrador: {str(e)}")
        return False

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Crea un superadministrador en el sistema")
    parser.add_argument("--email", required=True, help="Correo electrónico del superadministrador")
    parser.add_argument("--nombre", required=True, help="Nombre completo del superadministrador")
    parser.add_argument("--password", required=True, help="Contraseña del superadministrador")
    
    args = parser.parse_args()
    
    # Asegurar que la base de datos esté correctamente configurada
    try:
        print("Verificando la configuración de la base de datos...")
        setup_database()
        print("Base de datos verificada correctamente.")
    except Exception as e:
        print(f"Error al verificar la base de datos: {str(e)}")
        sys.exit(1)
    
    # Crear el superadmin
    success = create_superadmin(args.email, args.nombre, args.password)
    
    # Salir con código de estado apropiado
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()