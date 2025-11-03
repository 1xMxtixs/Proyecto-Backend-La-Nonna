# catalog/router.py
from fastapi import (
    APIRouter, HTTPException, status, 
    UploadFile, File, Form, Query
)
from typing import List, Optional
import shutil
import os

# --- 1. Importaciones de Beanie y Schemas ---
from beanie import BeanieObjectId, Link
from beanie.operators import In
from .schemas import (
    Categoria, Etiqueta, Producto,
    CategoriaCreate, CategoriaOut, 
    ProductoCreate, ProductoOut,
    VarianteProducto, ImagenProducto
)

router = APIRouter(
    prefix="/api",
    tags=["2. Catálogo y Productos"]
)


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# === Endpoints para CATEGORIAS  ===

@router.post("/categorias", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
async def crear_categoria(categoria_data: CategoriaCreate):
    slug_existente = await Categoria.find_one(Categoria.slug == categoria_data.slug)
    if slug_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El slug '{categoria_data.slug}' ya está en uso"
        )
    
    categoria_padre = None
    if categoria_data.categoriaPadreId:
        categoria_padre = await Categoria.get(categoria_data.categoriaPadreId)
        if not categoria_padre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La categoría padre no existe"
            )
            
    nueva_categoria = Categoria(
        nombre=categoria_data.nombre,
        slug=categoria_data.slug,
        categoriaPadre=categoria_padre
    )
    
    await nueva_categoria.insert()
    
    return CategoriaOut.model_validate(nueva_categoria)

@router.get("/categorias", response_model=List[CategoriaOut])
async def obtener_categorias():

    categorias = await Categoria.find_all().project(CategoriaOut).to_list()
    return categorias


# === Endpoints para ETIQUETAS  ===

@router.post("/etiquetas", response_model=Etiqueta, status_code=status.HTTP_201_CREATED)
async def crear_etiqueta(etiqueta_data: Etiqueta):
    nombre_existente = await Etiqueta.find_one(Etiqueta.nombre == etiqueta_data.nombre)
    if nombre_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La etiqueta '{etiqueta_data.nombre}' ya existe"
        )

    nueva_etiqueta = Etiqueta(nombre=etiqueta_data.nombre)
    await nueva_etiqueta.insert()
    return nueva_etiqueta

@router.get("/etiquetas", response_model=List[Etiqueta])
async def obtener_etiquetas():
    etiquetas = await Etiqueta.find_all().to_list()
    return etiquetas


# === Endpoints para PRODUCTOS  ===

@router.post("/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def crear_producto(producto_data: ProductoCreate):
    sku_existente = await Producto.find_one(Producto.sku == producto_data.sku)
    if sku_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El SKU '{producto_data.sku}' ya está en uso"
        )
    
    categoria = await Categoria.get(producto_data.categoriaId)
    if not categoria:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
        
    etiquetas = await Etiqueta.find(
        In(Etiqueta.id, producto_data.etiquetaIds)
    ).to_list()
    
    nuevo_producto = Producto(
        nombre=producto_data.nombre,
        sku=producto_data.sku,
        descripcion=producto_data.descripcion,
        precio_base=producto_data.precio_base,
        estado=producto_data.estado,
        categoria=categoria,
        etiquetas=etiquetas
    )
    
    await nuevo_producto.insert()
    
    return ProductoOut.model_validate(nuevo_producto)

@router.get("/productos", response_model=List[ProductoOut])
async def obtener_productos():
    productos = await Producto.find_all().project(ProductoOut).to_list()
    return productos

@router.get("/productos/{producto_id}", response_model=ProductoOut)
async def obtener_producto(producto_id: BeanieObjectId):
    producto = await Producto.find_one(
        Producto.id == producto_id
    ).project(ProductoOut)
    
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    return producto

@router.put("/productos/{producto_id}", response_model=ProductoOut)
async def actualizar_producto(producto_id: BeanieObjectId, producto_data: ProductoCreate):

    producto = await Producto.get(producto_id)
    if not producto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    
    sku_existente = await Producto.find_one(
        Producto.sku == producto_data.sku,
        Producto.id != producto_id 
    )
    if sku_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El SKU '{producto_data.sku}' ya está en uso por otro producto"
        )
        
    categoria = await Categoria.get(producto_data.categoriaId)
    etiquetas = await Etiqueta.find(In(Etiqueta.id, producto_data.etiquetaIds)).to_list()

    update_data = producto_data.model_dump(exclude_unset=True)
    update_data["categoria"] = categoria
    update_data["etiquetas"] = etiquetas
    
    await producto.update({"$set": update_data})
    
    await producto.reload() 
    return ProductoOut.model_validate(producto)

# === Endpoints para VARIANTES  ===

@router.post("/productos/{producto_id}/variantes", response_model=ProductoOut)
async def crear_variante_para_producto(
    producto_id: BeanieObjectId, 
    variante_data: VarianteProducto
):
    producto = await Producto.get(producto_id)
    if not producto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    
    await producto.update({"$push": {"variantes": variante_data.model_dump()}})
    
    producto_actualizado = await Producto.find_one(
        Producto.id == producto_id
    ).project(ProductoOut)
    
    return producto_actualizado

@router.get("/productos/{producto_id}/variantes", response_model=List[VarianteProducto])
async def obtener_variantes_por_producto(producto_id: BeanieObjectId):
    producto = await Producto.get(producto_id)
    if not producto:
         raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    
    return producto.variantes

# === Endpoints para IMÁGENES  ===

@router.post("/productos/{producto_id}/imagenes", response_model=ImagenProducto)
async def agregar_imagen_a_producto(
    producto_id: BeanieObjectId,
    archivo: UploadFile = File(..., description="El archivo de imagen a subir"),
    textoAlternativo: str = Form(None, description="Texto alternativo para accesibilidad"),
    esPrincipal: bool = Form(False, description="Marcar como imagen principal")
):
    producto = await Producto.get(producto_id)
    if not producto:
         raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    
    if archivo.size > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen excede el tamaño permitido (2MB)"
        )

    file_path = os.path.join(UPLOAD_DIR, archivo.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
    
    url_ficticia = f"/static/{archivo.filename}" 
    
    nueva_imagen = ImagenProducto(
        url=url_ficticia,
        textoAlternativo=textoAlternativo,
        esPrincipal=esPrincipal
    )
    
    await producto.update({"$push": {"imagenes": nueva_imagen.model_dump()}})
    
    return nueva_imagen

@router.delete("/productos/{producto_id}/imagenes", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_imagen_de_producto(
    producto_id: BeanieObjectId,
    url_imagen: str = Query(..., description="La URL de la imagen a eliminar")
):
    producto = await Producto.get(producto_id)
    if not producto:
         raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    file_path = os.path.join(UPLOAD_DIR, os.path.basename(url_imagen))
    if os.path.exists(file_path):
        os.remove(file_path)

    await producto.update({"$pull": {"imagenes": {"url": url_imagen}}})
    
    return