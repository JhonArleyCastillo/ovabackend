#!/bin/bash
# Script para verificar la configuración de seguridad HTTPS/CORS en producción

# Colores para mensajes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Verificador de Configuración HTTPS/CORS en Producción ===${NC}"
echo "Este script verifica que la configuración del servidor esté optimizada para seguridad."

# 1. Verificar que Nginx esté instalado y configurado
echo -e "\n${YELLOW}Verificando Nginx...${NC}"
if systemctl is-active --quiet nginx; then
  echo -e "${GREEN}✓ Nginx está ejecutándose${NC}"
else
  echo -e "${RED}✗ Nginx no está ejecutándose. Por favor, inicie el servicio:${NC}"
  echo "   sudo systemctl start nginx"
fi

# 2. Verificar archivo de configuración Nginx para el sitio
NGINX_CONFIG="/etc/nginx/sites-enabled/api.ovaonline.tech"
echo -e "\n${YELLOW}Verificando configuración Nginx...${NC}"

if [ -f "$NGINX_CONFIG" ]; then
  echo -e "${GREEN}✓ Archivo de configuración encontrado${NC}"
  
  # Verificar redirección de HTTP a HTTPS
  if grep -q "return 301 https://\$host\$request_uri" "$NGINX_CONFIG"; then
    echo -e "${GREEN}✓ Redirección HTTP a HTTPS configurada${NC}"
  else
    echo -e "${RED}✗ No se encontró redirección HTTP a HTTPS${NC}"
  fi
  
  # Verificar configuración SSL
  if grep -q "ssl_certificate" "$NGINX_CONFIG"; then
    echo -e "${GREEN}✓ Certificados SSL configurados${NC}"
  else
    echo -e "${RED}✗ No se encontró configuración de certificados SSL${NC}"
  fi
  
  # Verificar CORS
  if grep -q "Access-Control-Allow-Origin" "$NGINX_CONFIG"; then
    echo -e "${GREEN}✓ Cabeceras CORS configuradas en Nginx${NC}"
    
    # Verificar que solo se permitan orígenes HTTPS
    HTTP_ORIGINS=$(grep -o "Access-Control-Allow-Origin.*http:" "$NGINX_CONFIG" | wc -l)
    if [ $HTTP_ORIGINS -gt 0 ]; then
      echo -e "${RED}✗ Se encontraron orígenes HTTP en la configuración CORS${NC}"
    else
      echo -e "${GREEN}✓ Solo se permiten orígenes HTTPS en la configuración CORS${NC}"
    fi
  else
    echo -e "${YELLOW}⚠ No se encontraron cabeceras CORS en Nginx${NC}"
  fi
else
  echo -e "${RED}✗ No se encontró el archivo de configuración Nginx${NC}"
  echo "   Debería estar en: $NGINX_CONFIG"
fi

# 3. Verificar configuración FastAPI
BACKEND_DIR="/var/www/ovaweb/backend"
ENV_FILE="$BACKEND_DIR/.env"

echo -e "\n${YELLOW}Verificando configuración FastAPI...${NC}"

if [ -f "$ENV_FILE" ]; then
  echo -e "${GREEN}✓ Archivo .env encontrado${NC}"
  
  # Verificar orígenes CORS
  if grep -q "ALLOWED_ORIGINS" "$ENV_FILE"; then
    echo -e "${GREEN}✓ Variable ALLOWED_ORIGINS configurada${NC}"
    
    # Verificar que solo contenga orígenes HTTPS (excepto localhost)
    HTTP_ORIGINS=$(grep "ALLOWED_ORIGINS" "$ENV_FILE" | grep -o "http:" | grep -v "localhost" | wc -l)
    if [ $HTTP_ORIGINS -gt 0 ]; then
      echo -e "${RED}✗ Se encontraron orígenes HTTP (no localhost) en ALLOWED_ORIGINS${NC}"
    else
      echo -e "${GREEN}✓ Solo se permiten orígenes HTTPS (o localhost) en ALLOWED_ORIGINS${NC}"
    fi
  else
    echo -e "${RED}✗ No se encontró la variable ALLOWED_ORIGINS${NC}"
  fi
  
  # Verificar modo de producción
  if grep -q "ENVIRONMENT=production" "$ENV_FILE"; then
    echo -e "${GREEN}✓ Entorno configurado como producción${NC}"
  else
    echo -e "${RED}✗ El entorno no está configurado como producción${NC}"
  fi
else
  echo -e "${RED}✗ No se encontró el archivo .env${NC}"
  echo "   Debería estar en: $ENV_FILE"
fi

# 4. Probar la conexión HTTPS
echo -e "\n${YELLOW}Probando conexión HTTPS...${NC}"
CURL_RESULT=$(curl -s -o /dev/null -w "%{http_code}" https://api.ovaonline.tech/status)

if [ "$CURL_RESULT" = "200" ] || [ "$CURL_RESULT" = "404" ]; then
  echo -e "${GREEN}✓ Conexión HTTPS funcionando (código HTTP: $CURL_RESULT)${NC}"
else
  echo -e "${RED}✗ No se pudo conectar vía HTTPS (código HTTP: $CURL_RESULT)${NC}"
fi

# 5. Verificar configuración del servicio systemd
SERVICE_FILE="/etc/systemd/system/ovaweb.service"
echo -e "\n${YELLOW}Verificando servicio systemd...${NC}"

if [ -f "$SERVICE_FILE" ]; then
  echo -e "${GREEN}✓ Archivo de servicio systemd encontrado${NC}"
  
  # Verificar que el servicio esté activo
  if systemctl is-active --quiet ovaweb; then
    echo -e "${GREEN}✓ Servicio ovaweb está ejecutándose${NC}"
  else
    echo -e "${RED}✗ El servicio ovaweb no está ejecutándose${NC}"
    echo "   sudo systemctl start ovaweb"
  fi
else
  echo -e "${RED}✗ No se encontró el archivo de servicio systemd${NC}"
  echo "   Debería estar en: $SERVICE_FILE"
  echo "   Puede copiar el archivo de configuración desde el repositorio."
fi

echo -e "\n${YELLOW}=== Verificación completada ===${NC}"
