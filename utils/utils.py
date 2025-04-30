import os
import bcrypt 
import joblib
import pyshorteners
import pandas as pd
from db import sesion
from models import User
from sqlmodel import select
from dotenv import load_dotenv
from limpiar import limpiar_datos
from datetime import datetime, timedelta,timezone
from fastapi import HTTPException, status, Request
from jose import jwt, JWTError

load_dotenv()

Secret_key = os.getenv("SECRET_KEY")
Algortihm = "HS256" 
Expire_delta = 3600  


# ___________________________ Funciones de manejo de datos _____________________________
# Creamos el objeto Shortener
s = pyshorteners.Shortener()

def _shorten_url(url) -> str:
    """ Acorta la URL usando la API de TinyURL """
    try:
        return s.tinyurl.short(url)
    except Exception as e:
        # Si la API falla, retornamos la URL original
        return url

def preparar_datos(data)-> pd.DataFrame:
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

# ___________________________ Manejo de usuarios _____________________________
def hash_contraseña(contraseña: str) -> str:
    """ Hash de contraseña de usuario"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(contraseña.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_contraseña(plain_contraseña: str, hashed_contraseña: str)-> bool:
    """ Verifica la contraseña del usuario """
    return bcrypt.checkpw(plain_contraseña.encode("utf-8"), hashed_contraseña.encode("utf-8"))

def verificar_usuario(session:sesion, nombre: str, contraseña: str) -> User:
    """ Verifica si el usuario existe y la contraseña es correcta """
    # Buscar el usuario por nombre
    statement = select(User).where(User.nombre == nombre)
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    if not verify_contraseña(contraseña, result.contraseña):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")
    return result 


# ___________________________ Manejo de JWT _____________________________

def create_jwt_token(data: dict, secret_key: str , algorithm: str,expires_delta: int ) -> str: 
    """ Crea un token JWT """
    to_encode = data.copy()
    if expires_delta:
        to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(seconds=expires_delta)})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

def decode_jwt_token(token:str, secret_key: str, algorithm: str) -> dict:
    """ Decodifica un token JWT """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

# Validar el token JWT
async def get_current_user(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Intentar obtener el token de la cookie
    token = request.cookies.get("access_token")

    if not token:
        # Si no hay token en la cookie, intentar obtenerlo del encabezado de autorización
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, Secret_key, algorithms=[Algortihm])
        nombre: str = payload.get("sub")
        id: str = payload.get("id")
        if nombre is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return {"sub": nombre, "id": id}

def format_colombian_peso_manual(value):
    '''Funcion para formatear el precio en pesos colombianos'''
    try:
        num_int = int(float(value))
        s = str(num_int)
        n = len(s)
        res = ""
        for i in range(n):
            res += s[i]
            if (n - 1 - i) % 3 == 0 and i != n - 1:
                res += "."
        return f"{res}"
    except (ValueError, TypeError):
        #print(f"Advertencia: No se pudo formatear el valor '{value}' como moneda.")
        return value