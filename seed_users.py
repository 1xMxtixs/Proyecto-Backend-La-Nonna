import asyncio
import bcrypt
from db import init_db
from auth.schemas import User, Roles  

USUARIOS_PARA_CREAR = [
    {
        "email": "dueno@nonna.cl",
        "nombre": "Dueño Nonna",
        "rol": Roles.DUENO,
        "pass": "dueno123"  
    },
    {
        "email": "admin@nonna.cl",
        "nombre": "Admin Nonna",
        "rol": Roles.ADMIN,
        "pass": "admin123"
    },
    {
        "email": "logistica@nonna.cl",
        "nombre": "Encargado Logística",
        "rol": Roles.LOGISTICA,
        "pass": "logistica123"
    },
    {
        "email": "cliente@nonna.cl",
        "nombre": "Cliente Ejemplo",
        "rol": Roles.CLIENTE,
        "pass": "cliente123"
    }
]

async def poblar_base_de_datos():
    await init_db()
    
    print("Iniciando el sembrado (seeding) de usuarios...")
    
    for data_usuario in USUARIOS_PARA_CREAR:
        
        bytes_pass = data_usuario["pass"].encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_pass = bcrypt.hashpw(bytes_pass, salt).decode('utf-8')
        
        usuario_existente = await User.find_one(User.email == data_usuario["email"])
        
        if usuario_existente:
            print(f"Actualizando usuario: {data_usuario['email']}")
            await usuario_existente.update({"$set": {
                "hashedPassword": hashed_pass,
                "rol": data_usuario["rol"],
                "nombre": data_usuario["nombre"]
            }})
        else:
            print(f"Creando usuario: {data_usuario['email']}")
            nuevo_usuario = User(
                email=data_usuario["email"],
                nombre=data_usuario["nombre"],
                hashed_password=hashed_pass,
                rol=data_usuario["rol"]
            )
            await nuevo_usuario.insert()
            
    print("¡Sembrado de usuarios completado!")

if __name__ == "__main__":
    asyncio.run(poblar_base_de_datos())