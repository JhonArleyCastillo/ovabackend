"""
Router para exportar datos de administradores y contactos en Excel o PDF.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
import mysql.connector
import io
import pandas as pd
import pdfkit

from backend.common.database_utils import DbDependency, DatabaseManager

router = APIRouter(
    prefix="/api/export",
    tags=["exportacion"]
)

@router.get("/")
async def exportar_datos(
    tipo: str = Query(..., regex="^(contactos|admins)$"),
    formato: str = Query("excel", regex="^(excel|pdf)$"),
    db: mysql.connector.connection.MySQLConnection = Depends(DbDependency)
):
    """
    Exporta datos en Excel o PDF.
    - tipo: 'contactos' o 'admins'
    - formato: 'excel' o 'pdf'
    """
    # Consultar datos
    if tipo == "contactos":
        df = pd.DataFrame(DatabaseManager.execute_query(
            db,
            "SELECT id, nombre, email, asunto, mensaje, fecha_envio, leido, respondido FROM contactos",
            fetch_all=True
        ))
        filename = "contactos"
    else:
        df = pd.DataFrame(DatabaseManager.execute_query(
            db,
            "SELECT id, email, nombre, es_superadmin, activo, fecha_creacion, fecha_actualizacion FROM administradores",
            fetch_all=True
        ))
        filename = "administradores"

    if formato == "excel":
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    else:
        # Generar HTML intermedio
        html = df.to_html(index=False)
        try:
            pdf = pdfkit.from_string(html, False)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generando PDF: {e}")
        return StreamingResponse(
            io.BytesIO(pdf),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )
