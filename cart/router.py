# cart/router.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from .schemas import (
    Carrito, CartOut, CartItem, CartItemAdd, CartItemUpdate, 
    CouponApply, CartMerge
)
from auth.schemas import User, TokenResponse, UserBase
from auth.router import get_current_user 
from admin.schemas import Cupon
from catalog.schemas import Producto, VarianteProducto
from beanie import BeanieObjectId, Link

router = APIRouter(
    prefix="/api/carrito",
    tags=["3. Carrito y Checkout"]
)

# --- Funciones de Ayuda ---

async def recalcular_totales(carrito: Carrito) -> CartOut:
    subtotal_general = 0
    for item in carrito.items:
        item.subtotal = item.precioUnitario * item.cantidad
        subtotal_general += item.subtotal
    
    descuento = 0
    mensaje_cupon = None
    
    if carrito.cuponCodigo:
        cupon = await Cupon.find_one(Cupon.codigo == carrito.cuponCodigo)
        if cupon:
            if cupon.tipo == "Porcentaje":
                descuento = subtotal_general * (cupon.valor / 100)
            elif cupon.tipo == "Monto Fijo":
                descuento = cupon.valor
            mensaje_cupon = f"Cupón '{cupon.codigo}' aplicado"
        else:
            mensaje_cupon = "Cupón no válido"
            carrito.cuponCodigo = None 

    total = subtotal_general - descuento
    
    return CartOut(
        id=carrito.id,
        items=carrito.items,
        subtotalGeneral=subtotal_general,
        descuento=descuento,
        total=total,
        mensajeCupon=mensaje_cupon
    )

async def get_or_create_cart(propietario: User) -> Carrito:
    carrito = await Carrito.find_one(Carrito.propietario.id == propietario.id)
    if not carrito:
        carrito = Carrito(propietario=propietario)
        await carrito.insert()
    return carrito

# === Endpoints para CARRITO  ===

@router.get("", response_model=CartOut)
async def obtener_carrito(usuario: User = Depends(get_current_user)):
    carrito = await get_or_create_cart(usuario)
    return await recalcular_totales(carrito)

@router.post("/items", response_model=CartOut)
async def agregar_item_al_carrito(
    item_data: CartItemAdd, 
    usuario: User = Depends(get_current_user)
):
    carrito = await get_or_create_cart(usuario)
    
    producto = await Producto.get(item_data.producto_id)
    if not producto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
        
    variante_encontrada = None
    for v in producto.variantes:
        if v.sku == item_data.variante_sku:
            variante_encontrada = v
            break
            
    if not variante_encontrada:
         raise HTTPException(status.HTTP_404_NOT_FOUND, "SKU de variante no encontrado")

    item_existente = next(
        (item for item in carrito.items if item.variante_sku == item_data.variante_sku), 
        None
    )
    
    if item_existente:
        item_existente.cantidad += item_data.cantidad
    else:
        nuevo_item = CartItem(
            producto_id=item_data.producto_id,
            variante_sku=item_data.variante_sku,
            nombreProducto=f"{producto.nombre} ({variante_encontrada.valor})",
            precioUnitario=variante_encontrada.precio,
            cantidad=item_data.cantidad,
            subtotal=0
        )
        carrito.items.append(nuevo_item)
    
    await carrito.save()
    return await recalcular_totales(carrito)

@router.put("/items", response_model=CartOut)
async def actualizar_cantidad_item(
    update_data: CartItemUpdate, 
    usuario: User = Depends(get_current_user)
):
    carrito = await get_or_create_cart(usuario)
    
    item_existente = next(
        (item for item in carrito.items if item.variante_sku == update_data.variante_sku), 
        None
    )
    
    if not item_existente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item no encontrado en el carrito")
    
    if update_data.nuevaCantidad < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La cantidad mínima es 1")

    item_existente.cantidad = update_data.nuevaCantidad
    await carrito.save()
    return await recalcular_totales(carrito)

@router.delete("/items/{variante_sku}", response_model=CartOut)
async def eliminar_item_del_carrito(
    variante_sku: str, 
    usuario: User = Depends(get_current_user)
):
    carrito = await get_or_create_cart(usuario)
    
    item_existente = next(
        (item for item in carrito.items if item.variante_sku == variante_sku), 
        None
    )
    
    if not item_existente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item no encontrado en el carrito")
    
    carrito.items.remove(item_existente)
    await carrito.save()
    return await recalcular_totales(carrito)

@router.post("/cupon", response_model=CartOut)
async def aplicar_cupon(
    cupon_data: CouponApply, 
    usuario: User = Depends(get_current_user)
):
    carrito = await get_or_create_cart(usuario)
    
    cupon = await Cupon.find_one(Cupon.codigo == cupon_data.codigoCupon)
    if not cupon or cupon.estado != "Activo":
        carrito.cuponCodigo = None
        await carrito.save()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El cupón no es válido o está vencido")

    carrito.cuponCodigo = cupon.codigo
    await carrito.save()
    
    return await recalcular_totales(carrito)

@router.delete("/cupon", response_model=CartOut)
async def quitar_cupon(usuario: User = Depends(get_current_user)):
    carrito = await get_or_create_cart(usuario)
    carrito.cuponCodigo = None
    await carrito.save()
    return await recalcular_totales(carrito)