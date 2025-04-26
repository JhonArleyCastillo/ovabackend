"""
Utilidades y herramientas para la aplicación.

Este archivo contiene funciones de utilidad para diversas tareas como
configuración inicial, herramientas de mantenimiento, etc.
"""

import base64
import numpy as np
import cv2
import logging
import argparse
import sys
from database import db_session
from db_models import AdministradorModel
from auth import get_password_hash

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def decode_base64_image(base64_string: str) -> np.ndarray | None:
    """Decodifica una imagen en formato base64 a un array numpy."""
    try:
        # Eliminar prefijo si existe
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
            
        image_bytes = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("La imagen no pudo ser decodificada por OpenCV")
            return None
        return img
    except Exception as e:
        logger.error(f"Error al decodificar imagen base64: {e}")
        return None

def encode_audio_to_base64(audio_bytes: bytes) -> str:
    """Codifica bytes de audio a formato base64."""
    try:
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Error al codificar audio a base64: {e}")
        return ""

def create_error_response(message: str, status_code: int = 500) -> tuple[dict, int]:
    """Crea una respuesta JSON de error estándar."""
    return {"error": message, "status": "error"}, status_code

def validate_image_magic_bytes(image_data):
    """
    Valida que un archivo sea realmente una imagen mediante magic bytes
    
    Args:
        image_data (bytes): Datos binarios de la imagen
        
    Returns:
        tuple: (es_valido, tipo_detectado)
    """
    if not image_data or len(image_data) < 12:
        return False, None
    
    # Definir las firmas de magic bytes para los tipos permitidos
    signatures = {
        'image/jpeg': [(b'\xFF\xD8\xFF', 0)],
        'image/png': [(b'\x89PNG\r\n\x1A\n', 0)],
        'image/webp': [(b'RIFF', 0), (b'WEBP', 8)]
    }
    
    # Verificar cada tipo de imagen
    for mime_type, sig_list in signatures.items():
        valid = True
        for signature, offset in sig_list:
            if len(image_data) < offset + len(signature):
                valid = False
                break
                
            if image_data[offset:offset+len(signature)] != signature:
                valid = False
                break
                
        if valid:
            logger.debug(f"Tipo de imagen detectado por magic bytes: {mime_type}")
            return True, mime_type
    
    logger.warning("Archivo no es una imagen válida según magic bytes")
    return False, None

def crear_admin_inicial(email: str, nombre: str, password: str):
    """
    Crea el administrador inicial con privilegios de superadmin.
    
    Args:
        email: Email del administrador
        nombre: Nombre del administrador
        password: Contraseña del administrador
    
    Returns:
        bool: True si se creó correctamente, False en caso contrario
    """
    try:
        # Verificar si ya existe un administrador con ese email
        admin_existente = AdministradorModel.obtener_por_email(email)
        
        if admin_existente:
            logger.warning(f"Ya existe un administrador con el email {email}")
            return False
        
        # Crear el nuevo administrador
        hashed_password = get_password_hash(password)
        nuevo_admin_id = AdministradorModel.crear(
            email=email,
            nombre=nombre,
            hashed_password=hashed_password,
            es_superadmin=True,  # Este será un superadmin
            activo=True
        )
        
        logger.info(f"Administrador {email} creado exitosamente con ID {nuevo_admin_id}")
        return True
            
    except Exception as e:
        logger.error(f"Error al crear el administrador inicial: {e}")
        return False

def main():
    """Función principal para inicializar la base de datos con un administrador."""
    parser = argparse.ArgumentParser(description="Herramienta para gestionar la aplicación")
    
    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponibles")
    
    # Comando para crear un administrador inicial
    create_admin_parser = subparsers.add_parser("crear-admin", help="Crea un administrador inicial")
    create_admin_parser.add_argument("--email", required=True, help="Email del administrador")
    create_admin_parser.add_argument("--nombre", required=True, help="Nombre del administrador")
    create_admin_parser.add_argument("--password", required=True, help="Contraseña del administrador")
    
    args = parser.parse_args()
    
    if args.comando == "crear-admin":
        exito = crear_admin_inicial(args.email, args.nombre, args.password)
        if exito:
            logger.info("Administrador creado exitosamente")
        else:
            logger.error("Error al crear el administrador")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
