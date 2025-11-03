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
    foto_url: Optional[str] = None

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
    telefono: Optional[str] = None    

# --- Modelo  para gestion de equipo ---
class InvitarMiembroRequest(BaseModel):
    email: EmailStr
    rol: str  

class RevocarAccesoRequest(BaseModel):
    email: EmailStr
    
class TokenData(BaseModel):
    email: Optional[str] = None
    rol: Optional[str] = None               