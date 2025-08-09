from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json
import uuid
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import services and utilities
from services.chat_service import get_llm_response
from utils import create_error_response
from routes import WS_CHAT
from models import TextMessage, ErrorMessage, ConnectionMessage, TypingMessage, MessageType
from common.router_utils import handle_errors

logger = logging.getLogger(__name__)
router = APIRouter()

# Audio WebSocket endpoint removed for lighter deployment

@router.websocket(WS_CHAT)
@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for text-based chat with enhanced connection management."""
    # Generar ID único para esta conexión
    connection_id = f"chat_{uuid.uuid4().hex[:8]}"
    client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    
    logger.info(f"🔌 Nueva solicitud de conexión WebSocket desde {client_info} (ID: {connection_id})")
    
    try:
        await websocket.accept()
        logger.info(f"✅ Conexión WebSocket aceptada para chat (ID: {connection_id})")
        
        # Enviar mensaje de conexión establecida
        connection_msg = ConnectionMessage(
            client_id=connection_id,
            status="connected"
        )
        await websocket.send_json(connection_msg.dict())
        logger.debug(f"📤 Mensaje de conexión enviado a {connection_id}")
        
        message_count = 0
        
        while True:
            try:
                data = await websocket.receive_text()
                message_count += 1
                logger.debug(f"📨 Mensaje #{message_count} recibido de {connection_id}: {data[:100]}...")
                
                message_data = json.loads(data)
                
                # Analizar el tipo de mensaje recibido
                message_type = message_data.get("type", MessageType.TEXT)
                
                if message_type == MessageType.TEXT:
                    user_message = message_data.get("text", "")
                    
                    if not user_message:
                        logger.warning(f"⚠️ Mensaje vacío recibido de {connection_id}")
                        error_msg = ErrorMessage(
                            id=str(uuid.uuid4()),
                            error="Mensaje vacío",
                            code=400
                        )
                        await websocket.send_json(error_msg.dict())
                        continue
                    
                    logger.info(f"💬 Procesando mensaje de texto de {connection_id}: '{user_message[:50]}...'")
                    
                    # Indicar que estamos procesando
                    typing_msg = TypingMessage()
                    await websocket.send_json(typing_msg.dict())
                        
                    # Generar respuesta usando el servicio de chat
                    try:
                        respuesta = get_llm_response(user_message)
                        logger.debug(f"🤖 Respuesta generada para {connection_id}: '{respuesta[:50]}...'")
                        
                        # Enviar respuesta usando el modelo TextMessage
                        text_message = TextMessage(
                            id=str(uuid.uuid4()),
                            text=respuesta,
                            is_user=False
                        )
                        await websocket.send_json(text_message.dict())
                        logger.debug(f"📤 Respuesta enviada a {connection_id}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error al generar respuesta para {connection_id}: {e}")
                        error_msg = ErrorMessage(
                            id=str(uuid.uuid4()),
                            error=f"Error al generar respuesta: {str(e)}",
                            code=500
                        )
                        await websocket.send_json(error_msg.dict())
                
                elif message_type == MessageType.TYPING:
                    # Cliente indica que está escribiendo, no necesitamos hacer nada
                    logger.debug(f"⌨️ Cliente {connection_id} está escribiendo...")
                    pass
                
                else:
                    logger.warning(f"⚠️ Tipo de mensaje no soportado de {connection_id}: {message_type}")
                    error_msg = ErrorMessage(
                        id=str(uuid.uuid4()),
                        error=f"Tipo de mensaje no soportado: {message_type}",
                        code=400
                    )
                    await websocket.send_json(error_msg.dict())
                
            except json.JSONDecodeError as je:
                logger.error(f"❌ Error al decodificar JSON de {connection_id}: {je}")
                error_msg = ErrorMessage(
                    id=str(uuid.uuid4()),
                    error="Formato JSON inválido",
                    code=400
                )
                try:
                    await websocket.send_json(error_msg.dict())
                except:
                    break
                    
            except Exception as inner_e:
                logger.error(f"❌ Error interno procesando mensaje de {connection_id}: {inner_e}", exc_info=True)
                try:
                    error_msg = ErrorMessage(
                        id=str(uuid.uuid4()),
                        error="Error interno del servidor",
                        code=500
                    )
                    await websocket.send_json(error_msg.dict())
                except:
                    break
                
    except WebSocketDisconnect as wd:
        logger.info(f"🔌 Cliente {connection_id} desconectado voluntariamente - Código: {getattr(wd, 'code', 'N/A')}, Razón: '{getattr(wd, 'reason', 'Sin razón')}'")
        
    except Exception as e:
        logger.error(f"❌ Error inesperado en conexión {connection_id}: {e}", exc_info=True)
        try:
            error_msg = ErrorMessage(
                id=str(uuid.uuid4()),
                error=str(e),
                code=500
            )
            await websocket.send_json(error_msg.dict())
        except:
            pass
    
    finally:
        logger.info(f"🧹 Limpieza finalizada para conexión {connection_id} - Mensajes procesados: {message_count}")

@router.get("/chat/health")
@router.get("/api/chat/health")
async def websocket_health_check():
    """Endpoint para verificar el estado del servicio WebSocket"""
    return {
        "status": "healthy",
        "service": "websocket_chat",
        "timestamp": json.dumps({"timestamp": "now"}, default=str)
    }

# Audio processing endpoints removed for EC2 optimization