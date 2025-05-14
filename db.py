from  sqlmodel import SQLModel, create_engine, Session
from fastapi import FastAPI, Depends
from typing import Annotated

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False},
                    isolation_level="SERIALIZABLE")

def get_session():
    """ Funcion para obtener la sesion de la base de datos"""
    with Session(engine) as session:
        yield session
        
def crear_table(app: FastAPI):
    """ Crear las tablas de la base de datos"""
    SQLModel.metadata.create_all(engine)
    yield
    
sesion = Annotated[Session, Depends(get_session)]
    