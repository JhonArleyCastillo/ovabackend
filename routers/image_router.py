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
# Imagen general
# -----------------------------
@router.post("/process-image")
@handle_errors
async def process_image(file: UploadFile = File(...)):
    """Procesa una imagen general (detección + descripción)."""
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
# ASL legacy (sin estandarizar)
# -----------------------------
@router.post("/analyze-sign-language")
@handle_errors
async def analyze_sign_language(file: UploadFile = File(...)):
    """Ruta legacy que devuelve el formato 'legacy' sin estandarizar."""
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
# Helpers
# -----------------------------

def _standardize_asl_result(result: dict) -> dict:
    """Convierte el resultado 'legacy' a un contrato estándar."""
    prediction = result.get("resultado")
    raw_conf = result.get("confianza", 0.0) or 0.0
    try:
        conf = float(raw_conf)
        if conf <= 1.0:  # Normalizar si viene 0-1
            conf *= 100
    except Exception:
        conf = 0.0
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
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no soportado. Tipos permitidos: {ALLOWED_IMAGE_TYPES}",
        )

# -----------------------------
# ASL estandarizado
# -----------------------------
@router.post("/asl/predict")
async def predict_asl(file: UploadFile = File(...)):
    """Predicción ASL remota (resultado estandarizado)."""
    _validate_content_type(file)
    corr_id = uuid.uuid4().hex[:12]
    t0 = time.time()
    try:
        logger.info(
            f"[ASL_FLOW][{corr_id}] 📥 Recibida imagen /asl/predict fname={file.filename} ct={file.content_type}"
        )
        image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 🖼️ Imagen validada size={getattr(image,'size',None)} mode={getattr(image,'mode',None)}"
        )
        t_space_start = time.time()
        legacy = await process_sign_language(image, correlation_id=corr_id)
        t_space = (time.time() - t_space_start) * 1000
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 📦 Space legacy ms={t_space:.1f} resultado={legacy.get('resultado')} conf={legacy.get('confianza')} alt={len(legacy.get('alternativas', []))}"
        )
        std = _standardize_asl_result(legacy)
        total_ms = (time.time() - t0) * 1000
        logger.info(
            f"[ASL_FLOW][{corr_id}] ✅ Estandarización success={std['success']} prediction={std.get('prediction')} conf={std.get('confidence')} total_ms={total_ms:.1f}"
        )
        std["correlation_id"] = corr_id
        if ASL_DEBUG:
            std["legacy_raw"] = legacy
            std["timing_ms"] = {"total": round(total_ms,2), "space_call": round(t_space,2)}
        return std
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ASL_FLOW][{corr_id}] Error predict_asl: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.post("/asl/predict_space")
async def predict_asl_space(file: UploadFile = File(...)):
    """Alias histórico que produce el mismo resultado estandarizado."""
    _validate_content_type(file)
    corr_id = uuid.uuid4().hex[:12]
    t0 = time.time()
    try:
        logger.info(
            f"[ASL_FLOW][{corr_id}] 📥 Recibida imagen /asl/predict_space fname={file.filename} ct={file.content_type}"
        )
        image = await load_and_validate_image(file, ALLOWED_IMAGE_TYPES)
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 🖼️ Imagen validada size={getattr(image,'size',None)} mode={getattr(image,'mode',None)} (alias)"
        )
        t_space_start = time.time()
        legacy = await process_sign_language(image, correlation_id=corr_id)
        t_space = (time.time() - t_space_start) * 1000
        logger.debug(
            f"[ASL_FLOW][{corr_id}] 📦 Space legacy (alias) ms={t_space:.1f} resultado={legacy.get('resultado')} conf={legacy.get('confianza')} alt={len(legacy.get('alternativas', []))}"
        )
        std = _standardize_asl_result(legacy)
        total_ms = (time.time() - t0) * 1000
        logger.info(
            f"[ASL_FLOW][{corr_id}] ✅ Estandarización (alias) success={std['success']} prediction={std.get('prediction')} conf={std.get('confidence')} total_ms={total_ms:.1f}"
        )
        std["correlation_id"] = corr_id
        if ASL_DEBUG:
            std["legacy_raw"] = legacy
            std["timing_ms"] = {"total": round(total_ms,2), "space_call": round(t_space,2)}
        return std
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ASL_FLOW][{corr_id}] Error predict_asl_space: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")
