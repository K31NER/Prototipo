import json
import bcrypt 
import joblib
import pyshorteners
import pandas as pd
from models import *
from db import sesion
from sqlmodel import select
from datetime import datetime
from urllib.parse import quote
from limpiar import limpiar_datos
from fastapi.responses import RedirectResponse,JSONResponse
from fastapi import APIRouter, HTTPException, status,Form , Response, Request
from scraper_paralelismo import scrapear_todas_las_tiendas
from perfil_de_usuarios import obtener_categoria_meta, generar_embedding
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/users",tags=["users"])
templates = Jinja2Templates(directory="templates")
# Creamos el objeto Shortener
s = pyshorteners.Shortener()

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

def _shorten_url(url):
    try:
        return s.tinyurl.short(url)
    except Exception as e:
        # Si la API falla, retornamos la URL original
        return url


def preparar_datos(data):
    """ Prepara los datos para el modelo """
    # Cargamos el modelo
    modelo = joblib.load("modelo_random_forest.pkl")

    # Limpiamos los datos
    df = limpiar_datos(pd.DataFrame(data))

    # Recortamos las URLs en la columna 'Links' con manejo de excepciones
    df["Links"] = df["Links"].apply(
        lambda x: _shorten_url(x) if isinstance(x, str) else x
    )

    # Datos que usará el modelo
    x = df[["Precio", "Puntuacion", "PC", "PPW", "PS"]].values

    # Predicción
    df["IR"] = modelo.predict(x)

    # Escalado final
    df["IR"] = (df["IR"] - df["IR"].min()) / (df["IR"].max() - df["IR"].min()) * 100

    # Guardar y mostrar resultados
    top = df.nlargest(10, "IR")

    return top


@router.post("/registro", response_model=ReadUser, status_code=status.HTTP_201_CREATED)
async def create_user(session: sesion,
                    nombre: str = Form(...),
                    correo: str = Form(...),
                    genero: str = Form(...),
                    fecha_nacimiento: str = Form(...),
                    contraseña: str = Form(...),):
    """ Crea un nuevo usuario """
    # Convertir fecha de string a objeto datetime
    fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
    
    # Creamos el usuario en base al modelo 
    new_user = User(
        nombre=nombre,
        correo=correo,
        genero=genero,
        fecha_nacimiento=fecha_nacimiento, 
        contraseña=hash_contraseña(contraseña),
    )
    
    # Agregamos el usuario
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # redireccionamos al usuario a la página de inicio
    return RedirectResponse(url=f"/inicio?user_name={new_user.nombre}&user_id={new_user.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(session: sesion, nombre: str = Form(...), contraseña: str = Form(...)):
    """Función para verificar el usuario"""
    # Verificar si el usuario existe y la contraseña es correcta
    try:
        user = verificar_usuario(session, nombre, contraseña)
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return JSONResponse(content={"error": "Credenciales inválidas"}, status_code=status.HTTP_401_UNAUTHORIZED)
        raise e
        
    # redireccionamos al usuario a la página de inicio
    return RedirectResponse(url=f"/inicio?user_name={user.nombre}&user_id={user.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/buscar")
async def buscar(
    request: Request,
    session: sesion,
    response: Response,
    producto: str = Form(...),
    id: str = Form(...)
):
    # 1. Realizamos el scrapeo
    datos = scrapear_todas_las_tiendas(producto)

    # Si no hay resultados, volvemos a la página de inicio con mensaje de error
    if not datos:
        # opcionalmente puedes recuperar el nombre de usuario para el saludo
        user = session.get(User, id)
        nombre = user.nombre if user else ""
        return templates.TemplateResponse(
            "inicio.html",
            {
                "request": request,
                "name": nombre.capitalize(),
                "user_id": id,
                "error": "No se encontraron productos, realice otra búsqueda"
            },
            status_code=200
        )

    # 2. Buscar usuario
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 3. Actualizamos el historial de búsqueda
    user.productos_buscados.append(producto)

    # 4. Actualizamos conteo de categorías
    if user.categorias_visitadas_raw is None:
        user.categorias_visitadas_raw = {}
    categoria = obtener_categoria_meta(producto)
    user.categorias_visitadas_raw[categoria] = (
        user.categorias_visitadas_raw.get(categoria, 0) + 1
    )

    # 5. Recalculamos el embedding
    embedding = generar_embedding(user.categorias_visitadas_raw)
    user.categorias_embedding = embedding

    # 6. Guardamos cambios en la base de datos
    session.add(user)
    session.commit()
    session.refresh(user)

    # 7. Procesamos los datos scrapeados
    productos_filtrados = preparar_datos(datos)

    # 8. Creamos lista y la guardamos en cookie
    productos_lista = [
        {
            "nombre": p["Nombre"],
            "precio": p["Precio"],
            "puntuacion": p["Puntuacion"],
            "links": p["Links"],
        }
        for p in productos_filtrados.to_dict(orient="records")
    ]
    productos_json = quote(json.dumps(productos_lista))

    # 9. Redirigimos al dashboard
    response = RedirectResponse(
        url=f"/dashboard?user_name={user.nombre}&user_id={user.id}",
        status_code=303
    )
    response.set_cookie("productos", productos_json, max_age=1800, httponly=True)
    response.set_cookie("user_name", user.nombre,   max_age=1800, httponly=True)
    return response