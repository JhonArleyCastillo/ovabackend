from dotenv import load_dotenv
import os

# Cargar variables desde .env
load_dotenv()

# Variables de entorno
HF_API_KEY = os.getenv("HF_API_KEY")  # Token de Hugging Face
HF_MODELO_LLM = os.getenv("HF_MODELO_LLM")
HF_MODELO_TTS = os.getenv("HF_MODELO_TTS")
HF_MODELO_STT = os.getenv("HF_MODELO_STT")
HF_MODELO_IMG = os.getenv("HF_MODELO_IMG")
