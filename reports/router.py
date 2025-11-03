# reports/router.py
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Dict, Any, Optional
from .schemas import (
    AdminKPIResponse, OwnerSummaryResponse, LogisticsKPIResponse,
    VentaReporteItem, AuditEvent, Boleta,
    TopProducto, KpiConVariacion, TopProductoMargen,
    KpiTiempo, MotivoCancelacion
)
from datetime import datetime, date, timedelta
from auth.schemas import User
from checkout.schemas import Orden, Boleta
from catalog.schemas import Producto
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

    query = Orden.find(
        Orden.fecha >= start_datetime,
        Orden.fecha <= end_datetime,
        Orden.estado == "Pagado" 
    )
    
    ordenes = await query.to_list()
    
    ventas_totales = sum(o.total for o in ordenes)
    numero_pedidos = len(ordenes)
    ticket_promedio = ventas_totales / numero_pedidos if numero_pedidos > 0 else 0
    
    top_productos_simulado = [
        TopProducto(nombre="Rigatoni 500g (Real)", cantidad=150, monto=559000.0),
        TopProducto(nombre="Lasagna Clásica (Real)", cantidad=90, monto=320000.0)
    ]

    return AdminKPIResponse(
        ventasTotales=ventas_totales,
        numeroPedidos=numero_pedidos,
        ticketPromedio=ticket_promedio,
        topProductos=top_productos_simulado
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
                    cliente=str(orden.propietario.id), 
                    item=item.nombreProducto,
                    cantidad=item.cantidad,
                    precio=item.precioUnitario,
                    total=item.subtotal,
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
        Boleta.fechaEmision <= end_datetime
    ).to_list()
    
    return boletas

# === Endpoints de Reportes (DUEÑO) ===

@router.get("/dueño/resumen-ejecutivo", response_model=OwnerSummaryResponse, tags=["7. Reportes (Dueño)"])
async def get_resumen_ejecutivo(
    fechaInicio: date, 
    fechaFin: date,
    usuario: User = Depends(get_current_user)
):

    return OwnerSummaryResponse(
        ventasTotales=KpiConVariacion(valor=2450000, variacion=0.08),
        margenEstimado=KpiConVariacion(valor=950000, variacion=0.05),
        numeroPedidos=KpiConVariacion(valor=320, variacion=-0.01),
        ticketPromedio=KpiConVariacion(valor=7656, variacion=0.02),
        topPlatos=[
            TopProductoMargen(nombre="Rigatoni 500g", monto=350000, margenEstimado=0.35)
        ]
    )

@router.get("/dueño/reporte-logistica", response_model=LogisticsKPIResponse, tags=["7. Reportes (Dueño)"])
async def get_reporte_logistica(
    fecha: date, 
    franjaHoraria: Optional[str] = None,
    usuario: User = Depends(get_current_user)
):

    return LogisticsKPIResponse(
        tiempoMedioPreparacion=KpiTiempo(minutos=18, alertaSLA=True),
        tiempoMedioEnRuta=KpiTiempo(minutos=42, alertaSLA=False),
        otdPorcentaje=0.86,
        cancelaciones=[
            MotivoCancelacion(motivo="Sin stock", cantidad=2)
        ]
    )

@router.get("/dueño/reporte-auditoria", response_model=List[AuditEvent], tags=["7. Reportes (Dueño)"])
async def get_reporte_auditoria(
    fechaInicio: date, 
    fechaFin: date,
    usuario: Optional[str] = None,
    authUser: User = Depends(get_current_user)
):

    evento_ejemplo = AuditEvent(
        id="audit_1",
        fecha=datetime.now(),
        usuario="admin@nonna.cl",
        tipoEvento="login",
        descripcion="Inicio de sesión exitoso"
    )
    return [evento_ejemplo]