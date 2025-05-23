from contextlib import asynccontextmanager
import os
import secrets
import string
import httpx
import bcrypt 
import joblib
import pandas as pd
from db import sesion, engine
from models import User
from sqlmodel import SQLModel, select
from dotenv import load_dotenv
from limpiar import limpiar_datos
from models import Email
from jose import jwt, JWTError
from datetime import datetime, timedelta,timezone
from fastapi import FastAPI, HTTPException, status, Request
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

load_dotenv()

# Constante 
Secret_key = os.getenv("SECRET_KEY")
Algortihm = "HS256" 
Expire_delta = 3600 
url = os.getenv("URL_BASE_SCRAPER") 
apikey = os.getenv("KEY")
email = os.getenv("EMAIL")
password_email = os.getenv("PASSWORD_EMAIL")

# Configuración de FastAPI-Mail
conf = ConnectionConfig(
    MAIL_USERNAME=email,
    MAIL_PASSWORD=password_email,
    MAIL_FROM=email,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
# Almacenamiento temporal para códigos de recuperación
codigos_recuperacion = {}
codigos_validados = {}

# Funcion de aranque 
@asynccontextmanager
async def startup_lifespan(app: FastAPI):
    print("🎯 Iniciando ciclo de vida")

    # Crear tablas
    SQLModel.metadata.create_all(engine)
    print("✅ Tablas creadas")

    # Crear CSV si no existe
    CSV_PATH = "Metricas.csv"
    if not os.path.exists(CSV_PATH):
        pd.DataFrame(columns=["FechaHora", "Metodo","Endpoints","Status", "DuracionSegundos"]).to_csv(CSV_PATH, index=False)
        print("📄 CSV creado")

    # Cargar modelo
    try:
        print("📦 Cargando modelo...")
        modelo = joblib.load("modelo_random_forest.pkl")
        app.state.modelo_rf = modelo
        print("✅ Modelo cargado correctamente")
    except FileNotFoundError as e:
        print(f"❌ Error al cargar el modelo: {e}")

    yield

# ___________________________ Funciones de manejo de datos_________________________

def preparar_datos(data,modelo)-> pd.DataFrame:
    """ Prepara los datos para el modelo """
    
    # Limpiamos los datos
    df = limpiar_datos(pd.DataFrame(data))
    
    # Datos que usará el modelo
    x = df[["Precio", "Puntuacion", "PC", "PPW", "PS"]].values

    # Predicción
    df["IR"] = modelo.predict(x)


    # Escalado final
    df["IR"] = (df["IR"] - df["IR"].min()) / (df["IR"].max() - df["IR"].min()) * 100

    # Guardar y mostrar resultados
    top = df.nlargest(7, "IR")#se pone en 10

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
    
# _______________________ Solicitudes a API _______________________________

async def hacer_peticion_scraper(producto: str):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await client.post(url + producto, headers={"scraper-api": apikey})
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except Exception as e:
        print(f"[ERROR] Error al pedir scraping para '{producto}': {e}")
        return []

# ______________________________________ Email _____________________________________________________________

def generar_codigo() -> str:
    """ Generar codigo de recuperacion de cuenta"""
    ""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(6))

async def enviar_correo(correo:Email,code:str):
    """ Envia el mensaje al usuario con el correo"""
    # Leemos el archivo html para pasar la informacion
    with open("templates/email_templates.html", "r", encoding="utf-8") as file:
        html_template = file.read()
    
    # Ponemos el codigo en el html
    templates = string.Template(html_template)
    html_content = templates.safe_substitute(code=code)
    
    # Definimos el cuerpo del mensaje       
    mensaje = MessageSchema(
        subject="Recuperacion de contraseña",
        recipients=[correo],
        body=html_content,
        subtype="html"
    )
    
    # Enviamos con la configuracion definida
    fm = FastMail(config=conf)
    await fm.send_message(mensaje)