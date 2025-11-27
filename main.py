# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager
from db import init_db
from auth.router import router as auth_router
from catalog.router import router as catalog_router
from cart.router import router as cart_router
from admin.router import router as admin_router
from checkout.router import router as checkout_router
from logistics.router import router as logistics_router
from reports.router import router as reports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Servidor listo para recibir peticiones.")
    yield
    print("Servidor apagándose.")

app = FastAPI(
    title="La Nonna - API",
    description="API para el restaurante italiano La Nonna",
    version="1.0.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:4321",
    "http://127.0.0.1:4321",
]

os.makedirs("uploads", exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       
    allow_credentials=True,
    allow_methods=["*"],         
    allow_headers=["*"],
)
    

app.mount("/static", StaticFiles(directory="uploads"), name="static")
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(admin_router)
app.include_router(checkout_router)
app.include_router(logistics_router)
app.include_router(reports_router)

@app.get("/")
async def root():
    return {"message": "Bienvenido a la API de La Nonna"}

