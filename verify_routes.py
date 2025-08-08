#!/usr/bin/env python3
"""
Script para verificar las rutas disponibles en el backend FastAPI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from fastapi.routing import APIRoute

print("🔍 ANÁLISIS DE RUTAS DISPONIBLES EN EL BACKEND")
print("=" * 60)

# Obtener todas las rutas
routes = []
for route in app.routes:
    if isinstance(route, APIRoute):
        routes.append({
            'path': route.path,
            'methods': list(route.methods),
            'name': route.name
        })

# Filtrar rutas relacionadas con imágenes y ASL
print("📋 TODAS LAS RUTAS DE API:")
for route in sorted(routes, key=lambda x: x['path']):
    methods_str = ', '.join(sorted(route['methods']))
    print(f"   {methods_str:12} {route['path']:35} ({route['name']})")

print("\n" + "=" * 60)

# Buscar rutas específicas de ASL
asl_routes = [r for r in routes if '/asl' in r['path'] or '/image' in r['path']]
print("🎯 RUTAS DE PROCESAMIENTO ASL/IMAGEN:")
for route in sorted(asl_routes, key=lambda x: x['path']):
    methods_str = ', '.join(sorted(route['methods']))
    print(f"   {methods_str:12} {route['path']:35} ({route['name']})")

print("\n" + "=" * 60)

# Verificar la ruta específica que busca el frontend
target_route = '/api/image/asl/predict_space'
route_exists = any(r['path'] == target_route and 'POST' in r['methods'] for r in routes)

print("🔍 VERIFICACIÓN DE RUTA ESPECÍFICA:")
print(f"   Ruta buscada: POST {target_route}")
if route_exists:
    print("   ✅ ESTADO: ENCONTRADA")
    matching_route = next(r for r in routes if r['path'] == target_route)
    print(f"   📋 Métodos disponibles: {', '.join(matching_route['methods'])}")
    print(f"   🏷️  Nombre interno: {matching_route['name']}")
else:
    print("   ❌ ESTADO: NO ENCONTRADA")
    
    # Sugerir rutas similares
    similar_routes = [r for r in routes if '/asl' in r['path'] or 'predict' in r['path']]
    if similar_routes:
        print("   🔍 Rutas similares disponibles:")
        for route in similar_routes:
            methods_str = ', '.join(route['methods'])
            print(f"      {methods_str:10} {route['path']}")

print("\n" + "🚀 VERIFICACIÓN COMPLETADA")
