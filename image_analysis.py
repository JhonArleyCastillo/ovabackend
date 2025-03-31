import numpy as np
import requests
from config import HF_API_KEY, HF_MODELO_SIGN
from PIL import Image
import io
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
import logging

# Configurar el sistema de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL de Hugging Face para BLIP (Image Captioning)
CAPTION_API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
# URL de Hugging Face para YOLOv8 (Object Detection)
YOLO_API_URL = "https://api-inference.huggingface.co/models/ultralytics/yolov8"

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Variables globales para el modelo de lenguaje de señas
sign_processor = None
sign_model = None

def load_sign_language_model():
    """
    Carga el modelo de lenguaje de señas si aún no está cargado
    
    Returns:
        tuple: (bool, str) - Indicador de éxito y mensaje explicativo
    """
    global sign_processor, sign_model
    if sign_processor is None or sign_model is None:
        try:
            # Verificar que tenemos una API key válida
            if not HF_API_KEY or HF_API_KEY == "tu_huggingface_api_key_aqui":
                logger.error("API key de Hugging Face no configurada correctamente")
                return False, "API key de Hugging Face no configurada"
                
            # Verificar que el modelo está especificado
            if not HF_MODELO_SIGN:
                logger.error("Modelo de lenguaje de señas no especificado en la configuración")
                return False, "Modelo no especificado en configuración"
            
            logger.info(f"Cargando modelo de lenguaje de señas: {HF_MODELO_SIGN}")
            sign_processor = AutoImageProcessor.from_pretrained(HF_MODELO_SIGN, use_auth_token=HF_API_KEY)
            sign_model = AutoModelForImageClassification.from_pretrained(HF_MODELO_SIGN, use_auth_token=HF_API_KEY)
            logger.info("Modelo de lenguaje de señas cargado correctamente")
            return True, "Modelo cargado correctamente"
        except Exception as e:
            error_msg = f"Error al cargar el modelo de lenguaje de señas: {e}"
            logger.error(error_msg)
            return False, error_msg
    return True, "Modelo ya estaba cargado"

def detectar_objetos(imagen_np: np.ndarray):
    """
    Analiza la imagen usando YOLOv8 (a través de Hugging Face) para detectar objetos.
    Args:
        imagen_np (np.ndarray): Imagen cargada como array de NumPy.
    Returns:
        list/dict: Lista de objetos detectados con nombre, confianza y coordenadas.
              Si ocurre un error, se retorna un diccionario con el error.
    """
    # Verificar que tenemos una API key válida
    if not HF_API_KEY or HF_API_KEY == "tu_huggingface_api_key_aqui":
        logger.error("API key de Hugging Face no configurada correctamente")
        return {"error": "API key de Hugging Face no configurada"}
    
    try:
        # Convertir la imagen de NumPy a formato JPEG
        img = Image.fromarray(imagen_np)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()
        
        logger.info("Enviando imagen para detección de objetos")
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
            logger.info(f"Detección exitosa: {len(objetos)} objetos encontrados")
            return objetos
        else:
            error_msg = f"Error al detectar objetos: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"Excepción al detectar objetos: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


def describir_imagen(imagen_bytes: bytes):
    """
    Genera un caption (descripción automática) usando BLIP.
    Args:
        imagen_bytes (bytes): Imagen en formato binario.
    Returns:
        dict: Descripción generada o mensaje de error.
    """
    # Verificar que tenemos una API key válida
    if not HF_API_KEY or HF_API_KEY == "tu_huggingface_api_key_aqui":
        logger.error("API key de Hugging Face no configurada correctamente")
        return {"error": "API key de Hugging Face no configurada"}
    
    try:
        logger.info("Enviando imagen para generación de descripción")
        response = requests.post(
            CAPTION_API_URL,
            headers=HEADERS,
            files={"image": ("imagen.jpg", imagen_bytes, "image/jpeg")}
        )

        if response.status_code == 200:
            captions = response.json()
            if isinstance(captions, list) and len(captions) > 0 and 'generated_text' in captions[0]:
                descripcion = captions[0]['generated_text']
                logger.info(f"Descripción generada: {descripcion}")
                return {"descripcion": descripcion}
            else:
                error_msg = "Formato de respuesta inesperado"
                logger.warning(error_msg)
                return {"error": error_msg}
        else:
            error_msg = f"Error al generar caption: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"Excepción al generar descripción: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

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
        modelo_cargado, mensaje = load_sign_language_model()
        if not modelo_cargado:
            logger.error(f"No se pudo cargar el modelo: {mensaje}")
            return {"error": mensaje}
        
        logger.info("Procesando imagen para reconocimiento de lenguaje de señas")
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
            
            resultado = {
                "resultado": predicted_label,
                "confianza": round(probs[0][predicted_class_idx].item() * 100, 2),
                "alternativas": resultados
            }
            
            logger.info(f"Reconocimiento exitoso: {predicted_label} ({resultado['confianza']}%)")
            return resultado
    except Exception as e:
        error_msg = f"Error en reconocimiento de lenguaje de señas: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
