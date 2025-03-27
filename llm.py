import requests
from config import HF_API_KEY

# Configuración de la API de Hugging Face
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

SYSTEM_PROMPT = (
    "Eres un asistente virtual amable, cálido y servicial. "
    "Respondes en tono amigable y claro. Siempre explicas de forma sencilla y en español."
)

def obtener_respuesta(texto_usuario):
    try:
        # Crear el prompt con el formato correcto
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": texto_usuario}
        ]
        
        # Enviar solicitud a la API
        payload = {
            "inputs": messages,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "do_sample": True
            }
        }
        
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            # Extraer la respuesta del modelo
            respuesta = response.json()[0]["generated_text"]
            # Limpiar la respuesta si es necesario
            if "Assistant:" in respuesta:
                respuesta = respuesta.split("Assistant:")[-1].strip()
            return respuesta
        else:
            return f"Error al conectar con el modelo: {response.text}"
            
    except Exception as e:
        return f"Lo siento, hubo un error al procesar tu mensaje: {str(e)}"
