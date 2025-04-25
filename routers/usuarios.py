import bcrypt 
import joblib
import pandas as pd
from models import *
from db import sesion
from sqlmodel import select
from limpiar import limpiar_datos
from fastapi import APIRouter, HTTPException, status
from scraper_paralelismo import scrapear_todas_las_tiendas
from perfil_de_usuarios import obtener_categoria_meta, generar_embedding

router = APIRouter(prefix="/users",tags=["users"])

def hash_contraseña(contraseña: str) -> str:
    """ Hash de contraseña de usuario"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(contraseña.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_contraseña(plain_contraseña: str, hashed_contraseña: str)-> bool:
    """ Verifica la contraseña del usuario """
    return bcrypt.checkpw(plain_contraseña.encode("utf-8"), hashed_contraseña.encode("utf-8"))

def verificar_usuario(session:sesion, nombre: str, contraseña: str):
    # Buscar el usuario por nombre
    statement = select(User).where(User.nombre == nombre)
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    if not verify_contraseña(contraseña, result.contraseña):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")
    return result  # Puedes retornar el usuario completo

def preparar_datos(data):
    # cargamos el modelo
    modelo = joblib.load("modelo_random_forest.pkl")
    
    # Limpiamos los datos
    df = limpiar_datos(pd.DataFrame(data))
    
    # Datos que usara el modelo
    x = df[["Precio", "Puntuacion", "PC", "PPW", "PS"]].values
    
    # Predicción
    df["IR"] = modelo.predict(x)  
    
    # Escalado final
    df["IR"] = (df["IR"] - df["IR"].min()) / (df["IR"].max() - df["IR"].min()) * 100
    
    # Guardar y mostrar resultados
    top_30 = df.nlargest(30, "IR")
    
    return top_30

@router.post("/registro",response_model=ReadUser, status_code=status.HTTP_201_CREATED)
async def create_user(user: CreateUser, session:sesion):
    """ Crea un nuevo usuario """
    user = User(**user.model_dump())
    user.contraseña = hash_contraseña(user.contraseña)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.post("/login",status_code=status.HTTP_200_OK)
async def login(user:Login,session:sesion):
    """ Funcion para verificar el usuario """
    user = verificar_usuario(session,user.nombre,user.contraseña)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return {"mensaje": f"Bienvenido {user.nombre}"}


@router.post("/buscar")
async def buscar(producto: str, id: str, session: sesion):
    # 1. Realizamos el scrapeo
    datos = scrapear_todas_las_tiendas(producto)
    if not datos:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # 2. Buscar usuario
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 3. Actualizamos el historial de búsqueda
    if user.productos_buscados is None:
        user.productos_buscados = []
    user.productos_buscados.append(producto)

    # 4. Actualizamos conteo de categorías
    if user.categorias_visitadas_raw is None:
        user.categorias_visitadas_raw = {}
    
    # Obtener la categoría del producto
    categoria = obtener_categoria_meta(producto)

    # Verificar que la categoría se acumule correctamente
    if categoria in user.categorias_visitadas_raw:
        user.categorias_visitadas_raw[categoria] += 1
    else:
        user.categorias_visitadas_raw[categoria] = 1

    # Imprimir las categorías visitadas antes de guardar
    print(f"Categorías visitadas antes de commit: {user.categorias_visitadas_raw}")

    # 5. Recalculamos el embedding (este paso solo actualiza el embedding)
    embedding = generar_embedding(list(user.categorias_visitadas_raw.keys()))
    user.categorias_embedding = embedding

    # Imprimir el embedding antes de guardar
    print(f"Embedding calculado antes de commit: {user.categorias_embedding}")

    # 6. Guardamos cambios en la base de datos
    session.add(user)
    session.commit()
    session.refresh(user)

    # Verificar las categorías y el embedding después de guardar
    print(f"Categorías después de commit: {user.categorias_visitadas_raw}")
    print(f"Embedding después de commit: {user.categorias_embedding}")

    # 7. Procesamos los datos scrapeados
    productos_filtrados = preparar_datos(datos)

    return {
        "mensaje": "Perfil actualizado correctamente",
        "categorias_visitadas_raw": user.categorias_visitadas_raw,
        "categorias_embedding": user.categorias_embedding,
        "top_productos": productos_filtrados.to_dict(orient="records")
    }
