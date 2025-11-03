# cart/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from beanie import Document, Link, BeanieObjectId
from auth.schemas import User 

# --- Modelo Embebido (dentro de Carrito) ---
class CartItem(BaseModel):
    producto_id: BeanieObjectId
    variante_sku: str
    nombreProducto: str
    precioUnitario: float
    cantidad: int
    subtotal: float

# --- Modelo de Documento (Base de Datos) ---
class Carrito(Document):
    propietario: Link[User]
    items: List[CartItem] = []
    cuponCodigo: Optional[str] = None
    
    class Settings:
        name = "carritos"
        indexes = [
            [("propietario", 1)], 
        ]

# --- Schemas para la API (BaseModel) ---

class CartItemAdd(BaseModel):
    producto_id: BeanieObjectId
    variante_sku: str 
    cantidad: int = Field(1, gt=0)

class CartItemUpdate(BaseModel):
    variante_sku: str
    nuevaCantidad: int = Field(..., gt=0, description="La cantidad mínima es 1")

class CouponApply(BaseModel):
    codigoCupon: str

class CartMerge(BaseModel):
    itemsLocales: List[CartItemAdd]

class CartOut(BaseModel):
    id: BeanieObjectId = Field(..., alias="_id")
    items: List[CartItem]
    subtotalGeneral: float
    descuento: float
    total: float
    mensajeCupon: Optional[str] = None
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True