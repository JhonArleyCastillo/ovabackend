import numpy as np
import requests
from config import HF_API_KEY, HF_MODELO_SIGN
from PIL import Image
import io
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

# URL de Hugging Face para BLIP (Image Captioning)
CAPTION_API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
# URL de Hugging Face para YOLOv8 (Object Detection)
YOLO_API_URL = "https://api-inference.huggingface.co/models/ultralytics/yolov8"

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Variables globales para el modelo de lenguaje de señas
sign_processor = None
sign_model = None

def load_sign_language_model():
    """Carga el modelo de lenguaje de señas si aún no está cargado"""
    global sign_processor, sign_model
    if sign_processor is None or sign_model is None:
        try:
            sign_processor = AutoImageProcessor.from_pretrained(HF_MODELO_SIGN, use_auth_token=HF_API_KEY)
            sign_model = AutoModelForImageClassification.from_pretrained(HF_MODELO_SIGN, use_auth_token=HF_API_KEY)
            print("Modelo de lenguaje de señas cargado correctamente")
        except Exception as e:
            print(f"Error al cargar el modelo de lenguaje de señas: {e}")
            return False
    return True

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

def reconocer_lenguaje_senas(imagen_np: np.ndarray):
    """
    Analiza una imagen para reconocer lenguaje de señas
    
    Args:
        imagen_np (np.ndarray): Imagen como array de NumPy.
    
    Returns:
        dict: Diccionario con la letra/símbolo detectado y su probabilidad.
             En caso de error, retorna un mensaje explicativo.
    """
    try:
        # Cargar modelo si no está cargado
        if not load_sign_language_model():
            return {"error": "No se pudo cargar el modelo de lenguaje de señas"}
        
        # Convertir numpy array a formato RGB si está en BGR (formato de OpenCV)
        if imagen_np.shape[2] == 3:
            # Verificar si la imagen está en formato BGR (OpenCV)
            imagen_rgb = Image.fromarray(imagen_np).convert('RGB')
        else:
            imagen_rgb = Image.fromarray(imagen_np)
        
        # Preprocesar la imagen para el modelo
        inputs = sign_processor(images=imagen_rgb, return_tensors="pt")
        
        # Realizar la predicción
        with torch.no_grad():
            outputs = sign_model(**inputs)
            logits = outputs.logits
            # Obtener las probabilidades usando softmax
            probs = torch.nn.functional.softmax(logits, dim=1)
            # Obtener los 3 mejores resultados
            top3_prob, top3_indices = torch.topk(probs, 3)
            
            # Convertir a lista para facilitar la serialización
            resultados = []
            for i in range(3):
                if i < len(top3_indices[0]):
                    idx = top3_indices[0][i].item()
                    prob = top3_prob[0][i].item()
                    label = sign_model.config.id2label[idx]
                    resultados.append({
                        "simbolo": label,
                        "probabilidad": round(prob * 100, 2)
                    })
            
            # Obtener el mejor resultado
            predicted_class_idx = logits.argmax(-1).item()
            predicted_label = sign_model.config.id2label[predicted_class_idx]
            
            return {
                "resultado": predicted_label,
                "confianza": round(probs[0][predicted_class_idx].item() * 100, 2),
                "alternativas": resultados
            }
    except Exception as e:
        print(f"Error en reconocimiento de lenguaje de señas: {e}")
        return {"error": f"Error al analizar la imagen: {str(e)}"}
