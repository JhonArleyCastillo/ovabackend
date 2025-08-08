import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import logging

# Make Keras/JAX optional
try:
    os.environ["KERAS_BACKEND"] = "jax"
    import keras
    from huggingface_hub import login
    KERAS_AVAILABLE = True
    
    # login(token="TU_TOKEN_HF")  # Descomenta si tu modelo es privado
    MODEL_PATH = "hf://JhonArleyCastilloV/ASL_model_1"
    try:
        model = keras.saving.load_model(MODEL_PATH)
    except Exception as e:
        logging.warning(f"Could not load ASL model: {e}")
        model = None
        
except ImportError:
    KERAS_AVAILABLE = False
    model = None
    logging.warning("Keras/JAX not available - ASL model features disabled")

def preprocess_image_bytes(image_bytes, target_size=(224, 224)):
    img = Image.open(image_bytes).convert("RGB")
    img = img.resize(target_size, Image.LANCZOS)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    img = img.filter(ImageFilter.SHARPEN)
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

def predict_from_bytes(image_bytes):
    if not KERAS_AVAILABLE or model is None:
        return {
            "class": "N/A", 
            "prob": 0.0, 
            "top_preds": [],
            "error": "ASL model not available - Keras/JAX required"
        }
    
    try:
        img_array = preprocess_image_bytes(image_bytes)
        predictions = model(img_array, training=False).numpy()
        classes = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["nothing", "del", "space"]
        class_idx = np.argmax(predictions[0])
        prob = float(predictions[0][class_idx])
        class_name = classes[class_idx] if class_idx < len(classes) else f"Clase {class_idx}"
        top_indices = np.argsort(predictions[0])[::-1][:3]
        top_preds = [
            {"class": classes[i] if i < len(classes) else f"Clase {i}", "prob": float(predictions[0][i])}
            for i in top_indices
        ]
        return {"class": class_name, "prob": prob, "top_preds": top_preds}
    except Exception as e:
        logging.error(f"Error in ASL prediction: {e}")
        return {
            "class": "Error", 
            "prob": 0.0, 
            "top_preds": [],
            "error": str(e)
        }