# checkout/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from beanie import Document, Link, BeanieObjectId
from auth.schemas import User

# --- 1. Modelo para Datos de Entrega ---
class DatosEntrega(BaseModel):
    nombre: str
    email: str
    telefono: str
    metodo: str 
    direccion: Optional[str] = None 

# --- 2. Inputs desde el Frontend ---
class ItemOrdenInput(BaseModel):
    nombre: str
    precio: float
    cantidad: int
    img: Optional[str] = None

class IniciarPagoRequest(BaseModel):
    items: List[ItemOrdenInput]
    total: float
    datos_entrega: Optional[DatosEntrega] = None


# --- 3. Respuesta hacia el Frontend ---
class WebpayInitResponse(BaseModel):
    url: str
    token: str
    orden_id: str

# --- 4. Request para confirmar  ---
class WebpayCommitRequest(BaseModel):
    token_ws: str

# --- 5. Modelos de Base de Datos ---
class Orden(Document):
    propietario: Link[User]
    numeroOrden: str = Field(..., unique=True)
    fecha: datetime = Field(default_factory=datetime.now)
    estado: str 
    items: List[ItemOrdenInput]
    total: float
    token_ws: Optional[str] = None 
    datos_entrega: Optional[DatosEntrega] = None
    
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

class OrdenOut(BaseModel):
    id: BeanieObjectId 
    numeroOrden: str
    estado: str
    total: float
    items: List[ItemOrdenInput] = []
    datos_entrega: Optional[DatosEntrega] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

       