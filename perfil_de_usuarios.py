import os
import json
from collections import defaultdict
from typing import Literal, List,Dict, Optional
from Clasificador.NLP import clasificar_producto
from pydantic import BaseModel,Field, model_validator


URL = "Users/usuarios.json"
# ___________________ Modelo de usuario base __________________________________________________----
class PerfilUsuario(BaseModel):
    username: str
    edad: int
    genero: Optional[Literal["M", "F"]] = None
    productos_buscados: List[str] = Field(default_factory=list)
    categorias_visitadas: Dict[str, float] = Field(default_factory=dict)
    
    @model_validator(mode="after")
    def generar_categorias(self) -> "PerfilUsuario":
        if not self.productos_buscados:
            return self
        categorias = [obtener_categoria_meta(p) for p in self.productos_buscados]
        self.categorias_visitadas = generar_embedding(categorias)
        return self

# _________________________ Funciones de embedding __________________________________________________----

# Funcion para categorizar producto
def obtener_categoria_meta(producto:str) -> str:
    """
    Obtine la categoria meta de la siguiente manera:
    Obtenemos los valores del dicionario y lo volvemos una lista con la cual obtendremos 
    el indice 1 que son categorias y despues sacamos el indice 0 que es la primera categoria 
    """
    categoria = clasificar_producto(producto)
    
    categoria_meta  = list(categoria.values())[1][0] # 
    return categoria_meta

# _________________________ Función para generar embeddings de categorías _____________________________________

def generar_embedding(conteo_categorias: Dict[str, int]) -> dict:
    """
    Genera un embedding personalizado en base a la frecuencia con la que el usuario ha visitado cada categoría.

    A partir de un diccionario donde las claves son categorías y los valores son la cantidad de veces que se
    ha buscado dicha categoría, se calculan proporciones normalizadas para representar el perfil de intereses del usuario.
    """
    total = sum(conteo_categorias.values())  # Suma total de visitas a todas las categorías

    if total == 0:
        return {}  # Si no hay datos, retornamos un embedding vacío

    # Se calcula la proporción por categoría
    return {
        categoria: round(freq / total, 3)
        for categoria, freq in conteo_categorias.items()
    }


# ___________________________ Funciones Json para simular base de datos _____________________________________-

# Cargar todos los usuarios desde el JSON
def cargar_usuarios() -> Dict[str, dict]:
    """ Funcion para cargar los usuarios"""
    if not os.path.exists(URL):
        return {}
    with open(URL, "r", encoding="utf-8") as f:
        return json.load(f)

# Guardar todos los usuarios en el JSON
def guardar_usuarios(data: Dict[str, dict]):
    """ Funcion para guardar usuarios en el json"""
    with open(URL, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Guardar o actualizar un usuario por su username
def guardar_o_actualizar_usuario(perfil: PerfilUsuario):
    
    """ Funcion para refrescar la 'base de datos' """
    db = cargar_usuarios()
    
    # Si el usuario ya existe, actualizamos sus búsquedas
    if perfil.username in db:
        usuario_existente = db[perfil.username]
        productos_actuales = set(usuario_existente.get("productos_buscados", []))
        nuevos_productos = set(perfil.productos_buscados)
        productos_merged = list(productos_actuales.union(nuevos_productos))

        # Creamos nuevo perfil actualizado
        perfil.productos_buscados = productos_merged
        perfil = PerfilUsuario(**perfil.model_dump())  # Regenerar embedding

    # Guardamos o actualizamos en la "base de datos"
    db[perfil.username] = perfil.model_dump()
    guardar_usuarios(db)
    print(f"✅ Usuario '{perfil.username}' guardado o actualizado.")
    