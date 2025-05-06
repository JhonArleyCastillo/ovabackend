#!/usr/bin/env python
"""
Script para configurar el entorno de desarrollo de OVA Backend.

Este script ayuda a verificar y configurar la base de datos para desarrollo,
permitiendo elegir entre MySQL local o SQLite.
"""

import os
import sys
import shutil
import subprocess
from dotenv import load_dotenv

def banner(message):
    """Muestra un banner con el mensaje dado."""
    width = len(message) + 4
    print("=" * width)
    print(f"| {message} |")
    print("=" * width)
    print()

def check_mysql_connection():
    """Verifica si podemos conectarnos a MySQL con las credenciales actuales."""
    try:
        import mysql.connector
        from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
        
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.close()
        return True
    except Exception as e:
        print(f"No se pudo conectar a MySQL: {e}")
        return False

def setup_env_file():
    """Configura el archivo .env para desarrollo."""
    dotenv_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    example_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example')

    if os.path.exists(dotenv_file):
        print("Archivo .env ya existe.")
        overwrite = input("¿Deseas sobrescribirlo con la configuración de desarrollo? (s/N): ")
        if overwrite.lower() != 's':
            return
    
    if os.path.exists(example_file):
        shutil.copy(example_file, dotenv_file)
        print(f"Archivo .env creado basado en .env.example")
    else:
        # Crear un archivo .env básico
        with open(dotenv_file, 'w') as f:
            f.write("ENVIRONMENT=development\n")
            f.write("USE_SQLITE=true\n")
            f.write("JWT_SECRET_KEY=desarrollo_local\n")
            f.write("ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000\n")
        print(f"Archivo .env básico creado")

def setup_database_choice():
    """Permite al usuario elegir qué base de datos usar."""
    banner("Configuración de Base de Datos")
    print("Opciones disponibles:")
    print("1. MySQL local")
    print("2. SQLite (más simple, no requiere servidor)")
    print()
    
    choice = input("Elije una opción (1/2): ")
    
    dotenv_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(dotenv_file):
        setup_env_file()
    
    if choice == "1":
        # Configurar para MySQL
        mysql_host = input("Host MySQL (default: localhost): ") or "localhost"
        mysql_port = input("Puerto MySQL (default: 3306): ") or "3306"
        mysql_user = input("Usuario MySQL (default: root): ") or "root"
        mysql_password = input("Contraseña MySQL: ")
        mysql_db = input("Nombre de base de datos (default: ovaweb_dev): ") or "ovaweb_dev"
        
        # Actualizar archivo .env
        env_content = []
        with open(dotenv_file, 'r') as f:
            env_content = f.readlines()
        
        with open(dotenv_file, 'w') as f:
            for line in env_content:
                if line.startswith("USE_SQLITE="):
                    f.write("USE_SQLITE=false\n")
                elif line.startswith("DB_HOST="):
                    f.write(f"DB_HOST={mysql_host}\n")
                elif line.startswith("DB_PORT="):
                    f.write(f"DB_PORT={mysql_port}\n")
                elif line.startswith("DB_USER="):
                    f.write(f"DB_USER={mysql_user}\n")
                elif line.startswith("DB_PASSWORD="):
                    f.write(f"DB_PASSWORD={mysql_password}\n")
                elif line.startswith("DB_NAME="):
                    f.write(f"DB_NAME={mysql_db}\n")
                else:
                    f.write(line)
    
    elif choice == "2":
        # Configurar para SQLite
        env_content = []
        with open(dotenv_file, 'r') as f:
            env_content = f.readlines()
        
        with open(dotenv_file, 'w') as f:
            for line in env_content:
                if line.startswith("USE_SQLITE="):
                    f.write("USE_SQLITE=true\n")
                else:
                    f.write(line)
    
    else:
        print("Opción no válida. Saliendo.")
        return
    
    # Recargar variables de entorno
    load_dotenv(dotenv_file, override=True)
    
    print("Configuración guardada en .env")

def test_database_setup():
    """Intenta configurar la base de datos para verificar si funciona."""
    banner("Probando configuración de Base de Datos")
    try:
        # Importar solo después de que se hayan actualizado las variables de entorno
        from config import IS_DEVELOPMENT, USE_SQLITE
        from database import setup_database
        
        print(f"Entorno: {'Desarrollo' if IS_DEVELOPMENT else 'Producción'}")
        print(f"Usando SQLite: {'Sí' if USE_SQLITE else 'No'}")
        
        setup_database()
        print("✅ Base de datos configurada correctamente.")
        return True
    except Exception as e:
        print(f"❌ Error al configurar la base de datos: {e}")
        return False

def show_help_for_missing_mysql():
    """Muestra ayuda si MySQL no está instalado o configurado."""
    banner("Ayuda para configuración de MySQL")
    print("Parece que tienes problemas con la conexión a MySQL.")
    print("\nOpciones:")
    print("1. Instalar MySQL localmente:")
    print("   - Windows: Descargar MySQL Installer desde https://dev.mysql.com/downloads/installer/")
    print("   - macOS: `brew install mysql`")
    print("   - Linux: `sudo apt install mysql-server`")
    print("\n2. Usar Docker (recomendado para desarrollo):")
    print("   docker run --name mysql-ovaweb -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=ovaweb_dev -p 3306:3306 -d mysql:8.0")
    print("\n3. Usar SQLite (más simple):")
    print("   Selecciona la opción 2 (SQLite) en el menú de configuración\n")

def main():
    """Función principal del script."""
    banner("Configuración del Entorno de Desarrollo OVA")
    
    # Asegurarse de que estamos en el directorio correcto
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'main.py')):
        print("Error: Este script debe ejecutarse desde el directorio backend/")
        sys.exit(1)
    
    # Configurar archivo .env si no existe
    dotenv_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(dotenv_file):
        setup_env_file()
        print("Creado archivo .env inicial")
    
    # Opciones para el usuario
    print("1. Configurar base de datos")
    print("2. Probar configuración actual")
    print("3. Iniciar servidor de desarrollo")
    print("4. Salir")
    
    choice = input("\nSelecciona una opción (1-4): ")
    
    if choice == "1":
        setup_database_choice()
        test_database_setup()
    
    elif choice == "2":
        success = test_database_setup()
        if not success:
            # Verificar si el problema es MySQL
            from config import USE_SQLITE
            if not USE_SQLITE and not check_mysql_connection():
                show_help_for_missing_mysql()
    
    elif choice == "3":
        try:
            print("Iniciando servidor de desarrollo...")
            subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"])
        except KeyboardInterrupt:
            print("\nServidor detenido.")
    
    elif choice == "4":
        print("Saliendo.")
    
    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()