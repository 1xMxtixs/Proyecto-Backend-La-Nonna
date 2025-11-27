# logistics/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

# --- Modelo para un item en la hoja de picking ---

class PickingItem(BaseModel):
    sku: str
    nombreProducto: str
    ubicacion: str
    cantidadPedida: int

# --- Modelo para el pedido en preparación ---

class PedidoParaPicking(BaseModel):
    id: str
    numeroOrden: str
    fecha: datetime 
    items: List[PickingItem]

# --- Modelo para confirmar cantidades ---

class ItemConfirmado(BaseModel):
    sku: str
    cantidadEncontrada: int

class ConfirmacionPicking(BaseModel):
    pedidoId: str
    itemsConfirmados: List[ItemConfirmado]

# --- Modelo de respuesta para impresion ---

class DocumentoImpresion(BaseModel):
    url_pdf: str
    mensaje: str


    
    
            