# checkout/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from beanie import Document, Link, BeanieObjectId
from auth.schemas import User
from cart.schemas import CartItem 

# --- Modelo para Método de Entrega ---

class MetodoEntregaDetalles(BaseModel):
    direccion: Optional[str] = None
    zona: Optional[str] = None
    sucursalId: Optional[str] = None

class MetodoEntrega(BaseModel):
    metodo: str 
    detalles: MetodoEntregaDetalles

# --- Modelos para Iniciar Pago  ---
class IniciarPagoResponse(BaseModel):
    url_pago: str 
    id_transaccion: str 

# --- Modelos para Confirmar Pago  ---
class ConfirmarPagoRequest(BaseModel):
    datosGateway: Dict[str, Any]

# --- Modelos de Documento ---

class Orden(Document):
    propietario: Link[User]
    numeroOrden: str = Field(..., unique=True)
    fecha: datetime = Field(default_factory=datetime.now)
    estado: str 
    items: List[CartItem] 
    costoEnvio: float = 0.0
    descuento: float = 0.0
    total: float
    
    class Settings:
        name = "ordenes"

class Boleta(Document):
    orden: Link[Orden]
    boletaId: str = Field(..., unique=True) 
    fechaEmision: datetime = Field(default_factory=datetime.now)
    monto: float
    url_pdf: str
    
    class Settings:
        name = "boletas"

# --- Schemas para la API ---

class OrdenOut(BaseModel):
    id: BeanieObjectId = Field(..., alias="_id")
    numeroOrden: str
    fecha: datetime
    estado: str
    total: float
    items: List[CartItem]
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True