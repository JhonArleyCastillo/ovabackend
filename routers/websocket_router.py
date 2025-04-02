from fastapi import APIRouter, WebSocket, WebSocketDisconnect, File, UploadFile
import logging
import json
from services.chat_service import get_llm_response
from services.audio_service import speech_to_text, text_to_speech
from utils import encode_audio_to_base64, create_error_response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/api/detect")
async def websocket_detect_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para interacción por voz."""
    await websocket.accept()
    logger.info("Cliente conectado al WebSocket de voz /api/detect")

    while True:
        try:
            audio_bytes = await websocket.receive_bytes()
            logger.debug("Bytes de audio recibidos")

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
            else:
                archivo_audio_base64 = ""
                logger.warning("No se pudo generar el audio de respuesta")

            # Enviar respuesta
            await websocket.send_json({
                "texto": respuesta_texto,
                "audio": archivo_audio_base64
            })
            logger.debug("Respuesta de voz enviada al cliente")

        except WebSocketDisconnect:
            logger.info("Cliente desconectado del WebSocket de voz")
            break
        except Exception as e:
            logger.error(f"Error en WebSocket de voz: {e}")
            # Intentar enviar un mensaje de error si la conexión sigue activa
            try:
                await websocket.send_json({"error": f"Error en el servidor de voz: {str(e)}"})
            except Exception as send_error:
                logger.error(f"Error al enviar mensaje de error por WebSocket de voz: {send_error}")
            break # Romper el bucle en caso de error grave

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para interacción por chat de texto."""
    await websocket.accept()
    logger.info("Cliente conectado al WebSocket de chat /ws/chat")
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Datos recibidos en WebSocket de chat: {data[:100]}...")
                
                message_data = json.loads(data)
                user_message = message_data.get("text", "") # Asegurar que busca la clave 'text'
                
                if not user_message:
                    logger.warning("Mensaje de chat vacío recibido")
                    continue # Ignorar mensajes vacíos

                logger.info(f"Mensaje de chat recibido: {user_message[:50]}...")
                
                # Simular escritura
                await websocket.send_json({"type": "typing"})
                
                # Obtener respuesta del modelo
                response = get_llm_response(user_message)
                logger.info(f"Respuesta LLM (chat): {response}")
                
                # Enviar respuesta al cliente
                await websocket.send_json({
                    "type": "response",
                    "message": response
                })
                logger.debug("Respuesta de chat enviada al cliente")
                
            except json.JSONDecodeError:
                logger.error("Error al decodificar JSON del mensaje de chat")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error al procesar el mensaje: formato JSON inválido"
                })
            except WebSocketDisconnect:
                logger.info("Cliente desconectado del WebSocket de chat")
                raise # Re-lanzar para que el bloque exterior la capture
            except Exception as e:
                logger.error(f"Error en procesamiento de mensaje de chat: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error interno del servidor: {str(e)}"
                })
                # Considerar si se debe desconectar al cliente o continuar
                
    except WebSocketDisconnect:
        logger.info("Desconexión manejada para WebSocket de chat")
    except Exception as e:
        # Capturar cualquier otro error no manejado dentro del bucle
        logger.error(f"Error inesperado en WebSocket de chat: {e}") 

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
            return {
                "status": "success",
                "text": respuesta_texto, # Devolver también el texto reconocido/respuesta
                "audioBase64": archivo_audio_base64
            }
        else:
            logger.warning("No se pudo generar el audio de respuesta (HTTP)")
            return {"status": "success", "text": respuesta_texto, "audioBase64": None}
            
    except Exception as e:
        logger.error(f"Error en endpoint /process-voice: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=create_error_response(f"Error al procesar el audio: {str(e)}", 500)[0]
        ) 