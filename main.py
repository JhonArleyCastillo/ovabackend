from fastapi import FastAPI, WebSocket, File, UploadFile, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from llm import obtener_respuesta, verificar_conexion
from tts import generar_voz
from stt import convertir_audio_a_texto
from image_analysis import detectar_objetos, describir_imagen, reconocer_lenguaje_senas
import cv2
import numpy as np
import base64
import json
import asyncio
from typing import Dict, Any

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
            print(f"Usuario dijo: {texto_usuario}")

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
            print(f"Error en WebSocket: {e}")
            break

# -----------------------------------
# Endpoint HTTP (Análisis de Imágenes)
# -----------------------------------
@app.post("/procesar-imagen")
async def procesar_imagen(file: UploadFile = File(...)):
    """
    Recibe una imagen, la analiza (YOLO o BLIP) y devuelve resultados.
    """
    contenido = await file.read()

    # Decodificar imagen a numpy array (para YOLO)
    imagen_np = cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_COLOR)

    # Realizar análisis
    objetos_detectados = detectar_objetos(imagen_np)
    descripcion = describir_imagen(contenido)

    # Responder al frontend
    return {
        "objetos_detectados": objetos_detectados,
        "descripcion": descripcion
    }

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
                
                # Obtener respuesta del modelo
                response = obtener_respuesta(user_message)
                
                # Enviar respuesta al cliente
                await websocket.send_json({
                    "type": "response",
                    "message": response
                })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Error al procesar el mensaje"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        print("Cliente desconectado")

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
        resultado = reconocer_lenguaje_senas(img)
        
        # Verificar si hubo un error
        if "error" in resultado:
            return JSONResponse(
                status_code=500,
                content={"error": resultado["error"], "status": "error"}
            )
        
        # Generar respuesta para el frontend
        return {
            "prediction": resultado["resultado"],
            "confidence": resultado["confianza"],
            "alternatives": resultado["alternativas"],
            "status": "success"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error al analizar la imagen: {str(e)}",
                "status": "error"
            }
        )
