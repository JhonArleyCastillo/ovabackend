"""
Consolidated import utilities to eliminate sys.path redundancy.
This module handles all the path setup needed across the backend.
"""
import sys
import os
from pathlib import Path

# Obtener el directorio raíz del backend
BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent

# Agregar rutas a sys.path si no están ya presentes
def setup_backend_imports():
    """Setup import paths for backend modules."""
    paths_to_add = [
        str(PROJECT_ROOT),
        str(BACKEND_ROOT),
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)

# Call setup function when this module is imported
setup_backend_imports()

# Common imports that are used across multiple files
from backend.database import get_db
from backend.auth import get_current_admin, verify_token
import backend.schemas as schemas
import backend.db_models as db_models
from backend.config import *

# Export commonly used items
__all__ = [
    'get_db',
    'get_current_admin', 
    'verify_token',
    'schemas',
    'db_models',
    'BACKEND_ROOT',
    'PROJECT_ROOT'
]
