# reports/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

# --- Modelo para dashboard ---

class KpiConVariacion(BaseModel):
    valor: float
    variacion: float = Field(0.0, description="Ej: 0.05 para +5%")

class TopProducto(BaseModel):
    nombre: str
    cantidad: int
    monto: float

class AdminKPIResponse(BaseModel):
    ventasTotales: float
    ingresosDelivery: float
    numeroPedidos: int
    ticketPromedio: float
    topProductos: List[TopProducto]    

class TopProductoMargen(BaseModel):
    nombre: str
    monto: float
    margenEstimado: float

class OwnerSummaryResponse(BaseModel):
    ventasTotales: KpiConVariacion
    margenEstimado: KpiConVariacion
    numeroPedidos: KpiConVariacion
    ticketPromedio: KpiConVariacion
    topPlatos: List[TopProductoMargen]

# --- Modelo para reporte logistica ---

class KpiTiempo(BaseModel):
    minutos: int
    alertaSLA: bool = False

class MotivoCancelacion(BaseModel):
    motivo:str
    cantidad: int

class LogisticsKPIResponse(BaseModel):
    tiempoMedioPreparacion:KpiTiempo            
    tiempoMedioEnRuta:KpiTiempo            
    otdPorcentaje: float
    cancelaciones: List[MotivoCancelacion]

# --- Modelos para reportes y auditoria

class VentaReporteItem(BaseModel):
    fecha:datetime
    orden: str
    cliente: str
    item: str
    cantidad: int
    precio: float
    total: float
    estado: str

class AuditEvent(BaseModel):
    id: str
    fecha: datetime
    usuario: str
    tipoEvento: str
    descripcion: str

class Boleta(BaseModel):
    id: str
    boletaId: str
    ordenId: str
    fechaEmision: datetime
    monto: float
    url_pdf: str               