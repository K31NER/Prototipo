from db import crear_table
from routers import usuarios,render
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI,HTTPException, Request

app = FastAPI(
    title="Scrapymarket API",
    lifespan=crear_table,
    docs_url=None, redoc_url=None # Deshabilitar documentación automática
)

templates = Jinja2Templates("templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

    return templates.TemplateResponse(
        "inicio.html",
        {
            "request": request,
            "name": user_name.capitalize(),
            "user_id": user_id,
            "error": "Has alcanzado el límite de búsquedas. Intenta nuevamente más tarde."
        },
        status_code=429
    )
    
