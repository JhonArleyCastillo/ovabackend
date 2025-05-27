"""
Modelos de base de datos para la aplicación.

Este archivo contiene clases para interactuar con las tablas de la base de datos:
- AdministradorModel: para gestionar administradores
- SesionAdminModel: para gestionar sesiones de administradores
- ContactoModel: para gestionar mensajes de contacto
"""

from typing import List, Dict, Any, Optional
import datetime
from backend.database import db_session
from backend.security_utils import get_password_hash, verify_password
import mysql.connector

class AdministradorModel:
    """
    Modelo para interactuar con la tabla de administradores.
    """
    
    @staticmethod
    def crear(nombre: str, email: str, password: str, es_superadmin: bool = False) -> int:
        """
        Crea un nuevo administrador.
        
        Args:
            nombre: Nombre del administrador.
            email: Email del administrador.
            password: Contraseña sin encriptar.
            es_superadmin: Si es un superadministrador.
            
        Returns:
            ID del administrador creado.
        """
        hashed_password = get_password_hash(password)
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO administradores 
            (nombre, email, hashed_password, es_superadmin) 
            VALUES (%s, %s, %s, %s)
            """, (nombre, email, hashed_password, es_superadmin))
            
            admin_id = cursor.lastrowid
            return admin_id
    
    @staticmethod
    def obtener_por_id(admin_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un administrador por su ID.
        
        Args:
            admin_id: ID del administrador.
            
        Returns:
            Diccionario con los datos del administrador o None si no existe.
        """
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT id, nombre, email, es_superadmin, activo, 
                   fecha_creacion, fecha_actualizacion
            FROM administradores 
            WHERE id = %s
            """, (admin_id,))
            
            admin = cursor.fetchone()
            
            if admin:
                admin['es_superadmin'] = bool(admin['es_superadmin'])
                admin['activo'] = bool(admin['activo'])
                
            return admin
    
    @staticmethod
    def obtener_por_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un administrador por su email.
        
        Args:
            email: Email del administrador.
            
        Returns:
            Diccionario con los datos del administrador o None si no existe.
        """
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT id, nombre, email, hashed_password, es_superadmin, activo, 
                   fecha_creacion, fecha_actualizacion
            FROM administradores 
            WHERE email = %s
            """, (email,))
            
            admin = cursor.fetchone()
            
            if admin:
                admin['es_superadmin'] = bool(admin['es_superadmin'])
                admin['activo'] = bool(admin['activo'])
                
            return admin
    
    @staticmethod
    def listar(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Lista todos los administradores.
        
        Args:
            skip: Número de registros a saltar.
            limit: Número máximo de registros a devolver.
            
        Returns:
            Lista de administradores.
        """
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT id, nombre, email, es_superadmin, activo, 
                   fecha_creacion, fecha_actualizacion
            FROM administradores
            ORDER BY fecha_creacion DESC
            LIMIT %s, %s
            """, (skip, limit))
            
            admins = cursor.fetchall()
            
            for admin in admins:
                admin['es_superadmin'] = bool(admin['es_superadmin'])
                admin['activo'] = bool(admin['activo'])
                
            return admins
    
    @staticmethod
    def actualizar(admin_id: int, **kwargs) -> bool:
        """
        Actualiza los datos de un administrador.
        
        Args:
            admin_id: ID del administrador.
            **kwargs: Campos a actualizar.
            
        Returns:
            True si se actualizó correctamente, False si no.
        """
        campos_permitidos = {
            'nombre': str, 
            'email': str, 
            'es_superadmin': bool,
            'activo': bool
        }
        
        # Filtrar campos no permitidos
        campos_actualizar = {}
        for campo, valor in kwargs.items():
            if campo in campos_permitidos:
                campos_actualizar[campo] = valor
        
        if not campos_actualizar:
            return False
        
        # Construir la consulta SQL
        sql_campos = ", ".join([f"{campo} = %s" for campo in campos_actualizar.keys()])
        sql = f"UPDATE administradores SET {sql_campos} WHERE id = %s"
        
        # Valores para la consulta
        valores = list(campos_actualizar.values())
        valores.append(admin_id)
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, valores)
            return cursor.rowcount > 0
    
    @staticmethod
    def cambiar_password(admin_id: int, nueva_password: str) -> bool:
        """
        Cambia la contraseña de un administrador.
        
        Args:
            admin_id: ID del administrador.
            nueva_password: Nueva contraseña sin encriptar.
            
        Returns:
            True si se cambió correctamente, False si no.
        """
        hashed_password = get_password_hash(nueva_password)
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE administradores SET hashed_password = %s WHERE id = %s
            """, (hashed_password, admin_id))
            return cursor.rowcount > 0
    
    @staticmethod
    def eliminar(admin_id: int) -> bool:
        """
        Elimina un administrador.
        
        Args:
            admin_id: ID del administrador.
            
        Returns:
            True si se eliminó correctamente, False si no.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM administradores WHERE id = %s", (admin_id,))
            return cursor.rowcount > 0

class SesionAdminModel:
    """
    Modelo para interactuar con la tabla de sesiones de administradores.
    """
    
    @staticmethod
    def crear(admin_id: int, token: str, fecha_expiracion: datetime.datetime,
             ip_address: str = None, navegador: str = None, activa: bool = True) -> int:
        """
        Crea una nueva sesión de administrador.
        
        Args:
            admin_id: ID del administrador.
            token: Token de la sesión.
            fecha_expiracion: Fecha de expiración.
            ip_address: Dirección IP.
            navegador: Información del navegador.
            activa: Si la sesión está activa.
            
        Returns:
            ID de la sesión creada.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO sesiones_admin 
            (admin_id, token, fecha_expiracion, ip_address, navegador, activa) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (admin_id, token, fecha_expiracion, ip_address, navegador, activa))
            
            session_id = cursor.lastrowid
            return session_id
    
    @staticmethod
    def obtener_por_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una sesión por su token.
        
        Args:
            token: Token de la sesión.
            
        Returns:
            Diccionario con los datos de la sesión o None si no existe.
        """
        sql = """
        SELECT s.id, s.admin_id, s.token, s.fecha_inicio, s.fecha_expiracion, 
               s.ip_address, s.navegador, s.activa, 
               a.email as admin_email, a.nombre as admin_nombre, 
               a.es_superadmin as admin_es_superadmin
        FROM sesiones_admin s
        JOIN administradores a ON s.admin_id = a.id
        WHERE s.token = %s
        """
        
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (token,))
            resultado = cursor.fetchone()
            
            if resultado:
                resultado['activa'] = bool(resultado['activa'])
                resultado['admin_es_superadmin'] = bool(resultado['admin_es_superadmin'])
                
            return resultado
    
    @staticmethod
    def obtener_por_id(session_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una sesión por su ID.
        
        Args:
            session_id: ID de la sesión.
            
        Returns:
            Diccionario con los datos de la sesión o None si no existe.
        """
        sql = """
        SELECT s.id, s.admin_id, s.token, s.fecha_inicio, s.fecha_expiracion, 
               s.ip_address, s.navegador, s.activa, 
               a.email as admin_email, a.nombre as admin_nombre, 
               a.es_superadmin as admin_es_superadmin
        FROM sesiones_admin s
        JOIN administradores a ON s.admin_id = a.id
        WHERE s.id = %s
        """
        
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (session_id,))
            resultado = cursor.fetchone()
            
            if resultado:
                resultado['activa'] = bool(resultado['activa'])
                resultado['admin_es_superadmin'] = bool(resultado['admin_es_superadmin'])
                
            return resultado
    
    @staticmethod
    def obtener_sesiones_activas(admin_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene todas las sesiones activas.
        
        Args:
            admin_id: Filtrar por ID de administrador (opcional).
            
        Returns:
            Lista de sesiones activas.
        """
        sql_base = """
        SELECT s.id, s.admin_id, s.token, s.fecha_inicio, s.fecha_expiracion, 
               s.ip_address, s.navegador, s.activa, 
               a.email as admin_email, a.nombre as admin_nombre
        FROM sesiones_admin s
        JOIN administradores a ON s.admin_id = a.id
        WHERE s.activa = %s AND s.fecha_expiracion > NOW()
        """
        
        if admin_id is not None:
            sql = f"{sql_base} AND s.admin_id = %s ORDER BY s.fecha_inicio DESC"
            params = (True, admin_id)
        else:
            sql = f"{sql_base} ORDER BY s.fecha_inicio DESC"
            params = (True,)
            
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            sesiones = cursor.fetchall()
            
            for sesion in sesiones:
                sesion['activa'] = bool(sesion['activa'])
                
            return sesiones
    
    @staticmethod
    def invalidar_sesion(token: str) -> bool:
        """
        Invalida una sesión por su token.
        
        Args:
            token: Token de la sesión.
            
        Returns:
            True si se invalidó correctamente, False si no.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE sesiones_admin SET activa = %s WHERE token = %s
            """, (False, token))
            return cursor.rowcount > 0
    
    @staticmethod
    def invalidar_todas_sesiones(admin_id: int) -> int:
        """
        Invalida todas las sesiones de un administrador.
        
        Args:
            admin_id: ID del administrador.
            
        Returns:
            Número de sesiones invalidadas.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE sesiones_admin SET activa = %s 
            WHERE admin_id = %s AND activa = %s
            """, (False, admin_id, True))
            return cursor.rowcount
    
    @staticmethod
    def limpiar_sesiones_expiradas() -> int:
        """
        Marca como inactivas todas las sesiones expiradas.
        
        Returns:
            Número de sesiones limpiadas.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE sesiones_admin SET activa = %s 
            WHERE fecha_expiracion < NOW() AND activa = %s
            """, (False, True))
            return cursor.rowcount

class ContactoModel:
    """
    Modelo para interactuar con la tabla de contactos.
    """
    
    @staticmethod
    def crear(nombre: str, email: str, asunto: str, mensaje: str) -> int:
        """
        Crea un nuevo mensaje de contacto.
        
        Args:
            nombre: Nombre de la persona.
            email: Email de la persona.
            asunto: Asunto del mensaje.
            mensaje: Contenido del mensaje.
            
        Returns:
            ID del contacto creado.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO contactos 
            (nombre, email, asunto, mensaje) 
            VALUES (%s, %s, %s, %s)
            """, (nombre, email, asunto, mensaje))
            
            contacto_id = cursor.lastrowid
            return contacto_id
    
    @staticmethod
    def obtener_por_id(contacto_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un contacto por su ID.
        
        Args:
            contacto_id: ID del contacto.
            
        Returns:
            Diccionario con los datos del contacto o None si no existe.
        """
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
            SELECT id, nombre, email, asunto, mensaje, fecha_envio, leido, respondido
            FROM contactos 
            WHERE id = %s
            """, (contacto_id,))
            
            contacto = cursor.fetchone()
            
            if contacto:
                contacto['leido'] = bool(contacto['leido'])
                contacto['respondido'] = bool(contacto['respondido'])
                
            return contacto
    
    @staticmethod
    def listar(skip: int = 0, limit: int = 100, solo_no_leidos: bool = False) -> List[Dict[str, Any]]:
        """
        Lista todos los mensajes de contacto.
        
        Args:
            skip: Número de registros a saltar.
            limit: Número máximo de registros a devolver.
            solo_no_leidos: Si es True, solo devuelve mensajes no leídos.
            
        Returns:
            Lista de mensajes de contacto.
        """
        sql_base = """
        SELECT id, nombre, email, asunto, mensaje, fecha_envio, leido, respondido
        FROM contactos
        """
        
        if solo_no_leidos:
            sql = f"{sql_base} WHERE leido = 0 ORDER BY fecha_envio DESC LIMIT %s, %s"
        else:
            sql = f"{sql_base} ORDER BY fecha_envio DESC LIMIT %s, %s"
            
        with db_session() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (skip, limit))
            contactos = cursor.fetchall()
            
            for contacto in contactos:
                contacto['leido'] = bool(contacto['leido'])
                contacto['respondido'] = bool(contacto['respondido'])
                
            return contactos
    
    @staticmethod
    def marcar_como_leido(contacto_id: int, leido: bool = True) -> bool:
        """
        Marca un mensaje como leído o no leído.
        
        Args:
            contacto_id: ID del contacto.
            leido: Si el mensaje ha sido leído.
            
        Returns:
            True si se actualizó correctamente, False si no.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE contactos SET leido = %s WHERE id = %s
            """, (leido, contacto_id))
            return cursor.rowcount > 0
    
    @staticmethod
    def marcar_como_respondido(contacto_id: int, respondido: bool = True) -> bool:
        """
        Marca un mensaje como respondido o no respondido.
        
        Args:
            contacto_id: ID del contacto.
            respondido: Si el mensaje ha sido respondido.
            
        Returns:
            True si se actualizó correctamente, False si no.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE contactos SET respondido = %s WHERE id = %s
            """, (respondido, contacto_id))
            return cursor.rowcount > 0
    
    @staticmethod
    def eliminar(contacto_id: int) -> bool:
        """
        Elimina un mensaje de contacto.
        
        Args:
            contacto_id: ID del contacto.
            
        Returns:
            True si se eliminó correctamente, False si no.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contactos WHERE id = %s", (contacto_id,))
            return cursor.rowcount > 0