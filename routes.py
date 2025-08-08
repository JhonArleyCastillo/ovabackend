"""
Definición centralizada de rutas API para el backend.
"""

# Rutas WebSocket - Solo chat, audio removido para optimización EC2
WS_CHAT = "/api/chat"

# Rutas REST
API_PREFIX = "/api"
STATUS_ENDPOINT = "/status"
PROCESS_IMAGE_ENDPOINT = "/process-image"
ANALYZE_SIGN_LANGUAGE_ENDPOINT = "/analyze-sign-language"

# Rutas completas para APIs REST
STATUS_ROUTE = STATUS_ENDPOINT
PROCESS_IMAGE_ROUTE = f"{API_PREFIX}{PROCESS_IMAGE_ENDPOINT}"
ANALYZE_SIGN_LANGUAGE_ROUTE = f"{API_PREFIX}{ANALYZE_SIGN_LANGUAGE_ENDPOINT}"