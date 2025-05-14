import os
import time
import pandas as pd
from db import crear_table
from datetime import datetime
from routers import usuarios,render
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi import FastAPI,HTTPException, Request

app = FastAPI(
    title="Scrapymarket API",
    lifespan=crear_table,
    docs_url=None, redoc_url=None # Deshabilitar documentación automática
)

templates = Jinja2Templates("templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ruta del csv
CSV_PATH = "Metricas.csv"

# Si no existe, crea el archivo con encabezado
if not os.path.exists(CSV_PATH):
    df_init = pd.DataFrame(columns=["FechaHora", "Metodo","Endpoints","Status", "DuracionSegundos"])
    df_init.to_csv(CSV_PATH, index=False, encoding="utf-8")


# Middleware para monitorear el trafico
@app.middleware("http")
async def monitorear(request: Request, call_next):
    inicio = time.perf_counter() # Iniciamos el contador
    http_method = request.method # Obtener el metodo de la request
    endpoint = request.url.path  # Obtener la ruta  
    response = await call_next(request) 
    status = response.status_code
    final = time.perf_counter() - inicio # Finalizar el tiempo
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Fecha y hora actual
    duracion_formateada = round(final, 4) # Duracion formateada

    # Crear un DataFrame con una sola fila
    df = pd.DataFrame([{
        "FechaHora": timestamp,
        "Metodo": http_method,
        "Endpoints": endpoint,
        "Status":status,
        "DuracionSegundos": duracion_formateada
    }])

    # Escribir al CSV en modo append, sin escribir encabezado
    df.to_csv(CSV_PATH, mode='a', header=False, index=False, encoding="utf-8")

    #print(f"[{timestamp}] Método: {http_method} | Duración: {duracion_formateada} segundos")

    return response

app.include_router(usuarios.router)
app.include_router(render.router)

# Manejador global de excepciones
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 429:
        # Si el código de error es 429, renderizamos una plantilla con el mensaje de error
        return templates.TemplateResponse("error_429.html",{"request": request,  
                "title":"Demasiadas peticiones",
                "message": "Demasiadas peticiones, por favor intente más tarde.",
                "error_description":"Demasiadas solicitudes en poco tiempo vuelva a intentar mas tarde"}, status_code=429)
    
    if exc.status_code == 401:
        return templates.TemplateResponse("error.html", {"request": request,
                "title":"Credenciales",
                "message":"Credenciales invalidas",
                "error_description":"Credenciales incorrectas verifique sus datos"},
                status_code=401)
    # Aquí dejamos que FastAPI maneje otros errores
    return await request.app.default_exception_handler(request, exc)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    user_id = request.cookies.get("user_id", "")
    user_name = request.cookies.get("user_name", "Usuario")

    redirect_url = f"/inicio?user_name={user_name}&user_id={user_id}&error=rate_limit"
    response = RedirectResponse(url=redirect_url, status_code=303)

    response.set_cookie("user_id", user_id, max_age=1800, httponly=True)
    response.set_cookie("user_name", user_name, max_age=1800, httponly=True)

    return response


    
