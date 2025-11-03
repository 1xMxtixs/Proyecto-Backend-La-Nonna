# auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .schemas import (
    User, TokenRequest, TokenResponse, Perfil, UserBase,
    InvitarMiembroRequest, TokenData
)
from jose import jwt, JWTError
from typing import Dict, Any, Optional
from beanie import BeanieObjectId
from db import db_settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(
    prefix="/api",
    tags=["1. Autenticación y Usuarios"]
)

# --- Función de Ayuda para crear Tokens ---
def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    encoded_jwt = jwt.encode(
        to_encode, db_settings.SECRET_KEY, algorithm=db_settings.ALGORITHM
    )
    return encoded_jwt
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Decodifica el token JWT, valida al usuario y lo devuelve.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, db_settings.SECRET_KEY, algorithms=[db_settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        rol: str = payload.get("rol")
        
        if email is None:
            raise credentials_exception
        
        token_data = TokenData(email=email, rol=rol)
        
    except JWTError:
        raise credentials_exception

    usuario = await User.find_one(User.email == token_data.email)
    
    if usuario is None:
        raise credentials_exception
        
    return usuario


# --- Endpoint de Login ---
@router.post("/auth/login", response_model=TokenResponse)
async def login(
    # (CORREGIDO) Ya no usamos TokenRequest, usamos el formulario estándar
    form_data: OAuth2PasswordRequestForm = Depends()
):
    
    usuario = await User.find_one(User.email == form_data.username)

    if not usuario or not usuario.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas" 
        )

    token_data = {"sub": usuario.email, "rol": str(usuario.rol.value)}
    access_token = create_access_token(token_data)

    # 4. Devuelve la respuesta exitosa
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        usuario=UserBase(
            email=usuario.email, 
            nombre=usuario.nombre, 
            rol=str(usuario.rol.value)
        )
    )

# --- Endpoints de Perfil ---

@router.get("/perfil", response_model=Perfil)
async def get_perfil(current_user: User = Depends(get_current_user)):
    return Perfil(
        nombre=current_user.nombre,
        telefono=current_user.telefono
    )

@router.put("/perfil", response_model=Perfil)
async def update_perfil(
    perfil_data: Perfil, 
    current_user: User = Depends(get_current_user)
):
    await current_user.update({"$set": perfil_data.model_dump()})
    print(f"Perfil de {current_user.email} actualizado.")
    return perfil_data

# --- Endpoints de Gestión de Equipo ---

@router.post("/gestion-equipo/invitar")
async def invitar_miembro(
    invitacion: InvitarMiembroRequest,
    current_user: User = Depends(get_current_user) # Protegido
):
    print(f"Invitando a {invitacion.email} con el rol {invitacion.rol}")
    return {"mensaje": f"Invitación enviada a {invitacion.email}"}