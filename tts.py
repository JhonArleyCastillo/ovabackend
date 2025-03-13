import requests
from config import HF_API_KEY, HF_MODELO_TTS

HF_MODELO_TTS = "espnet/kan-bayashi_ljspeech_vits"
TTS_URL = f"https://api-inference.huggingface.co/models/{HF_MODELO_TTS}"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

def generar_voz(texto):
    payload = {"inputs": texto}
    response = requests.post(TTS_URL, headers=HEADERS, json=payload)

    if response.status_code != 200:
        raise Exception(f"Error en TTS: {response.status_code} - {response.text}")

    # Validar que sea audio y no error HTML
    content_type = response.headers.get("Content-Type", "")
    if "audio/" not in content_type:
        raise Exception(f"Respuesta inesperada de Hugging Face (esperaba audio): {response.text}")

    # Devolver el audio como binario (no base64 aquí)
    return response.content
