# admin/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from beanie import Document, BeanieObjectId

# --- Modelo para Reglas del carrito (B-35) ---
class ReglasCarrito(Document):
    cantidadMinimaGlobal: int = Field(default=1, gt=0)
    cantidadMaximaPorSKU: int = Field(default=10, gt=0) 
    tiempoReservaStockMinutos: int = Field(default=15, gt=0)
    habilitarGuardarCarrito: bool = True 

    class Settings:
        name = "reglas_carrito"

# --- Modelo para Cupones (B-36) ---
class CuponBase(BaseModel):
    codigo: str = Field(..., description="El código que el cliente ingresará")
    tipo: str = Field("Porcentaje", description="Tipo de cupón: Porcentaje o Monto fijo")
    valor: float = Field(..., gt=0, description="Valor del descuento")
    pedidoMinimo: Optional[float] = Field(None, gt=0)
    vigenciaDesde: Optional[date] = None
    vigenciaHasta: Optional[date] = None
    categoriasExcluidas: Optional[List[str]] = []
    estado: str = "Activo"

class CuponCreate(CuponBase):
    pass

class Cupon(Document, CuponBase):
    class Settings:
        name = "cupones"

class CuponOut(CuponBase):
    id: BeanieObjectId = Field(..., alias="_id")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True