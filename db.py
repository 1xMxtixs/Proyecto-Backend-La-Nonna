# db.py

from beanie import init_beanie
import motor.motor_asyncio
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Type

# --- Imports de Modelos ---
from auth.schemas import User
from catalog.schemas import Categoria, Etiqueta, Producto, Vitrina
from cart.schemas import Carrito
from admin.schemas import ReglasCarrito, Cupon, SecuritySettings, AuditLog 
from checkout.schemas import Orden, Boleta

class Settings(BaseSettings):
    DATABASE_URL: str
    model_config = SettingsConfigDict(env_file=".env")
    SECRET_KEY: str
    ALGORITHM: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str

db_settings = Settings()

# --- Lista de Modelos ---
DOCUMENT_MODELS: List[Type] = [
    User, 
    Categoria,
    Etiqueta,
    Producto,
    Carrito,
    ReglasCarrito,
    Cupon,
    Orden,
    Boleta,
    SecuritySettings,
    AuditLog,
    Vitrina,
    
]

async def init_db():
    print("Conectando a MongoDB Atlas...")

    client = motor.motor_asyncio.AsyncIOMotorClient(
        db_settings.DATABASE_URL
    )

    await init_beanie(
        database=client.get_default_database(),
        document_models=DOCUMENT_MODELS
    )

    print("Conexión a MONGODB establecida.")