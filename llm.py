import requests
from config import HF_API_KEY, HF_MODELO_LLM

API_URL = f"https://api-inference.huggingface.co/models/{HF_MODELO_LLM}"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

SYSTEM_PROMPT = (
    "Eres un asistente virtual amable, cálido y servicial. "
    "Respondes en tono amigable y claro. Siempre explicas de forma sencilla."
)

def obtener_respuesta(texto_usuario):
    prompt_completo = f"{SYSTEM_PROMPT}\n\nUsuario: {texto_usuario}\n\nAsistente:"

    payload = {"inputs": prompt_completo}
    response = requests.post(API_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        raw_text = response.json()[0]['generated_text']
        respuesta = raw_text.replace(prompt_completo, "").strip()
        return respuesta
    else:
        return f"Error al consultar el modelo: {response.text}"
