from fastapi import APIRouter, WebSocket, WebSocketDisconnect, File, UploadFile
import logging
import json
import uuid
from services.chat_service import get_llm_response
from services.audio_service import speech_to_text, text_to_speech
from utils import encode_audio_to_base64, create_error_response
from fastapi.responses import JSONResponse
from routes import WS_DETECT_AUDIO, WS_CHAT
from models import TextMessage, AudioMessage, ErrorMessage, ConnectionMessage, TypingMessage, MessageType

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket(WS_DETECT_AUDIO)
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para interacción por voz."""
    await websocket.accept()
    logger.info("Cliente conectado al WebSocket de voz /api/detect")

    # Enviar mensaje de conexión establecida
    connection_msg = ConnectionMessage(
        client_id=str(uuid.uuid4()),
        status="connected"
    )
    await websocket.send_json(connection_msg.dict())

    while True:
        try:
            audio_bytes = await websocket.receive_bytes()
            logger.debug("Bytes de audio recibidos")

            # Enviar mensaje de "procesando"
            typing_msg = TypingMessage()
            await websocket.send_json(typing_msg.dict())

            # Convertir audio a texto
            texto_usuario = speech_to_text(audio_bytes)
            logger.info(f"Usuario dijo (voz): {texto_usuario}")

            # Obtener respuesta del LLM
            if "hola" in texto_usuario.lower(): # Manejo simple de saludo
                respuesta_texto = "Hola, ¿qué deseas realizar hoy?"
            else:
                respuesta_texto = get_llm_response(texto_usuario)
            logger.info(f"Respuesta LLM (voz): {respuesta_texto}")

            # Convertir respuesta a voz
            archivo_audio_bytes = text_to_speech(respuesta_texto)
            if archivo_audio_bytes:
                archivo_audio_base64 = encode_audio_to_base64(archivo_audio_bytes)
                logger.debug("Audio de respuesta codificado a base64")
                
                # Usar el modelo AudioMessage para estandarizar la respuesta
                audio_message = AudioMessage(
                    id=str(uuid.uuid4()),
                    text=respuesta_texto,
                    audio=archivo_audio_base64,
                    is_user=False
                )
                await websocket.send_json(audio_message.dict())
            else:
                logger.warning("No se pudo generar el audio de respuesta")
                # Usar el modelo TextMessage ya que no hay audio disponible
                text_message = TextMessage(
                    id=str(uuid.uuid4()),
                    text=respuesta_texto,
                    is_user=False
                )
                await websocket.send_json(text_message.dict())
            
            logger.debug("Respuesta de voz enviada al cliente")

        except WebSocketDisconnect:
            logger.info("Cliente desconectado del WebSocket de voz")
            break
        except Exception as e:
            logger.error(f"Error en WebSocket de voz: {e}")
            # Enviar mensaje de error usando el modelo ErrorMessage
            try:
                error_msg = ErrorMessage(
                    id=str(uuid.uuid4()),
                    error=f"Error en el servidor de voz: {str(e)}",
                    code=500
                )
                await websocket.send_json(error_msg.dict())
            except Exception as send_error:
                logger.error(f"Error al enviar mensaje de error por WebSocket de voz: {send_error}")
            break # Romper el bucle en caso de error grave

@router.websocket(WS_CHAT)
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Conexión WebSocket aceptada para chat")
    
    # Enviar mensaje de conexión establecida
    connection_msg = ConnectionMessage(
        client_id=str(uuid.uuid4()),
        status="connected"
    )
    await websocket.send_json(connection_msg.dict())
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Analizar el tipo de mensaje recibido
            message_type = message_data.get("type", MessageType.TEXT)
            
            if message_type == MessageType.TEXT:
                user_message = message_data.get("text", "")
                
                if not user_message:
                    error_msg = ErrorMessage(
                        id=str(uuid.uuid4()),
                        error="Mensaje vacío",
                        code=400
                    )
                    await websocket.send_json(error_msg.dict())
                    continue
                
                # Indicar que estamos procesando
                typing_msg = TypingMessage()
                await websocket.send_json(typing_msg.dict())
                    
                # Generar respuesta usando el servicio de chat
                try:
                    respuesta = get_llm_response(user_message)
                    
                    # Enviar respuesta usando el modelo TextMessage
                    text_message = TextMessage(
                        id=str(uuid.uuid4()),
                        text=respuesta,
                        is_user=False
                    )
                    await websocket.send_json(text_message.dict())
                except Exception as e:
                    logger.error(f"Error al generar respuesta: {e}")
                    error_msg = ErrorMessage(
                        id=str(uuid.uuid4()),
                        error=f"Error al generar respuesta: {str(e)}",
                        code=500
                    )
                    await websocket.send_json(error_msg.dict())
            
            elif message_type == MessageType.TYPING:
                # Cliente indica que está escribiendo, no necesitamos hacer nada
                pass
            
            else:
                logger.warning(f"Tipo de mensaje no soportado: {message_type}")
                error_msg = ErrorMessage(
                    id=str(uuid.uuid4()),
                    error=f"Tipo de mensaje no soportado: {message_type}",
                    code=400
                )
                await websocket.send_json(error_msg.dict())
            
    except WebSocketDisconnect:
        logger.info("Cliente chat desconectado")
    except Exception as e:
        logger.error(f"Error en chat WebSocket: {e}", exc_info=True)
        try:
            error_msg = ErrorMessage(
                id=str(uuid.uuid4()),
                error=str(e),
                code=500
            )
            await websocket.send_json(error_msg.dict())
        except:
            pass

@router.post("/process-voice")
async def process_voice_endpoint(audio: UploadFile = File(...)):
    """Endpoint HTTP para procesar un archivo de audio."""
    try:
        logger.info(f"Recibido archivo de audio: {audio.filename}")
        audio_bytes = await audio.read()
        
        # Convertir audio a texto
        texto_usuario = speech_to_text(audio_bytes)
        logger.info(f"Usuario dijo (audio HTTP): {texto_usuario}")

        # Obtener respuesta del LLM
        respuesta_texto = get_llm_response(texto_usuario)
        logger.info(f"Respuesta LLM (audio HTTP): {respuesta_texto}")

        # Convertir respuesta a voz
        archivo_audio_bytes = text_to_speech(respuesta_texto)
        if archivo_audio_bytes:
            archivo_audio_base64 = encode_audio_to_base64(archivo_audio_bytes)
            logger.debug("Audio de respuesta (HTTP) codificado a base64")
            
            # Usar el modelo AudioMessage para estandarizar la respuesta
            audio_message = AudioMessage(
                id=str(uuid.uuid4()),
                text=respuesta_texto,
                audio=archivo_audio_base64,
                is_user=False
            )
            return audio_message.dict()
        else:
            logger.warning("No se pudo generar el audio de respuesta (HTTP)")
            # Usar el modelo TextMessage ya que no hay audio disponible
            text_message = TextMessage(
                id=str(uuid.uuid4()),
                text=respuesta_texto,
                is_user=False
            )
            return text_message.dict()
            
    except Exception as e:
        logger.error(f"Error en endpoint /process-voice: {e}", exc_info=True)
        error_message = ErrorMessage(
            id=str(uuid.uuid4()),
            error=f"Error al procesar el audio: {str(e)}",
            code=500
        )
        return JSONResponse(
            status_code=500,
            content=error_message.dict()
        )