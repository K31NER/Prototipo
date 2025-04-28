from fastapi import FastAPI,HTTPException, Request
from fastapi.templating import Jinja2Templates
from db import crear_table
from routers import usuarios,render
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Scrapymarket API",
    lifespan=crear_table,
)

templates = Jinja2Templates("templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(usuarios.router)
app.include_router(render.router)

# Manejador global de excepciones
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return templates.TemplateResponse("error.html", {"request": request})
    # Aquí dejamos que FastAPI maneje otros errores
    return await request.app.default_exception_handler(request, exc)