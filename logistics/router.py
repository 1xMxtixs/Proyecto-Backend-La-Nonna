# logistics/router.py

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from typing import List, Dict
from .schemas import PedidoParaPicking, ConfirmacionPicking, PickingItem, DocumentoImpresion
from checkout.schemas import Orden, OrdenOut
from auth.schemas import User
from auth.router import get_current_user

router = APIRouter(prefix="/api/logistica", tags=["5. Logística y Despacho"])

# === 1. VISTA BODEGA: Pedidos Nuevos (Pagados) ===
@router.get("/pedidos-picking", response_model=List[PedidoParaPicking])
async def obtener_pedidos_picking(usuario: User = Depends(get_current_user)):
    ordenes = await Orden.find(
        {"estado": {"$in": ["Pagado", "En Preparación"]}}
    ).sort(+Orden.fecha).to_list()
    
    resultado = []
    for orden in ordenes:
        items_picking = [
            PickingItem(
                sku=getattr(i, 'producto_id', 'GEN'), 
                nombreProducto=i.nombre, 
                ubicacion="Pasillo A", 
                cantidadPedida=i.cantidad
            ) for i in orden.items
        ]
        resultado.append(PedidoParaPicking(
            id=str(orden.id), 
            numeroOrden=orden.numeroOrden, 
            fecha=orden.fecha, 
            items=items_picking
        ))
    return resultado

# === 2. VISTA DESPACHO: Pedidos Listos para Salir ===
@router.get("/pedidos-despacho", response_model=List[OrdenOut])
async def obtener_pedidos_despacho(usuario: User = Depends(get_current_user)):
    ordenes = await Orden.find(
        {"estado": {"$in": ["Listo para Despacho", "En Ruta"]}}
    ).sort(+Orden.fecha).to_list()
    return ordenes

# === 3. CAMBIO DE ESTADO GENÉRICO ===
@router.put("/pedidos/{orden_id}/estado")
async def cambiar_estado_orden(orden_id: str, nuevo_estado: str, usuario: User = Depends(get_current_user)):
    orden = await Orden.get(orden_id)
    if not orden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
    
    orden.estado = nuevo_estado
    await orden.save()
    return {"mensaje": f"Estado actualizado a {nuevo_estado}"}

# === 4. CONFIRMACIÓN DE PICKING (Bodega -> Despacho) ===
@router.post("/picking/confirmar")
async def confirmar_picking(confirmacion: ConfirmacionPicking, usuario: User = Depends(get_current_user)):
    orden = await Orden.get(confirmacion.pedidoId)
    if not orden: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
    
    orden.estado = "Listo para Despacho"
    await orden.save()
    return {"mensaje": "Picking finalizado. Orden lista para despacho."}

@router.get("/picking/{pedido_id}/imprimir-hoja", response_model=DocumentoImpresion) 
async def imprimir_hoja_picking(
    pedido_id: str,
    usuario: User = Depends(get_current_user)
):
    orden = await Orden.get(pedido_id)
    if not orden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    
    url_pdf = f"/static/picking/hoja_{orden.numeroOrden}.pdf"
    return DocumentoImpresion(
        url_pdf=url_pdf,
        mensaje="Hoja generada"
    )

# === Endpoint para KPIs del Dashboard ===
@router.get("/dashboard-kpis")
async def obtener_kpis_logistica(
    usuario: User = Depends(get_current_user)
):
    hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    en_ruta = await Orden.find(Orden.estado == "Enviado").count()
    
    entregados_hoy = await Orden.find(
        Orden.estado == "Entregado",
        Orden.fecha >= hoy_inicio
    ).count()
    
    alertas = await Orden.find(Orden.estado == "Fallido").count()
    
    pendientes = await Orden.find(Orden.estado == "Pagado").count()

    return {
        "en_ruta": en_ruta,
        "entregados_hoy": entregados_hoy,
        "alertas": alertas,
        "pendientes": pendientes
    }