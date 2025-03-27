from fastapi import FastAPI, WebSocket, File, UploadFile, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from llm import obtener_respuesta, verificar_conexion
from tts import generar_voz
from stt import convertir_audio_a_texto
from image_analysis import detectar_objetos, describir_imagen
import cv2
import numpy as np
import base64
import json
import asyncio

# Crear la app FastAPI
app = FastAPI()

# Habilitar CORS para el frontend (React)
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
async def websocket_endpoint(websocket: WebSocket):
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

@app.get("/status")
async def get_status():
    """Endpoint para verificar el estado de la conexión con Hugging Face"""
    is_connected = verificar_conexion()
    return {
        "status": "connected" if is_connected else "disconnected",
        "message": "Conectado a Hugging Face" if is_connected else "Desconectado de Hugging Face"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
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
                
    except WebSocketDisconnect:
        print("Cliente desconectado")
