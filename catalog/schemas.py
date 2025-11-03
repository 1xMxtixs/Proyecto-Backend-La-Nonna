#catalog/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from beanie import Document, Link, BeanieObjectId
from datetime import datetime

# --- Modelos para categorias ---

class Categoria(Document):
    nombre: str
    slug: str = Field(..., unique=True)
    categoriaPadreId: Optional[Link["Categoria"]] = None

    class Settings:
        name = "categorias"

class Etiqueta(Document):
    nombre: str = Field(..., unique=True)

    class Settings: "etiquetas"        

# --- Modelo para Embebidos ---

class ImagenProducto(BaseModel):
    url: str
    textoAlternativo: Optional[str] = None
    esPrincipal: bool = False

class VarianteProducto(BaseModel):
    atributo: str
    valor: str
    sku: str
    precio: float = Field(..., gt=0)

class Producto(Document):
    nombre: str 
    sku: str = Field(..., unique=True, description="SKU principal del producto")
    descriopcion: Optional[str] = None
    precio_base: float = Field(..., gt=0)
    estado: str = "Borrador"

    categoria: Link[Categoria]
    etiquetas: List[Link[Etiqueta]]
    variantes: List[VarianteProducto] = []
    imagenes: List[ImagenProducto] = []

    fechaCreacion: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "productos"

class CategoriaCreate(BaseModel):
    nombre: str
    slug: str
    categoriaPadreId: Optional[BeanieObjectId] = None

class CategoriaOut(BaseModel):
    id: BeanieObjectId
    nombre: str
    slug: str
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class ProductoCreate(BaseModel):
    nombre: str
    sku: str
    descripcion: Optional[str] = None
    precio_base: float
    estado: str = "Borrador"
    categoriaId: BeanieObjectId 
    etiquetaIds: List[BeanieObjectId] = [] 

class ProductoOut(BaseModel):

    id: BeanieObjectId 
    nombre: str
    sku: str
    descripcion: Optional[str] = None
    precio_base: float
    estado: str
    categoria: CategoriaOut 
    
    class Config:
        from_attributes = True   
        arbitrary_types_allowed = True             

