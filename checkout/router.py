# checkout/router.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from .schemas import (
    MetodoEntrega, IniciarPagoResponse, 
    ConfirmarPagoRequest, Orden, Boleta, OrdenOut
)
from cart.schemas import Carrito
from cart.router import get_or_create_cart, recalcular_totales
from auth.schemas import User
from auth.router import get_current_user
import datetime
import random

router = APIRouter(
    prefix="/api/checkout",
    tags=["3. Carrito y Checkout"]
)

# === Endpoints para CHECKOUT  ===

@router.post("/entrega", response_model=Dict[str, Any])
async def seleccionar_metodo_entrega(
    metodo: MetodoEntrega,
    usuario: User = Depends(get_current_user)
):
    costo_envio = 0
    if metodo.metodo == "delivery" and metodo.detalles.zona == "Zona 1":
        costo_envio = 3500.0
    
    carrito = await get_or_create_cart(usuario)
    
    cart_out = await recalcular_totales(carrito)
    total_con_envio = cart_out.total + costo_envio
    
    return {
        "costo_envio": costo_envio, 
        "metodo_seleccionado": metodo.metodo,
        "nuevo_total_estimado": total_con_envio
    }

@router.post("/iniciar-pago", response_model=IniciarPagoResponse)
async def iniciar_pago(usuario: User = Depends(get_current_user)):
    carrito = await get_or_create_cart(usuario)
    cart_out = await recalcular_totales(carrito)
    
    if not carrito.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay items en el carrito")
    
    id_transaccion_ficticia = f"tx_{random.randint(10000, 99999)}"
    url_pago_ficticia = f"https://pasarela.pago.cl/pagar?id={id_transaccion_ficticia}&monto={cart_out.total}"
    
    return IniciarPagoResponse(
        url_pago=url_pago_ficticia,
        id_transaccion=id_transaccion_ficticia
    )

@router.post("/confirmar-pago", response_model=OrdenOut)
async def confirmar_pago(
    confirmacion: ConfirmarPagoRequest,
    usuario: User = Depends(get_current_user)
):
    carrito = await get_or_create_cart(usuario)
    if not carrito.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay items en el carrito")
    pago_aprobado = True 
    
    if not pago_aprobado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pago rechazado por el proveedor"
        )
        
    cart_out = await recalcular_totales(carrito)

    numero_orden_nuevo = f"LN-2025-00{await Orden.count() + 1}"
    nueva_orden = Orden(
        propietario=usuario,
        numeroOrden=numero_orden_nuevo,
        estado="Pagado",
        items=carrito.items, 
        costoEnvio=0, 
        descuento=cart_out.descuento,
        total=cart_out.total 
    )
    await nueva_orden.insert()
    
    numero_boleta_nuevo = f"B-LN-000{await Boleta.count() + 1}"
    nueva_boleta = Boleta(
        orden=nueva_orden,
        boletaId=numero_boleta_nuevo,
        monto=nueva_orden.total,
        url_pdf=f"/static/boletas/{numero_boleta_nuevo}.pdf"
    )
    await nueva_boleta.insert()
    
    carrito.items = []
    carrito.cuponCodigo = None
    await carrito.save()
    
    
    return OrdenOut.model_validate(nueva_orden)