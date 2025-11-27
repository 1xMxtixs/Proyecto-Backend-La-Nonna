# auth/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from beanie import Document
import bcrypt
from enum import Enum

class Roles(str, Enum):
    CLIENTE = "cliente"
    ADMIN = "administrador"
    DUENO = "dueño"
    LOGISTICA = "logistica"

# --- Modelo Base para Usuario ---
class User(Document):
    email: EmailStr
    nombre: str
    hashed_password : str = Field(..., alias="hashedPassword")
    rol: Roles = Roles.CLIENTE
    telefono: Optional[str] = None
    verification_code: Optional[str] = None
    foto_url: Optional[str] = None
    direccion: Optional[str] = None

    class Settings:
        name = "usuarios"

    # --- Metodo de ayuda ---
    def check_password(self, clear_password: str) -> bool:
        """Verifica la contraseña ingresada contra la hasheada"""
        return bcrypt.hashpw(
            clear_password.encode('utf-8'), 
            self.hashed_password.encode('utf-8')
        ) == self.hashed_password.encode('utf-8')

# --- Modelo para autenticación ---
class TokenRequest(BaseModel):
    email: EmailStr
    contrasena: str

class UserBase(BaseModel):
    email: EmailStr
    nombre: str
    rol: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str 
    usuario: UserBase

class Perfil(BaseModel):
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None

# --- Modelo para gestion de equipo ---
class InvitarMiembroRequest(BaseModel):
    email: EmailStr
    rol: str  

class RevocarAccesoRequest(BaseModel):
    email: EmailStr
    
class TokenData(BaseModel):
    email: Optional[str] = None
    rol: Optional[str] = None

class UserCreate(BaseModel):
    nombre: str
    email: EmailStr
    contrasena: str

# --- Función de Ayuda para Hashear ---
def hash_password(password: str) -> str:
    """Hashea una contraseña en texto plano usando bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# --- Recuperación de Contraseña  ---
class PasswordRecoveryRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class TwoFARequest(BaseModel):
    telefono: str

class TwoFAVerify(BaseModel):
    telefono: str
    codigo: str    