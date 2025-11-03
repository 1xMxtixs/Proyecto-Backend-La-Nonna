# logistics/router.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from .schemas import (
    PedidoParaPicking, ConfirmacionPicking, 
    PickingItem, DocumentoImpresion, ItemConfirmado
)
from checkout.schemas import Orden 
from auth.schemas import User
from auth.router import get_current_user
import datetime

router = APIRouter(
    prefix="/api/logistica",
    tags=["5. Logística y Despacho"]
)

# === Endpoints para PICKING ===

@router.get("/pedidos-en-preparacion", response_model=List[PedidoParaPicking])
async def obtener_pedidos_en_preparacion(
    usuario: User = Depends(get_current_user)
):
    
    ordenes_pendientes = await Orden.find(
        Orden.estado == "Pagado"
    ).to_list()
    
    pedidos_para_picking = []
    for orden in ordenes_pendientes:
        items_picking = []
        for item_carrito in orden.items:
            items_picking.append(
                PickingItem(
                    sku=item_carrito.variante_sku,
                    nombreProducto=item_carrito.nombreProducto,
                    ubicacion="Pasillo A-1 (Simulado)",
                    cantidadPedida=item_carrito.cantidad
                )
            )
        
        pedidos_para_picking.append(
            PedidoParaPicking(
                id=str(orden.id), 
                numeroOrden=orden.numeroOrden,
                fecha=orden.fecha,
                items=items_picking
            )
        )
        
    return pedidos_para_picking

@router.post("/picking/confirmar", response_model=Dict[str, str])
async def confirmar_cantidades_picking(
    confirmacion: ConfirmacionPicking,
    usuario: User = Depends(get_current_user)
):
    orden = await Orden.get(confirmacion.pedidoId)
    if not orden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
        
    if orden.estado != "Pagado":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El pedido no está en estado 'Pagado'")

    es_parcial = False
    for item_confirmado in confirmacion.itemsConfirmados:
        for item_original in orden.items:
            if item_original.variante_sku == item_confirmado.sku:
                if item_original.cantidad > item_confirmado.cantidadEncontrada:
                    es_parcial = True
                    break
        if es_parcial:
            break
    
    if es_parcial:
        nuevo_estado = "Listo para despacho (Parcial)"
        print(f"Pedido {orden.numeroOrden} preparado con FALTANTES. Notificando a admin.")
        mensaje = f"Pedido {orden.numeroOrden} preparado con FALTANTES. Notificado al administrador."
    else:
        nuevo_estado = "Listo para despacho"
        print(f"Pedido {orden.numeroOrden} preparado completo.")
        mensaje = f"Pedido {orden.numeroOrden} listo para despacho."
    
    await orden.update({"$set": {"estado": nuevo_estado}})

    return {
        "mensaje": mensaje,
        "nuevo_estado": nuevo_estado
    }

@router.get("/picking/{pedido_id}/imprimir-hoja", response_model=DocumentoImpresion) 
async def imprimir_hoja_picking(
    pedido_id: str,
    usuario: User = Depends(get_current_user)
):
    orden = await Orden.get(pedido_id)
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    
    url_pdf = f"/static/picking/hoja_{orden.numeroOrden}.pdf"
    print(f"Generando hoja de picking {url_pdf}")
    return DocumentoImpresion(
        url_pdf=url_pdf,
        mensaje="Hoja de picking generada correctamente."
    )