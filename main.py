from fastapi import FastAPI
from db import crear_table
from routers import usuarios


app = FastAPI(
    title="Scrapymarket API",
    lifespan=crear_table,
)

app.include_router(usuarios.router)