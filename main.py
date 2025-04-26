from fastapi import FastAPI
from db import crear_table
from routers import usuarios,render
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Scrapymarket API",
    lifespan=crear_table,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(usuarios.router)
app.include_router(render.router)