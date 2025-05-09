from sqlmodel import SQLModel, Field
from typing import  List, Dict,Optional
from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.mutable import MutableDict, MutableList
from datetime import date

# Clases de usuario
class UserBase(SQLModel):
    nombre: str = Field(index=True)
    correo: str = Field(index=True, unique=True)
    genero: str = Field(index=True)
    fecha_nacimiento: date = Field(index=True)  
    
class ReadUser(UserBase):
    id: int = Field(default=None, primary_key=True)
    
class User(UserBase, table=True):
    id: int = Field(default=None, primary_key=True)
    contraseña: str = Field(index=True)
    
    productos_buscados: List[str] = Field(
        default_factory=list,
        sa_column=Column(MutableList.as_mutable(JSON))
    )

    categorias_visitadas_raw: Dict[str, int] = Field(  
        default_factory=dict,
        sa_column=Column(MutableDict.as_mutable(JSON))
    )

    categorias_embedding: Dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(MutableDict.as_mutable(JSON))
    )

    class Config:
        orm_mode = True

# Email schemas
class Email(BaseModel):
    email: str
    
class PasswordRest(Email):
    code:str
    new_passwprd: str
    