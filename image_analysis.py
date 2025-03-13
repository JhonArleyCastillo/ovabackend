import numpy as np
import requests
from config import HF_API_KEY
from PIL import Image
import io

# URL de Hugging Face para BLIP (Image Captioning)
CAPTION_API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
# URL de Hugging Face para YOLOv8 (Object Detection)
YOLO_API_URL = "https://api-inference.huggingface.co/models/ultralytics/yolov8"

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

def detectar_objetos(imagen_np: np.ndarray):
    """
    Analiza la imagen usando YOLOv8 (a través de Hugging Face) para detectar objetos.
    Args:
        imagen_np (np.ndarray): Imagen cargada como array de NumPy.
    Returns:
        list: Lista de objetos detectados con nombre, confianza y coordenadas.
              Si ocurre un error, se retorna un string con el mensaje de error.
    """
    # Convertir la imagen de NumPy a formato JPEG
    img = Image.fromarray(imagen_np)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()
    
    response = requests.post(
        YOLO_API_URL,
        headers=HEADERS,
        files={"image": ("imagen.jpg", img_bytes, "image/jpeg")}
    )
    
    if response.status_code == 200:
        detecciones = response.json()
        objetos = []
        # Se asume que la respuesta es una lista de diccionarios con la siguiente estructura:
        # [{"label": "person", "score": 0.98, "box": [xmin, ymin, xmax, ymax]}, ...]
        for obj in detecciones:
            label = obj.get("label", "desconocido")
            score = obj.get("score", 0.0)
            box = obj.get("box", None)
            if box and len(box) == 4:
                x1, y1, x2, y2 = box
            else:
                x1 = y1 = x2 = y2 = None

            objetos.append({
                "nombre": label,
                "confianza": float(score),
                "coordenadas": {
                    "x1": float(x1) if x1 is not None else None,
                    "y1": float(y1) if y1 is not None else None,
                    "x2": float(x2) if x2 is not None else None,
                    "y2": float(y2) if y2 is not None else None
                }
            })
        return objetos
    else:
        return f"Error al detectar objetos: {response.text}"


def describir_imagen(imagen_bytes: bytes):
    """
    Genera un caption (descripción automática) usando BLIP.
    Args:
        imagen_bytes (bytes): Imagen en formato binario.
    Returns:
        str: Descripción generada o mensaje de error.
    """
    response = requests.post(
        CAPTION_API_URL,
        headers=HEADERS,
        files={"image": ("imagen.jpg", imagen_bytes, "image/jpeg")}
    )

    if response.status_code == 200:
        captions = response.json()
        if isinstance(captions, list) and len(captions) > 0 and 'generated_text' in captions[0]:
            return captions[0]['generated_text']
        else:
            return "No se pudo generar una descripción."
    else:
        return f"Error al generar caption: {response.text}"
