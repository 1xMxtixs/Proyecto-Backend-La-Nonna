# auth/router.py

# ---
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .schemas import (
    User, UserCreate, TokenRequest, TokenResponse, Perfil, UserBase,
    InvitarMiembroRequest, TokenData,
    hash_password, Roles, PasswordRecoveryRequest, PasswordResetConfirm, TwoFARequest, TwoFAVerify
)
from admin.schemas import AuditLog, SecuritySettings
from jose import jwt, JWTError
from typing import Dict, Any, Optional
from beanie import BeanieObjectId
from db import db_settings
from datetime import datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import random

# ---


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

RESET_TOKEN_EXPIRE_MINUTES = 15

conf = ConnectionConfig(
    MAIL_USERNAME = db_settings.MAIL_USERNAME,
    MAIL_PASSWORD = db_settings.MAIL_PASSWORD,
    MAIL_FROM = db_settings.MAIL_FROM,
    MAIL_PORT = db_settings.MAIL_PORT,
    MAIL_SERVER = db_settings.MAIL_SERVER,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

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
    request: Request, 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # Obtenemos la IP del cliente
    client_ip = request.client.host

    usuario = await User.find_one(User.email == form_data.username)

    if not usuario or not usuario.check_password(form_data.password):
        # --- REGISTRAR EL INTENTO FALLIDO ---
        await AuditLog(
            usuario=form_data.username,
            accion="Intento de Login",
            ip=client_ip,
            estado="Fallo"
        ).insert()
        # ------------------------------------
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas" 
        )

    token_data = {"sub": usuario.email, "rol": str(usuario.rol.value)}
    access_token = create_access_token(token_data)

    # --- REGISTRAR EL ÉXITO ---
    await AuditLog(
        usuario=usuario.email,
        accion="Inicio de Sesión",
        ip=client_ip,
        estado="Exito"
    ).insert()
    # --------------------------

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
        email=current_user.email,
        telefono=current_user.telefono,
        direccion=current_user.direccion
    )

@router.put("/perfil", response_model=Perfil)
async def update_perfil(
    perfil_data: Perfil, 
    current_user: User = Depends(get_current_user)
):
    update_data = {
        "nombre": perfil_data.nombre,
        "telefono": perfil_data.telefono,
        "direccion": perfil_data.direccion
    }

    await current_user.update({"$set": perfil_data.model_dump()})
    print(f"Perfil de {current_user.email} actualizado.")
    return Perfil(
        nombre=perfil_data.nombre,
        email=current_user.email, 
        telefono=perfil_data.telefono,
        direccion=perfil_data.direccion
    )

# --- Endpoints de Gestión de Equipo ---

@router.post("/gestion-equipo/invitar")
async def invitar_miembro(
    invitacion: InvitarMiembroRequest,
    current_user: User = Depends(get_current_user) 
):
    print(f"Invitando a {invitacion.email} con el rol {invitacion.rol}")
    return {"mensaje": f"Invitación enviada a {invitacion.email}"}

# --- Endpoints de Resgistro ---

@router.post("/auth/registro", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def registro_usuario(
    request: Request,
    user_data: UserCreate
):

    settings = await SecuritySettings.find_one()

    if settings and settings.requerirMinimoCaracteres:
        if len(user_data.contrasena) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 8 caracteres por política de seguridad."
            )
    
    usuario_existente = await User.find_one(User.email == user_data.email)
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="El correo electrónico ya está registrado"
        )
        
    hashed_password = hash_password(user_data.contrasena)
    
    nuevo_usuario = User(
        nombre=user_data.nombre,
        email=user_data.email,
        hashedPassword=hashed_password, 
        rol=Roles.CLIENTE 
    )
    
    await nuevo_usuario.insert()

    client_ip = request.client.host
    await AuditLog(
        usuario=nuevo_usuario.email,
        accion="Resgistro de Nuevo Usuario",
        ip=client_ip,
        estado="Exito"
    ).insert()
    
    return UserBase(
        email=nuevo_usuario.email,
        nombre=nuevo_usuario.nombre,
        rol=str(nuevo_usuario.rol.value)
    )

@router.post("/auth/password-recovery")
async def solicitar_recuperacion(request: PasswordRecoveryRequest):
    user = await User.find_one(User.email == request.email)
    
    if not user:
        return {"mensaje": "Si el correo existe, se ha enviado un enlace."}

    expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": user.email, "type": "recovery", "exp": expires}
    reset_token = jwt.encode(to_encode, db_settings.SECRET_KEY, algorithm=db_settings.ALGORITHM)

    link = f"http://localhost:4321/ResetPassword?token={reset_token}"

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #6E0F2C; text-align: center;">Restablecer Contraseña</h2>
                <p>Hola <strong>{user.nombre}</strong>,</p>
                <p>Hemos recibido una solicitud para cambiar tu contraseña en <strong>La Nonna</strong>.</p>
                <p>Haz clic en el siguiente botón para crear una nueva clave:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link}" style="background-color: #6E0F2C; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Cambiar mi Contraseña
                    </a>
                </div>
                
                <p style="font-size: 12px; color: #777;">Este enlace expirará en 15 minutos.</p>
                <p style="font-size: 12px; color: #777;">Si no solicitaste esto, puedes ignorar este correo.</p>
            </div>
        </body>
    </html>
    """

    message = MessageSchema(
        subject="Recuperación de Contraseña - La Nonna",
        recipients=[request.email],  
        body=html_content,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)

    return {"mensaje": "Correo enviado con éxito"}

@router.post("/auth/reset-password")
async def ejecutar_reset_password(data: PasswordResetConfirm):
    try:
        payload = jwt.decode(data.token, db_settings.SECRET_KEY, algorithms=[db_settings.ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "recovery":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido")
            
    except JWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El enlace ha expirado o es inválido")

    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    nuevo_hash = hash_password(data.new_password)
    user.hashed_password = nuevo_hash
    await user.save()

    return {"mensaje": "Contraseña actualizada correctamente. Ahora puedes iniciar sesión."}


@router.post("/auth/2fa/request")
async def solicitar_2fa(data: TwoFARequest):
    print(f"🔍 Buscando usuario con teléfono: '{data.telefono}'") 

    user = await User.find_one(User.telefono == data.telefono)
    
    if not user:
        print("❌ USUARIO NO ENCONTRADO. Revisa la base de datos.") 
        return {"mensaje": "Si el número existe, se envió el código."}

    codigo = str(random.randint(1000, 9999))
    
    user.verification_code = codigo
    await user.save()

    print(f"\n========================================")
    print(f"📱 [SIMULACIÓN SMS] Para: {data.telefono}")
    print(f"🔑 Código de Seguridad: {codigo}")
    print(f"========================================\n")

    return {"mensaje": "Código enviado."}

@router.post("/auth/2fa/verify")
async def verificar_2fa(data: TwoFAVerify):
    user = await User.find_one(User.telefono == data.telefono)
    
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    if user.verification_code != data.codigo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código incorrecto")

    user.verification_code = None
    await user.save()

    return {"mensaje": "Autenticación exitosa. 2FA Activado."}