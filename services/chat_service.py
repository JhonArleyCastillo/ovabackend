import logging
import asyncio
from gradio_client import Client
from .resilience_service import ResilienceService

logger = logging.getLogger(__name__)

# Lista de endpoints de Hugging Face con fallbacks
GRADIO_ENDPOINTS = [
    {
        "name": "GPT-OSS-20B",
        "endpoint": "merterbak/gpt-oss-20b-demo",
        "api_name": "/chat",
        "supports_system_prompt": True
    },
    {
        "name": "Microsoft DialoGPT",
        "endpoint": "microsoft/DialoGPT-medium",
        "api_name": "/predict",
        "supports_system_prompt": False
    },
    {
        "name": "Hugging Face Chat UI",
        "endpoint": "amd/gpt-oss-120b-chatbot",
        "api_name": "/chat",
        "supports_system_prompt": True
    }
]

DEFAULT_SYSTEM_PROMPT = "Eres un asistente útil y amigable. Responde de manera clara y concisa en español."

def _create_gradio_client(endpoint: str):
    """Crea una instancia del cliente Gradio para un endpoint específico."""
    try:
        return Client(endpoint)
    except Exception as e:
        logger.error(f"Error al crear cliente Gradio para {endpoint}: {e}")
        raise

def _call_gradio_endpoint(endpoint_config: dict, user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Llama a un endpoint específico de Gradio."""
    try:
        client = _create_gradio_client(endpoint_config["endpoint"])
        
        if endpoint_config["supports_system_prompt"]:
            # Endpoint que soporta system prompt
            final_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
            
            result = client.predict(
                input_data=user_input,
                max_new_tokens=max_tokens,
                system_prompt=final_system_prompt,
                temperature=0.7,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.0,
                api_name=endpoint_config["api_name"]
            )
        else:
            # Endpoint simple sin system prompt
            result = client.predict(
                user_input,
                api_name=endpoint_config["api_name"]
            )
        
        # Procesar el resultado
        if isinstance(result, str):
            return result
        elif isinstance(result, (list, tuple)) and len(result) > 0:
            return str(result[0])
        else:
            logger.warning(f"Formato de respuesta inesperado de {endpoint_config['name']}: {type(result)}")
            return str(result)
            
    except Exception as e:
        logger.error(f"Error en llamada a {endpoint_config['name']}: {e}")
        raise

def _get_fallback_response(user_input: str) -> str:
    """Genera una respuesta de fallback inteligente cuando todos los endpoints fallan."""
    user_lower = user_input.lower()
    
    # Saludos y presentaciones
    if any(greeting in user_lower for greeting in ["hola", "hello", "hi", "buenos días", "buenas tardes", "buenas noches"]):
        return "¡Hola! 👋 Soy tu asistente virtual OVA. Aunque el servicio de IA avanzada no está disponible en este momento, puedo ayudarte con información básica y responder preguntas simples. ¿En qué puedo asistirte?"
    
    # Preguntas sobre programación
    elif any(term in user_lower for term in ["python", "javascript", "programación", "código", "html", "css"]):
        return "¡Me encanta hablar de programación! 💻 Aunque no tengo acceso al modelo de IA completo ahora, puedo ayudarte con conceptos básicos. Python es un lenguaje de programación versátil, JavaScript es esencial para web, y HTML/CSS son la base del diseño web. ¿Hay algo específico que te gustaría saber?"
    
    # Preguntas sobre inteligencia artificial
    elif any(term in user_lower for term in ["inteligencia artificial", "ia", "ai", "machine learning", "aprendizaje automático"]):
        return "🤖 La Inteligencia Artificial es fascinante! Es la tecnología que permite a las máquinas realizar tareas que normalmente requieren inteligencia humana, como reconocer patrones, tomar decisiones y procesar lenguaje natural. Incluye campos como machine learning, deep learning y redes neuronales. ¿Te interesa algún aspecto específico?"
    
    # Preguntas generales de conocimiento
    elif any(question in user_lower for question in ["qué es", "que es", "cómo", "como", "cuál", "cual", "por qué", "porque", "why", "what", "how"]):
        if "fotosíntesis" in user_lower:
            return "🌱 La fotosíntesis es el proceso por el cual las plantas convierten la luz solar, agua y dióxido de carbono en glucosa y oxígeno. Es fundamental para la vida en la Tierra porque produce el oxígeno que respiramos y es la base de la cadena alimentaria."
        elif "gravity" in user_lower or "gravedad" in user_lower:
            return "🌍 La gravedad es la fuerza de atracción entre objetos con masa. En la Tierra, nos mantiene con los pies en el suelo y hace que los objetos caigan hacia el centro del planeta."
        else:
            return "Es una pregunta interesante! 🤔 Aunque no tengo acceso al modelo de IA completo en este momento, puedo intentar ayudarte con información básica. ¿Podrías reformular tu pregunta de manera más específica?"
    
    # Chistes y entretenimiento
    elif any(term in user_lower for term in ["chiste", "joke", "divertido", "gracioso"]):
        chistes = [
            "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae bugs! 🐛💻",
            "¿Cómo llamas a un robot que toma el camino más largo? R2-Detrús! 🤖",
            "¿Por qué los desarrolladores odian la naturaleza? Porque tiene demasiados bugs! 🌿🐛"
        ]
        import random
        return random.choice(chistes)
    
    # Agradecimientos
    elif any(thanks in user_lower for thanks in ["gracias", "thanks", "thank you", "muchas gracias"]):
        return "¡De nada! 😊 Aunque el servicio completo de IA no esté disponible, me alegra poder ayudarte con lo que puedo. Si necesitas algo más específico, ¡no dudes en preguntar!"
    
    # Despedidas
    elif any(bye in user_lower for bye in ["adiós", "adios", "bye", "hasta luego", "nos vemos"]):
        return "¡Hasta luego! 👋 Fue un placer ayudarte. Vuelve cuando necesites asistencia. ¡Que tengas un excelente día!"
    
    # Consultas sobre el estado del servicio
    elif any(term in user_lower for term in ["funciona", "disponible", "servicio", "error"]):
        return "🔧 El servicio de IA avanzada está temporalmente no disponible debido a limitaciones de cuota en los servidores externos. Sin embargo, puedo ayudarte con respuestas básicas y información general. ¿Hay algo específico en lo que pueda asistirte mientras tanto?"
    
    # Respuesta general
    else:
        return f"He recibido tu mensaje: '{user_input}' 📝\n\nAunque el modelo de IA completo no está disponible ahora, estoy aquí para ayudarte con información básica. Puedo responder preguntas sobre programación, ciencia, tecnología, o simplemente conversar contigo. ¿En qué te gustaría que te ayude?"

@ResilienceService.resilient_hf_call(
    timeout_seconds=30.0,  # Reducido para ser más responsivo
    retry_attempts=2,      # Menos intentos para endpoints lentos
    fallback_response="Lo siento, el servicio no está disponible en este momento. Por favor, inténtalo más tarde."
)
async def get_llm_response_async(user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Obtiene una respuesta usando múltiples endpoints como fallback."""
    try:
        # Ejecutar la llamada con fallbacks en un thread separado para mantener async
        response = await asyncio.get_event_loop().run_in_executor(
            None, _call_with_fallbacks, user_input, system_prompt, max_tokens
        )
        logger.info(f"Respuesta generada para: '{user_input[:30]}...'")
        return response
    except Exception as e:
        logger.error(f"Error al obtener respuesta: {e}")
        raise

def _call_with_fallbacks(user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Intenta llamar a endpoints con fallbacks automáticos."""
    
    for i, endpoint_config in enumerate(GRADIO_ENDPOINTS):
        try:
            logger.info(f"Intentando endpoint {i+1}/{len(GRADIO_ENDPOINTS)}: {endpoint_config['name']}")
            response = _call_gradio_endpoint(endpoint_config, user_input, system_prompt, max_tokens)
            logger.info(f"✅ Respuesta exitosa de {endpoint_config['name']}")
            return response
            
        except Exception as e:
            logger.warning(f"❌ Falló endpoint {endpoint_config['name']}: {e}")
            
            # Si es el último endpoint, usar fallback local
            if i == len(GRADIO_ENDPOINTS) - 1:
                logger.info("Usando respuesta de fallback local")
                return _get_fallback_response(user_input)
            
            # Continuar con el siguiente endpoint
            continue
    
    # Esto no debería ejecutarse nunca, pero por seguridad
    return _get_fallback_response(user_input)

def get_llm_response(user_input: str, system_prompt: str = None, max_tokens: int = 1024) -> str:
    """Obtiene una respuesta usando múltiples endpoints (versión síncrona)."""
    try:
        return _call_with_fallbacks(user_input, system_prompt, max_tokens)
    except Exception as e:
        logger.error(f"Error al obtener respuesta: {e}")
        return _get_fallback_response(user_input)

# APIs externas migradas a gradio_client - código legacy limpiado 