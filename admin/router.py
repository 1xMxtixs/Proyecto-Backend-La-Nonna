# admin/router.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
from .schemas import ReglasCarrito, Cupon, CuponCreate, CuponOut
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
    cupones = await Cupon.find_all().project(CuponOut).to_list()
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
    await cupon.reload()
    return CuponOut.model_validate(cupon)

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