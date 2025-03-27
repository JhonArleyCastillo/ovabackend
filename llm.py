import requests
from config import HF_API_KEY

# URL de la API de Hugging Face
API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-1.5B-Instruct"

# Headers para la autenticación
headers = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

# Estado de la conexión
is_connected = False

def verificar_conexion():
    """Verifica la conexión con la API de Hugging Face"""
    global is_connected
    try:
        # Intenta hacer una petición simple para verificar la conexión
        response = requests.get(
            "https://api-inference.huggingface.co/status",
            headers=headers,
            timeout=5
        )
        is_connected = response.status_code == 200
        return is_connected
    except Exception as e:
        is_connected = False
        return False

def obtener_respuesta(mensaje):
    """Obtiene una respuesta del modelo usando la API de Hugging Face"""
    global is_connected
    
    if not is_connected:
        if not verificar_conexion():
            return "Lo siento, hay un problema de conexión con el servicio. Por favor, intenta más tarde."
    
    try:
        # Crear el prompt con el formato correcto
        prompt = f"<|im_start|>system\nEres un asistente amigable y servicial. Responde siempre en español de manera clara y concisa.<|im_end|>\n<|im_start|>user\n{mensaje}<|im_end|>\n<|im_start|>assistant\n"
        
        # Realizar la petición a la API
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "do_sample": True,
                    "return_full_text": False
                }
            },
            timeout=30
        )
        
        # Verificar si la respuesta fue exitosa
        if response.status_code == 200:
            respuesta = response.json()[0]["generated_text"]
            # Limpiar la respuesta para obtener solo el texto generado
            respuesta = respuesta.replace(prompt, "").strip()
            return respuesta
        else:
            is_connected = False
            return "Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta más tarde."
            
    except requests.exceptions.Timeout:
        return "Lo siento, la respuesta está tomando más tiempo del esperado. Por favor, intenta de nuevo."
    except Exception as e:
        is_connected = False
        return f"Lo siento, ocurrió un error: {str(e)}"
