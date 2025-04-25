from sqlmodel import SQLModel, Field
from typing import  List, Dict
from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON


# Clases de usuario
class UserBase(SQLModel):
    nombre: str = Field(index=True)
    correo: str = Field(index=True, unique=True)
    genero: str = Field(index=True)
    edad: int = Field(index=True)
    
class CreateUser(UserBase):
    contraseña: str = Field(index=True)
    
class ReadUser(UserBase):
    id: int = Field(default=None, primary_key=True)
    
class User(UserBase, table=True):
    id: int = Field(default=None, primary_key=True)
    contraseña: str = Field(index=True)
    
    productos_buscados: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )

    categorias_visitadas_raw: Dict[str, int] = Field(  
        default_factory=dict,
        sa_column=Column(JSON)
    )

    categorias_embedding: List[float] = Field(  
        default_factory=list,
        sa_column=Column(JSON)
    )
    class Config:
        orm_mode = True

# Clase para logear
class Login(BaseModel):
    nombre: str
    contraseña: str
