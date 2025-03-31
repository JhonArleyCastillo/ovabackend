from fastapi import FastAPI, WebSocket, File, UploadFile, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from llm import obtener_respuesta, verificar_conexion
from tts import generar_voz
from stt import convertir_audio_a_texto
from image_analysis import reconocer_lenguaje_senas, detectar_objetos, describir_imagen
import cv2
import numpy as np
import base64
import json
import logging
from typing import Dict, Any
from config import HF_API_KEY

# Configurar el sistema de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from huggingface_hub import InferenceClient

# Crear cliente de Hugging Face usando la API key desde config
client = InferenceClient(api_key=HF_API_KEY)

# Crear la app FastAPI
app = FastAPI()

# Configurar CORS con opciones más permisivas para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://helpova.web.app", "https://helpova.firebaseapp.com"],
    allow_credentials=True,
    allow_methods=["get", "post"],
    allow_headers=["content-type", "authorization"],
)

# -----------------------------------
# Endpoint WebSocket (Voz / Chat)
# -----------------------------------
@app.websocket("/api/detect")
async def websocket_detect_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            audio = await websocket.receive_bytes()

            texto_usuario = convertir_audio_a_texto(audio)
            logger.info(f"Usuario dijo: {texto_usuario}")

            if "hola" in texto_usuario.lower():
                respuesta_texto = "Hola, ¿qué deseas realizar hoy?"
            else:
                respuesta_texto = obtener_respuesta(texto_usuario)

            archivo_audio = generar_voz(respuesta_texto)
            archivo_audio_base64 = base64.b64encode(archivo_audio).decode("utf-8")

            await websocket.send_json({
                "texto": respuesta_texto,
                "audio": archivo_audio_base64
            })

        except Exception as e:
            logger.error(f"Error en WebSocket: {e}")
            break

# -----------------------------------
# Endpoint HTTP (Análisis de Imágenes)
# -----------------------------------

@app.get("/")
async def read_root():
    """Endpoint de prueba para verificar que el servidor está funcionando"""
    return {"status": "ok", "message": "Servidor funcionando correctamente"}

@app.get("/status")
async def get_status():
    """Endpoint para verificar el estado de la conexión con Hugging Face"""
    try:
        is_connected = verificar_conexion()
        return JSONResponse(
            status_code=200,
            content={
                "status": "connected" if is_connected else "disconnected",
                "message": "Conectado a Hugging Face" if is_connected else "Desconectado de Hugging Face"
            }
        )
    except Exception as e:
        logger.error(f"Error al verificar la conexión: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Error al verificar la conexión: {str(e)}"
            }
        )

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                
                logger.info(f"Mensaje recibido: {user_message[:50]}...")
                
                # Obtener respuesta del modelo
                response = obtener_respuesta(user_message)
                
                # Enviar respuesta al cliente
                await websocket.send_json({
                    "type": "response",
                    "message": response
                })
            except json.JSONDecodeError:
                logger.error("Error al decodificar JSON del mensaje")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error al procesar el mensaje: formato JSON inválido"
                })
            except Exception as e:
                logger.error(f"Error en el procesamiento del mensaje: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        logger.info("Cliente desconectado del WebSocket")

@app.post("/analyze-sign-language")
async def analyze_sign_language(payload: Dict[str, Any] = Body(...)):
    """
    Analiza una imagen para detectar lenguaje de señas
    """
    try:
        # Extraer la imagen base64 del payload
        base64_image = payload.get("image", "")
        if not base64_image:
            return JSONResponse(
                status_code=400,
                content={"error": "No se proporcionó ninguna imagen", "status": "error"}
            )
        
        # Eliminar el prefijo de datos URI si existe
        if "base64," in base64_image:
            base64_image = base64_image.split("base64,")[1]
        
        # Decodificar la imagen base64
        image_bytes = base64.b64decode(base64_image)
        
        # Convertir a numpy array para el procesamiento
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Analizar la imagen con el modelo de lenguaje de señas
        logger.info("Procesando imagen para análisis de lenguaje de señas")
        resultado = reconocer_lenguaje_senas(img)
        
        # Verificar si hubo un error
        if "error" in resultado:
            logger.error(f"Error en análisis de señas: {resultado['error']}")
            return JSONResponse(
                status_code=500,
                content={"error": resultado["error"], "status": "error"}
            )
        
        # Generar respuesta para el frontend
        logger.info(f"Análisis exitoso: {resultado['resultado']} ({resultado['confianza']}%)")
        return {
            "prediction": resultado["resultado"],
            "confidence": resultado["confianza"],
            "alternatives": resultado["alternativas"],
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error en endpoint analyze-sign-language: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error al analizar la imagen: {str(e)}",
                "status": "error"
            }
        )

@app.post("/detect-objects")
async def detect_objects(payload: Dict[str, Any] = Body(...)):
    """
    Detecta objetos en una imagen usando YOLOv8
    """
    try:
        # Extraer la imagen base64 del payload
        base64_image = payload.get("image", "")
        if not base64_image:
            return JSONResponse(
                status_code=400,
                content={"error": "No se proporcionó ninguna imagen", "status": "error"}
            )
        
        # Eliminar el prefijo de datos URI si existe
        if "base64," in base64_image:
            base64_image = base64_image.split("base64,")[1]
        
        # Decodificar la imagen base64
        image_bytes = base64.b64decode(base64_image)
        
        # Convertir a numpy array para el procesamiento
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Detectar objetos en la imagen
        logger.info("Procesando imagen para detección de objetos")
        resultado = detectar_objetos(img)
        
        # Verificar si hubo un error
        if isinstance(resultado, dict) and "error" in resultado:
            logger.error(f"Error en detección de objetos: {resultado['error']}")
            return JSONResponse(
                status_code=500,
                content={"error": resultado["error"], "status": "error"}
            )
        
        # Generar respuesta para el frontend
        logger.info(f"Detección exitosa: {len(resultado)} objetos encontrados")
        return {
            "objects": resultado,
            "count": len(resultado),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error en endpoint detect-objects: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error al detectar objetos en la imagen: {str(e)}",
                "status": "error"
            }
        )

@app.post("/describe-image")
async def describe_image(payload: Dict[str, Any] = Body(...)):
    """
    Genera una descripción textual de una imagen usando BLIP
    """
    try:
        # Extraer la imagen base64 del payload
        base64_image = payload.get("image", "")
        if not base64_image:
            return JSONResponse(
                status_code=400,
                content={"error": "No se proporcionó ninguna imagen", "status": "error"}
            )
        
        # Eliminar el prefijo de datos URI si existe
        if "base64," in base64_image:
            base64_image = base64_image.split("base64,")[1]
        
        # Decodificar la imagen base64
        image_bytes = base64.b64decode(base64_image)
        
        # Describir la imagen
        logger.info("Procesando imagen para generación de descripción")
        resultado = describir_imagen(image_bytes)
        
        # Verificar si hubo un error
        if "error" in resultado:
            logger.error(f"Error en descripción de imagen: {resultado['error']}")
            return JSONResponse(
                status_code=500,
                content={"error": resultado["error"], "status": "error"}
            )
        
        # Generar respuesta para el frontend
        logger.info(f"Descripción generada correctamente")
        return {
            "description": resultado["descripcion"],
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error en endpoint describe-image: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error al generar descripción de la imagen: {str(e)}",
                "status": "error"
            }
        )
