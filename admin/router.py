# admin/router.py
from datetime import date
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
from auth.schemas import User
from .schemas import ReglasCarrito, Cupon, CuponCreate, CuponOut, SecuritySettings, AuditLog, UserUpdateAdmin
from beanie import BeanieObjectId

router = APIRouter(
    prefix="/api/admin",
    tags=["4. Administración (Reglas y Cupones)"]
)

# === Endpoints para Reglas del Carrito ===

@router.get("/carrito/reglas", response_model=ReglasCarrito)
async def obtener_reglas_carrito():
    reglas = await ReglasCarrito.find_one()
    if not reglas:
        reglas = ReglasCarrito()
        await reglas.insert()
    return reglas

@router.put("/carrito/reglas", response_model=ReglasCarrito)
async def actualizar_reglas_carrito(reglas_data: ReglasCarrito):
    reglas = await ReglasCarrito.find_one()
    if not reglas:
        reglas = ReglasCarrito(**reglas_data.model_dump())
        await reglas.insert()
    else:
        await reglas.update({"$set": reglas_data.model_dump(exclude_unset=True)})
    
    return reglas

# === Endpoints para Gestión de Cupones ===

@router.post("/cupones", response_model=CuponOut, status_code=status.HTTP_201_CREATED)
async def crear_cupon(cupon_data: CuponCreate):
    codigo_existente = await Cupon.find_one(Cupon.codigo == cupon_data.codigo)
    if codigo_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El código de cupón '{cupon_data.codigo}' ya existe"
        )
            
    nuevo_cupon = Cupon(**cupon_data.model_dump())
    await nuevo_cupon.insert()
    return CuponOut.model_validate(nuevo_cupon)

@router.get("/cupones", response_model=List[CuponOut])
async def obtener_cupones():
    cupones = await Cupon.find_all().to_list()
    return cupones

@router.put("/cupones/{cupon_id}", response_model=CuponOut)
async def actualizar_cupon(cupon_id: BeanieObjectId, cupon_data: CuponCreate):
    cupon = await Cupon.get(cupon_id)
    if not cupon:
        raise HTTPException(
            status_code=status.HTTP_44_NOT_FOUND,
            detail="Cupón no encontrado"
        )
    
    await cupon.update({"$set": cupon_data.model_dump(exclude_unset=True)})
    cupon_actualizado = await Cupon.get(cupon_id)
    return cupon_actualizado

@router.get("/cupones/validar/{codigo}")
async def validar_cupon_publico(codigo: str):
    # 1. Buscar cupón activo por código
    cupon = await Cupon.find_one(
        Cupon.codigo == codigo, 
        Cupon.estado == "Activo"
    )
    
    if not cupon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cupón no válido o no existe")
    
    # 2. Validar Fechas
    hoy = date.today()
    if cupon.vigenciaDesde and cupon.vigenciaDesde > hoy:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El cupón aún no está vigente")
        
    if cupon.vigenciaHasta and cupon.vigenciaHasta < hoy:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El cupón ha expirado")

    # 3. Retornar datos para que el front calcule
    return {
        "codigo": cupon.codigo,
        "tipo": cupon.tipo, 
        "valor": cupon.valor,
        "pedidoMinimo": cupon.pedidoMinimo
    }

@router.delete("/cupones/{cupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_cupon(cupon_id: BeanieObjectId):
    cupon = await Cupon.get(cupon_id)
    if not cupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cupón no encontrado"
        )
    
    await cupon.delete()
    return

# ==========================================
# === GESTIÓN DE USUARIOS ===
# ==========================================

@router.get("/users", response_model=List[User])
async def listar_usuarios():
    users = await User.find_all().to_list()
    return users

@router.put("/users/{user_id}")
async def actualizar_usuario_admin(user_id: BeanieObjectId, data: UserUpdateAdmin):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    
    await user.update({"$set": data.model_dump(exclude_unset=True)})
    return await User.get(user_id)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(user_id: BeanieObjectId):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    await user.delete()
    return

# ==========================================
# === SEGURIDAD Y AUDITORÍA ===
# ==========================================

@router.get("/security/settings", response_model=SecuritySettings)
async def obtener_config_seguridad():
    settings = await SecuritySettings.find_one()
    if not settings:
        settings = SecuritySettings()
        await settings.insert()
    return settings

@router.put("/security/settings", response_model=SecuritySettings)
async def actualizar_config_seguridad(settings_data: SecuritySettings):
    settings = await SecuritySettings.find_one()
    if not settings:
        settings = SecuritySettings(**settings_data.model_dump())
        await settings.insert()
    else:
        await settings.update({"$set": settings_data.model_dump(exclude={"id", "_id"})})
        settings = await SecuritySettings.find_one()
    return settings

@router.get("/security/audit-logs", response_model=List[AuditLog])
async def obtener_auditoria():
    logs = await AuditLog.find_all().sort("-fecha").limit(50).to_list()
    return logs

@router.post("/security/audit-logs")
async def crear_log_auditoria(log: AuditLog):
    await log.insert()
    return {"mensaje": "Log registrado"}