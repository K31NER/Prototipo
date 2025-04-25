import os
import json
import pandas as pd

# Rutas de los archivos
RUTA_CATEGORIAS = "Clasificador/categorias.json"
SALIDA_META = "Users/categorias_meta.json"

def leer_json_categorias(ruta: str) -> dict:
    """
    Lee un archivo JSON que contiene las categorías clasificadas por producto.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo JSON: {e}")
        return {}

def generar_categorias_meta(data: dict) -> list:
    """
    Genera una lista de categorías únicas (nivel 0) con IDs.
    """
    categorias_nivel_0 = [
        categorias[0] for categorias in data.values()
        if categorias and isinstance(categorias, list)
    ]

    df = pd.DataFrame(categorias_nivel_0, columns=["categoria"])
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["id"] = df.index + 1  # ID incremental comenzando en 1

    # Reordenamos columnas para claridad
    df = df[["id", "categoria"]]

    try:
        df.to_json(SALIDA_META, orient="records", force_ascii=False, indent=4)
        print(f"[OK] Se guardaron {len(df)} categorías meta únicas en '{SALIDA_META}'.")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar el JSON: {e}")

    return df.to_dict(orient="records")

def actualizar_categorias_meta(nueva_categoria: str, ruta_meta: str = "Users/categorias_meta.json"):
    """
    Verifica si la categoría ya existe en el JSON meta y, si no, la agrega con un nuevo ID.
    """
    if not nueva_categoria:
        return

    # Cargar categorías meta actuales
    try:
        if os.path.exists(ruta_meta):
            with open(ruta_meta, "r", encoding="utf-8") as f:
                categorias_meta = json.load(f)
        else:
            categorias_meta = []
    except Exception as e:
        print( f"[ERROR] Al leer categorias meta: {e}")
        categorias_meta = []

    # Revisar si la categoría ya existe
    categorias_existentes = {cat.get("categoria") for cat in categorias_meta if "categoria" in cat}
    if nueva_categoria not in categorias_existentes:
        nuevo_id = max([cat["id"] for cat in categorias_meta], default=0) + 1
        nueva_entrada = {"id": nuevo_id, "categoria": nueva_categoria}
        categorias_meta.append(nueva_entrada)

        # Guardar cambios
        try:
            with open(ruta_meta, "w", encoding="utf-8") as f:
                json.dump(categorias_meta, f, indent=4, ensure_ascii=False)
            print( f"[INFO] Nueva categoría agregada: {nueva_entrada}")
        except Exception as e:
            print( f"[ERROR] Al guardar nueva categoría: {e}")

