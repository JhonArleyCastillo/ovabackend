import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import keras
from huggingface_hub import login

os.environ["KERAS_BACKEND"] = "jax"
# login(token="TU_TOKEN_HF")  # Descomenta si tu modelo es privado

MODEL_PATH = "hf://JhonArleyCastilloV/ASL_model_1"
model = keras.saving.load_model(MODEL_PATH)

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