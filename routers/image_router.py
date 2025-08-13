import logging
import time
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
try:
    from ..config import ASL_DEBUG
except ImportError:
    from config import ASL_DEBUG  # type: ignore

try:
    from ..services.image_service import analyze_image, process_sign_language
    from ..common.service_utils import load_and_validate_image
    from ..common.router_utils import handle_errors
except ImportError:  # Fallback if relative import fails (direct run)
    from services.image_service import analyze_image, process_sign_language  # type: ignore
    from common.service_utils import load_and_validate_image  # type: ignore
    from common.router_utils import handle_errors  # type: ignore

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

router = APIRouter(
    prefix="/api/image",
    tags=["imagen"],
    responses={404: {"description": "Recurso no encontrado"}},
)

# -----------------------------
# Procesamiento de imágenes generales
# Este endpoint era para detección de objetos general, ahora solo lo mantenemos por compatibilidad
# -----------------------------
@router.post("/process-image")
@handle_errors
async def process_image(file: UploadFile = File(...)):
    """
    Procesa imágenes generales para detección de objetos y descripción.
    Esto es más para cosas como fotos normales, no específicamente ASL.
    """
    logger.info(
        f"[IMAGE_FLOW] 📥 Recibida imagen /process-image filename={file.filename} ct={file.content_type}"
    )
    image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
    logger.debug("[IMAGE_FLOW] 🔍 Imagen validada, iniciando análisis")
    result = await analyze_image(image)
    logger.info(
        f"[IMAGE_FLOW] ✅ Completado objects={len(result.get('objects', []))} has_description={bool(result.get('description'))}"
    )
    return {
        "objects": result.get("objects", []),
        "description": result.get("description", "No se pudo generar una descripción"),
    }

# -----------------------------
# ASL modo legacy - mantenemos por si alguien lo usa aún
# Este endpoint devuelve el formato "crudo" de Gradio sin estandarizar
# -----------------------------
@router.post("/analyze-sign-language")
@handle_errors
async def analyze_sign_language(file: UploadFile = File(...)):
    """
    Ruta legacy para reconocimiento ASL.
    Devuelve directamente lo que viene de Gradio Space sin limpiar los datos.
    Solo la mantenemos por compatibilidad, mejor usar /asl/predict.
    """
    logger.info(
        f"[ASL_FLOW] 📥 Recibida imagen /analyze-sign-language filename={file.filename} ct={file.content_type}"
    )
    image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
    legacy = await process_sign_language(image)
    logger.debug(
        f"[ASL_FLOW] 📦 Respuesta legacy keys={list(legacy.keys())} resultado={legacy.get('resultado')} confianza={legacy.get('confianza')}"
    )
    return legacy

# -----------------------------
# Funciones auxiliares para manejar datos ASL
# -----------------------------

def _standardize_asl_result(result: dict) -> dict:
    """
    Convierte la respuesta "cruda" de Gradio Space a un formato más limpio y consistente.
    
    Gradio a veces devuelve confianzas en 0-1, otras en 0-100, esto lo normaliza.
    También maneja casos donde no hay predicción o hay errores.
    """
    # Extraemos la predicción y limpiamos la confianza
    prediction = result.get("resultado")
    raw_conf = result.get("confianza", 0.0) or 0.0
    try:
        conf = float(raw_conf)
        if conf <= 1.0:  # Si viene como decimal (0.85), lo convertimos a porcentaje (85)
            conf *= 100
    except Exception:
        conf = 0.0
    
    # Determinamos si hubo algún error o falta de reconocimiento
    has_error = (
        bool(result.get("error"))
        or not prediction
        or conf <= 0.0
        or prediction in ("Sin reconocimiento", "Error en reconocimiento")
    )
    return {
        "success": not has_error,
        "prediction": None if has_error else prediction,
        "confidence": 0.0 if has_error else round(conf, 2),
        "alternatives": result.get("alternativas", []),
        "message": "Predicción obtenida" if not has_error else "Sin predicción",
        "error": result.get("error") if has_error else None,
        "source": "remote",
    }


def _validate_content_type(file: UploadFile):
    """
    Verifica que el archivo subido sea realmente una imagen.
    Si no es un tipo permitido, rechaza la petición inmediatamente.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no soportado. Tipos permitidos: {ALLOWED_IMAGE_TYPES}",
        )

# -----------------------------
# Los endpoints ASL que realmente importan - estos son los buenos
# Ambos devuelven el mismo formato limpio y estandarizado
# -----------------------------
@router.post("/asl/predict")
async def predict_asl(file: UploadFile = File(...)):
    """
    El endpoint principal para reconocimiento ASL.
    Toma una imagen y devuelve qué signo detectó con confianza.
    Incluye correlación para seguimiento y campos de debug cuando está activado.
    """
    _validate_content_type(file)
    corr_id = uuid.uuid4().hex[:12]  # ID para seguimiento de esta petición específica
    t0 = time.time()
    try:
        logger.info(
            f"[ASL_FLOW][{corr_id}] 📥 Nueva imagen para procesar: {file.filename} tipo={file.content_type}"
        )
        image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 🖼️ Imagen cargada correctamente, tamaño={getattr(image,'size',None)} modo={getattr(image,'mode',None)}"
        )
        
        # Llamamos a Gradio Space y medimos cuánto tarda
        t_space_start = time.time()
        legacy = await process_sign_language(image, correlation_id=corr_id)
        t_space = (time.time() - t_space_start) * 1000
        
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 📦 Gradio respondió en {t_space:.1f}ms: '{legacy.get('resultado')}' con {legacy.get('confianza')}% confianza"
        )
        
        # Convertimos el resultado "crudo" a nuestro formato estándar
        std = _standardize_asl_result(legacy)
        total_ms = (time.time() - t0) * 1000
        
        logger.info(
            f"[ASL_FLOW][{corr_id}] ✅ Proceso completado en {total_ms:.1f}ms - éxito={std['success']} predicción='{std.get('prediction')}' confianza={std.get('confidence')}%"
        )
        
        # Agregamos datos de seguimiento
        std["correlation_id"] = corr_id
        if ASL_DEBUG:
            std["legacy_raw"] = legacy  # La respuesta original de Gradio para debug
            std["timing_ms"] = {"total": round(total_ms,2), "space_call": round(t_space,2)}
        return std
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ASL_FLOW][{corr_id}] Error predict_asl: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.post("/asl/predict_space")
async def predict_asl_space(file: UploadFile = File(...)):
    """
    Alias del endpoint principal, mantenido por compatibilidad histórica.
    Hace exactamente lo mismo que /asl/predict pero con URL diferente.
    Algunos clientes antiguos podrían estar usando esta ruta.
    """
    _validate_content_type(file)
    corr_id = uuid.uuid4().hex[:12]  # ID para seguimiento de esta petición específica
    t0 = time.time()
    try:
        logger.info(
            f"[ASL_FLOW][{corr_id}] 📥 Nueva imagen via predict_space: {file.filename} tipo={file.content_type}"
        )
        image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 🖼️ Imagen cargada (via alias), tamaño={getattr(image,'size',None)} modo={getattr(image,'mode',None)}"
        )
        
        # Llamamos a Gradio Space y medimos cuánto tarda
        t_space_start = time.time()
        legacy = await process_sign_language(image, correlation_id=corr_id)
        t_space = (time.time() - t_space_start) * 1000
        
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 📦 Gradio respondió en {t_space:.1f}ms (via alias): '{legacy.get('resultado')}' con {legacy.get('confianza')}% confianza"
        )
        
        # Convertimos el resultado "crudo" a nuestro formato estándar
        std = _standardize_asl_result(legacy)
        total_ms = (time.time() - t0) * 1000
        
        logger.info(
            f"[ASL_FLOW][{corr_id}] ✅ Proceso completado en {total_ms:.1f}ms (via alias) - éxito={std['success']} predicción='{std.get('prediction')}' confianza={std.get('confidence')}%"
        )
        
        # Agregamos datos de seguimiento
        std["correlation_id"] = corr_id
        if ASL_DEBUG:
            std["legacy_raw"] = legacy  # La respuesta original de Gradio para debug
            std["timing_ms"] = {"total": round(total_ms,2), "space_call": round(t_space,2)}
        return std
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ASL_FLOW][{corr_id}] Error predict_asl_space: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")
