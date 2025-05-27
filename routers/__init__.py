# Módulo de routers para el backend de OVA
from . import (
    status_router,
    websocket_router, 
    image_router,
    auth_router,
    usuarios_router,
    contact_router,
    resilience_router
)

__all__ = [
    "status_router",
    "websocket_router",
    "image_router", 
    "auth_router",
    "usuarios_router",
    "contact_router",
    "resilience_router"
]
