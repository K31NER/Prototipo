import pandas as pd
import json
from comercios.popularidad import obtener_popularidad  

# __________________________ Diccionarios y parámetros ___________________________

datos_popularidad = obtener_popularidad()

# Convertir a DataFrame
df_popularidad = pd.DataFrame(datos_popularidad)

# Convertir el DataFrame a un diccionario con los valores de popularidad
valores_popularidad = dict(zip(df_popularidad["comercio"], df_popularidad["popularidad"]))

# Convertir el DataFrame a un diccionario con los valores de popularidad
valores_popularidad = dict(zip(df_popularidad["comercio"], df_popularidad["popularidad"]))

# Definir la popularidad ajustada
popularidad = {k: valores_popularidad.get(k, 20) for k in ["Mercado Libre", "Alkosto", "Falabella", "Éxito", "Linio", "Jumbo"]}

# Índice de seguridad (ajustado a 1-100)
seguridad = {
    "Mercado Libre": 5.0 * 20,
    "Falabella": 4.6 * 20,
    "Alkosto": 4.5 * 20,
    "Éxito": 3.7 * 20,
    "Linio": 2.6 * 20,
    "Jumbo": 1.9 * 20
}

# ___________________ Función para limpiar el df ___________________________
def limpiar_datos(df) -> pd.DataFrame:
    # Hacemos una copia del DataFrame
    df = df.copy()

    # Verificar si las columnas existen antes de intentar limpiarlas
    if "Precio" not in df.columns or "Puntuacion" not in df.columns:
        raise ValueError("El DataFrame debe contener las columnas 'Precio' y 'Puntuacion'")

    # Limpiar la columna "Precio"
    df["Precio"] = df["Precio"].astype(str).str.replace(r"[^\d]", "", regex=True).replace("", "0").astype(float)

    # Limpiar la columna "Puntuacion"
    df["Puntuacion"] = pd.to_numeric(df["Puntuacion"], errors="coerce")

    # Eliminar productos sin puntuación válida
    df = df.dropna(subset=["Puntuacion"])

    # Filtrar productos con puntuación inválida
    #df = df[df["Puntuacion"] > 1]  


    # Normalización de Puntuación y Precio
    P_min, P_max = df["Puntuacion"].min(), df["Puntuacion"].max()
    V_min, V_max = df["Precio"].min(), df["Precio"].max()

    # Evitar división por cero en el cálculo de PC
    if P_min == P_max:
        df["Puntuacion_Norm"] = 1  # Si solo hay un valor, lo tratamos como máximo posible
    else:
        df["Puntuacion_Norm"] = (df["Puntuacion"] - P_min) / (P_max - P_min)

    if V_min == V_max:
        df["Precio_Norm"] = 1  # Si solo hay un valor, lo dejamos como neutro
    else:
        df["Precio_Norm"] = 1 - ((df["Precio"] - V_min) / (V_max - V_min))

    # Calcular PC
    df["PC"] = df["Puntuacion_Norm"] * df["Precio_Norm"] * 100  # Escalar a 0-100

    # Asegurar que PC sea válido
    df = df[df["PC"].notna() & (df["PC"] > 0)]

    # Agregar popularidad y seguridad
    df["PPW"] = df["Pagina"].map(popularidad).fillna(50)
    df["PS"] = df["Pagina"].map(seguridad).fillna(50)
    
    # Devolvemos el df para que sea procesado por los algoritmos 
    return df