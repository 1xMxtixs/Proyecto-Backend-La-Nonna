# checkout/router.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import random
import datetime

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.error.transbank_error import TransbankError
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

from .schemas import (
    WebpayInitResponse, WebpayCommitRequest, IniciarPagoRequest,
    Orden, OrdenOut, Boleta
)
from auth.schemas import User
from auth.router import get_current_user
from admin.schemas import ReglasCarrito

router = APIRouter(prefix="/api/checkout", tags=["3. Carrito y Checkout"])

URL_RETORNO = "http://localhost:4321/PagoExito"

# --- Función Helper para Configurar Transbank ---
def get_transaction():
    """
    Crea una instancia de Transaction con las credenciales de prueba.
    """
    options = WebpayOptions(
        commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
        api_key=IntegrationApiKeys.WEBPAY,
        integration_type="TEST"
    )
    return Transaction(options)


# 1. INICIAR PAGO (Crear transacción en Webpay)
@router.post("/iniciar-pago", response_model=WebpayInitResponse)
async def iniciar_pago_webpay(
    datos: IniciarPagoRequest,
    usuario: User = Depends(get_current_user)
):
    reglas = await ReglasCarrito.find_one()
    if reglas:
        total_cantidad = sum(item.cantidad for item in datos.items)
        
        if total_cantidad < reglas.cantidadMinimaGlobal:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, 
                f"El pedido mínimo es de {reglas.cantidadMinimaGlobal} productos."
            )

    if not datos.items or datos.total <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Datos de compra inválidos")

    buy_order = f"LN-{int(datetime.datetime.now().timestamp())}"
    session_id = str(random.randint(100000, 999999))
    
    nueva_orden = Orden(
        propietario=usuario,
        numeroOrden=buy_order,
        estado="Pendiente",
        items=datos.items,
        total=datos.total,
        datos_entrega=datos.datos_entrega
    )
    await nueva_orden.insert()

    tx = get_transaction() 
    
    try:
        response = tx.create(buy_order, session_id, datos.total, URL_RETORNO)
    except TransbankError as e:
        print(f"Error Transbank: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "No se pudo conectar con Transbank")

    nueva_orden.token_ws = response['token']
    await nueva_orden.save()

    return WebpayInitResponse(
        url=response['url'],
        token=response['token'],
        orden_id=buy_order
    )

# 2. CONFIRMAR PAGO (Cuando vuelve de Webpay)
@router.post("/confirmar-pago", response_model=OrdenOut)
async def confirmar_pago_webpay(
    datos: WebpayCommitRequest
):
    token = datos.token_ws
    
    orden = await Orden.find_one(Orden.token_ws == token)
    if not orden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orden no encontrada para este token")
        
    if orden.estado == "Pagado":
        return orden 

    tx = get_transaction()
    
    try:
        response = tx.commit(token)
    except TransbankError as e:
        orden.estado = "Fallido"
        await orden.save()
        print(f"Error confirmando: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Error al confirmar transacción con el banco")

    if response.get('status') == 'AUTHORIZED' and response.get('response_code') == 0:
        orden.estado = "Pagado"
        await orden.save()
        
        numero_boleta = f"B-{orden.numeroOrden}"
        nueva_boleta = Boleta(
            orden=orden,
            boletaId=numero_boleta,
            monto=orden.total,
            url_pdf=f"/static/boletas/{numero_boleta}.pdf"
        )
        await nueva_boleta.insert()
        
        return orden
    else:
        orden.estado = "Rechazado"
        await orden.save()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El pago fue rechazado o anulado")