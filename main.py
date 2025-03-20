from fastapi import FastAPI, WebSocket, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from llm import obtener_respuesta
from tts import generar_voz
from stt import convertir_audio_a_texto
from image_analysis import detectar_objetos, describir_imagen
import cv2
import numpy as np
import base64

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
