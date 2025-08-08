#!/usr/bin/env python3
"""
Script de debug para verificar qué está pasando con la API GPT-OSS
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gradio_client import Client

def debug_gradio_client():
    """Debug directo del cliente Gradio"""
    print("🔍 Debugging cliente Gradio...")
    
    endpoint = "merterbak/gpt-oss-20b-demo"
    print(f"🎯 Endpoint: {endpoint}")
    
    try:
        print("📡 Creando cliente...")
        client = Client(endpoint)
        print("✅ Cliente creado exitosamente")
        
        print("📋 Obteniendo información del API...")
        try:
            # Obtener info del endpoint
            api_info = client.view_api()
            print(f"📊 API Info: {api_info}")
        except Exception as e:
            print(f"⚠️ No se pudo obtener API info: {e}")
        
        print("\n🧪 Prueba básica...")
        
        # Intentar con parámetros mínimos primero
        try:
            result = client.predict(
                "Hello, how are you?",
                api_name="/chat"
            )
            print(f"✅ Resultado básico: {result}")
        except Exception as e:
            print(f"❌ Error con parámetros básicos: {e}")
            print(f"   Tipo de error: {type(e)}")
            
        print("\n🧪 Prueba con parámetros completos...")
        try:
            result = client.predict(
                input_data="¡Hola! ¿Cómo estás?",
                max_new_tokens=100,
                system_prompt="Eres un asistente útil",
                temperature=0.7,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.0,
                api_name="/chat"
            )
            print(f"✅ Resultado completo: {result}")
        except Exception as e:
            print(f"❌ Error con parámetros completos: {e}")
            print(f"   Tipo de error: {type(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Error al crear cliente: {e}")
        import traceback
        traceback.print_exc()

def test_alternative_endpoints():
    """Probar endpoints alternativos conocidos que funcionan"""
    print("\n🔄 Probando endpoints alternativos...")
    
    # Algunos endpoints públicos conocidos que suelen funcionar
    alternative_endpoints = [
        "microsoft/DialoGPT-medium",
        "facebook/blenderbot-400M-distill",
        "microsoft/DialoGPT-small"
    ]
    
    for endpoint in alternative_endpoints:
        print(f"\n🧪 Probando: {endpoint}")
        try:
            client = Client(endpoint)
            print(f"✅ Cliente creado para {endpoint}")
            
            # Intentar una llamada simple
            # Nota: Cada modelo puede tener diferentes APIs
            try:
                result = client.predict("Hello", api_name="/predict")
                print(f"✅ Respuesta de {endpoint}: {result}")
                return True, endpoint
            except Exception as e:
                print(f"❌ Error en predict para {endpoint}: {e}")
                
        except Exception as e:
            print(f"❌ Error creando cliente para {endpoint}: {e}")
    
    return False, None

if __name__ == "__main__":
    print("🚀 Script de Debug para Gradio Client")
    print("=" * 50)
    
    # Debug del endpoint original
    debug_gradio_client()
    
    # Probar alternativas
    success, working_endpoint = test_alternative_endpoints()
    
    print("\n" + "=" * 50)
    if success:
        print(f"🎉 Encontramos un endpoint que funciona: {working_endpoint}")
    else:
        print("⚠️ Ningún endpoint de prueba funcionó")
        print("💡 Recomendaciones:")
        print("   1. Verificar conectividad a internet")
        print("   2. Probar el endpoint original en el navegador")
        print("   3. Buscar endpoints alternativos en Hugging Face Spaces")
