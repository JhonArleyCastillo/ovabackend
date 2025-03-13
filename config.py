from dotenv import load_dotenv
import os

# Cargar variables desde .env
load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODELO_LLM = os.getenv("HF_MODELO_LLM")
HF_MODELO_TTS = os.getenv("HF_MODELO_TTS")
HF_MODELO_CAPTION = os.getenv("HF_MODELO_CAPTION")
