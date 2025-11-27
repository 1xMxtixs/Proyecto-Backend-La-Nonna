#reports/router.py

from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Dict, Any, Optional
from .schemas import (
    AdminKPIResponse, OwnerSummaryResponse, LogisticsKPIResponse,
    VentaReporteItem, AuditEvent, 
    TopProducto, KpiConVariacion, TopProductoMargen,
    KpiTiempo, MotivoCancelacion
)
from datetime import datetime, date, timedelta
from auth.schemas import User
from checkout.schemas import Orden, Boleta
from auth.router import get_current_user

router = APIRouter(
    prefix="/api",
)

# === Endpoints de Reportes (ADMINISTRADOR) ===


@router.get("/admin/dashboard-kpi", response_model=AdminKPIResponse, tags=["6. Reportes (Admin)"])
async def get_dashboard_kpi(
    fechaInicio: date,
    fechaFin: date,
    usuario: User = Depends(get_current_user)
):
    start_datetime = datetime.combine(fechaInicio, datetime.min.time())
    end_datetime = datetime.combine(fechaFin, datetime.max.time())

    estados_venta = ["Pagado", "En Preparación", "Enviado", "Entregado"]

    query = Orden.find(
        Orden.fecha >= start_datetime,
        Orden.fecha <= end_datetime,
        {"estado": {"$in": estados_venta}}
    )
    
    ordenes = await query.to_list()
    
    venta_productos_pura = 0 
    recaudacion_total_caja = 0
    
    for o in ordenes:
        recaudacion_total_caja += o.total
        for item in o.items:
            venta_productos_pura += (item.precio * item.cantidad)

    ingresos_delivery = recaudacion_total_caja - venta_productos_pura        
            
    numero_pedidos = len(ordenes)
    
    ticket_promedio = venta_productos_pura / numero_pedidos if numero_pedidos > 0 else 0
    
    pipeline = [
        {
            "$match": {
                "fecha": {"$gte": start_datetime, "$lte": end_datetime},
                "estado": {"$in": estados_venta}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.nombre",
                "cantidad": {"$sum": "$items.cantidad"},
                "monto": {"$sum": {"$multiply": ["$items.precio", "$items.cantidad"]}}
            }
        },
        {"$sort": {"monto": -1}},
        {"$limit": 5}
    ]

    resultados_top = await Orden.get_motor_collection().aggregate(pipeline).to_list(length=5)

    top_productos_real = [
        TopProducto(
            nombre=r["_id"], 
            cantidad=r["cantidad"], 
            monto=r["monto"]
        ) for r in resultados_top
    ]

    return AdminKPIResponse(
        ventasTotales=venta_productos_pura, 
        ingresosDelivery=ingresos_delivery,
        numeroPedidos=numero_pedidos,
        ticketPromedio=ticket_promedio,
        topProductos=top_productos_real
    )

@router.get("/admin/reporte-ventas", response_model=List[VentaReporteItem], tags=["6. Reportes (Admin)"])
async def get_reporte_ventas(
    fechaInicio: date,
    fechaFin: date,
    categoria: Optional[str] = None, 
    usuario: User = Depends(get_current_user)
):
    start_datetime = datetime.combine(fechaInicio, datetime.min.time())
    end_datetime = datetime.combine(fechaFin, datetime.max.time())

    ordenes = await Orden.find(
        Orden.fecha >= start_datetime,
        Orden.fecha <= end_datetime
    ).to_list()
    
    reporte_items = []
    for orden in ordenes:
        for item in orden.items:
            reporte_items.append(
                VentaReporteItem(
                    fecha=orden.fecha,
                    orden=orden.numeroOrden,
                    cliente=str(orden.propietario), 
                    item=item.nombre,
                    cantidad=item.cantidad,
                    precio=item.precio,
                    total=item.precio * item.cantidad,
                    estado=orden.estado
                )
            )
    return reporte_items

@router.get("/admin/reporte-boletas", response_model=List[Boleta], tags=["6. Reportes (Admin)"])
async def get_reporte_boletas(
    fechaInicio: date, 
    fechaFin: date,
    clienteEmail: Optional[str] = None, 
    usuario: User = Depends(get_current_user)
):
    start_datetime = datetime.combine(fechaInicio, datetime.min.time())
    end_datetime = datetime.combine(fechaFin, datetime.max.time())
    
    boletas = await Boleta.find(
        Boleta.fechaEmision >= start_datetime,
        Boleta.fechaEmision <= end_datetime,
        fetch_links=True
    ).to_list()
    
    if clienteEmail:
        clienteEmail = clienteEmail.lower()
        boletas_filtradas = []
        for b in boletas:
            if b.orden and b.orden.propietario:
                email_usuario = b.orden.propietario.email.lower()
                nombre_usuario = b.orden.propietario.nombre.lower()
                
                if clienteEmail in email_usuario or clienteEmail in nombre_usuario:
                    boletas_filtradas.append(b)
        return boletas_filtradas

    return boletas

@router.get("/dueño/resumen-ejecutivo", response_model=OwnerSummaryResponse, tags=["7. Reportes (Dueño)"])
async def get_resumen_ejecutivo(
    fechaInicio: date, 
    fechaFin: date,
    usuario: User = Depends(get_current_user)
):
    start = datetime.combine(fechaInicio, datetime.min.time())
    end = datetime.combine(fechaFin, datetime.max.time())
    estados_validos = ["Pagado", "En Preparación", "Enviado", "Entregado"]

    ordenes = await Orden.find({
        "fecha": {"$gte": start, "$lte": end},
        "estado": {"$in": estados_validos}
    }).to_list()

    venta_neta = 0
    for o in ordenes:
        if o.items:
            for item in o.items:
                venta_neta += (item.precio * item.cantidad)

    num_pedidos = len(ordenes)
    ticket_promedio = venta_neta / num_pedidos if num_pedidos > 0 else 0
    
    margen_estimado = venta_neta * 0.40

    pipeline = [
        {"$match": {"fecha": {"$gte": start, "$lte": end}, "estado": {"$in": estados_validos}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.nombre",
            "monto": {"$sum": {"$multiply": ["$items.precio", "$items.cantidad"]}}
        }},
        {"$sort": {"monto": -1}},
        {"$limit": 5}
    ]
    
    top_raw = await Orden.get_motor_collection().aggregate(pipeline).to_list(length=5)
    
    top_platos = [
        TopProductoMargen(
            nombre=r["_id"], 
            monto=r["monto"],
            margenEstimado=r["monto"] * 0.4
        ) for r in top_raw
    ]

    return OwnerSummaryResponse(
        ventasTotales=KpiConVariacion(valor=venta_neta, variacion=0),
        margenEstimado=KpiConVariacion(valor=margen_estimado, variacion=0),
        numeroPedidos=KpiConVariacion(valor=num_pedidos, variacion=0),
        ticketPromedio=KpiConVariacion(valor=ticket_promedio, variacion=0),
        topPlatos=top_platos
    )

@router.get("/dueño/reporte-logistica", response_model=LogisticsKPIResponse, tags=["7. Reportes (Dueño)"])
async def get_reporte_logistica(
    fecha: date, 
    franjaHoraria: Optional[str] = None,
    usuario: User = Depends(get_current_user)
):
    return LogisticsKPIResponse(
        tiempoMedioPreparacion=KpiTiempo(minutos=0, alertaSLA=False),
        tiempoMedioEnRuta=KpiTiempo(minutos=0, alertaSLA=False),
        otdPorcentaje=0.0,
        cancelaciones=[]
    )

@router.get("/dueño/reporte-auditoria", response_model=List[AuditEvent], tags=["7. Reportes (Dueño)"])
async def get_reporte_auditoria(
    fechaInicio: date, 
    fechaFin: date,
    usuario: Optional[str] = None,
    authUser: User = Depends(get_current_user)
):
    return []